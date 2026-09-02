"""Serve the FeatureGraph study assistant to more than one person at a time.

``scripts/run_conversational_study_demo.py`` runs the same conversation on one
machine for one person, and holds its session in a class attribute. That is
correct for a local demonstration and wrong for a public deployment in three
ways, each of which this module exists to fix.

A shared session means two visitors type into the same conversation, and either
can approve the other's study. Sessions here are per visitor, keyed by an opaque
cookie, evicted on a timer.

An unbounded key is a bill. Every model call is charged against a per-session
and a process-wide budget before it is made.

And an anonymous visitor clicking "approve" is not a researcher approving a
study. The approval record names the session, not a person, so the contract it
produces says truthfully who stood behind it -- which is the whole point of
recording an authority at all.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from featuregraph.study_builder import (  # noqa: E402
    CohereResearchAssistant,
    ConversationalStudySession,
    DraftDecision,
    OfflineResearchAssistant,
)
from scripts.conversational_demo_backend import (  # noqa: E402
    APPROVED_STUDY_CONTRACT,
    PhysioNetConversationalDemoExecutor,
)

INTERFACE_PATH = Path(__file__).resolve().parent / "index.html"
COOKIE_NAME = "fg_session"

DEFAULT_SESSION_CALL_LIMIT = 10
DEFAULT_GLOBAL_CALL_LIMIT = 1000
#: The global ceiling refills on this cadence rather than being a lifetime cap.
DEFAULT_GLOBAL_WINDOW_SECONDS = 24 * 60 * 60
DEFAULT_SESSION_TTL_SECONDS = 60 * 60
DEFAULT_MAX_SESSIONS = 200


class BudgetExceeded(RuntimeError):
    """Raised before a model call that no remaining budget covers."""


class CallBudget:
    """Count model calls against a per-session ceiling and a rolling global one.

    The global ceiling refills. A lifetime cap on a machine that stays up would
    make the demonstration die permanently the first time it was popular, which
    is the wrong failure: the point of a ceiling here is to bound a day's spend,
    not to spend the site.

    It is still per process. Running more than one machine multiplies it, so the
    deployment pins a single machine rather than pretending this coordinates
    across them.
    """

    def __init__(
        self,
        *,
        session_limit: int,
        global_limit: int,
        window_seconds: int = DEFAULT_GLOBAL_WINDOW_SECONDS,
    ) -> None:
        self.session_limit = session_limit
        self.global_limit = global_limit
        self.window_seconds = window_seconds
        self._global_used = 0
        self._window_started = time.monotonic()
        self._lock = threading.Lock()

    def _roll_window(self) -> None:
        """Start a fresh window if the current one has run out. Holds the lock."""
        now = time.monotonic()
        if now - self._window_started >= self.window_seconds:
            self._global_used = 0
            self._window_started = now

    @property
    def global_used(self) -> int:
        with self._lock:
            self._roll_window()
            return self._global_used

    @property
    def window_remaining(self) -> int:
        """Seconds until the global ceiling refills."""
        with self._lock:
            elapsed = time.monotonic() - self._window_started
            return max(0, int(self.window_seconds - elapsed))

    def charge(self, usage: SessionUsage) -> None:
        """Reserve one call, or refuse before anything is spent."""
        with self._lock:
            self._roll_window()
            if usage.calls >= self.session_limit:
                raise BudgetExceeded(
                    "This session has used its "
                    f"{self.session_limit} assistant calls. Reload to start a "
                    "new one."
                )
            if self._global_used >= self.global_limit:
                hours = max(
                    1,
                    round(
                        (
                            self.window_seconds
                            - (time.monotonic() - self._window_started)
                        )
                        / 3600
                    ),
                )
                raise BudgetExceeded(
                    "This demonstration has used its assistant calls for now, "
                    f"and will accept more in about {hours} hour"
                    f"{'s' if hours != 1 else ''}. The conversation is still "
                    "readable, and the offline example remains available in "
                    "the repository."
                )
            self._global_used += 1
            usage.calls += 1


class SessionUsage:
    """How many model calls one visitor's session has spent."""

    def __init__(self) -> None:
        self.calls = 0


class BudgetedAssistant:
    """Charge the budget for every model call, not for every turn.

    A turn can make no calls at all -- an empty message, a phase that answers
    deterministically -- and counting turns would bill for those while missing a
    turn that calls twice.
    """

    def __init__(self, inner: Any, budget: CallBudget, usage: SessionUsage) -> None:
        self.inner = inner
        self.budget = budget
        self.usage = usage

    def clarify(self, research_goal: str) -> str:
        self.budget.charge(self.usage)
        return self.inner.clarify(research_goal)

    def draft(self, research_goal: str, clarification: str) -> DraftDecision:
        self.budget.charge(self.usage)
        return self.inner.draft(research_goal, clarification)

    def revise(
        self,
        revision: str,
        current_statistics: Sequence[str],
        research_question: str,
    ) -> DraftDecision:
        self.budget.charge(self.usage)
        return self.inner.revise(revision, current_statistics, research_question)


class VisitorSession:
    """One visitor's conversation, its budget, and where its artifacts live."""

    def __init__(
        self,
        session_id: str,
        session: ConversationalStudySession,
        usage: SessionUsage,
        artifact_root: Path,
    ) -> None:
        self.session_id = session_id
        self.session = session
        self.usage = usage
        self.artifact_root = artifact_root
        self.touched_at = time.monotonic()
        self.lock = threading.Lock()


class SessionRegistry:
    """Hand each visitor their own conversation, and reclaim it later.

    Every session holds a directory of written artifacts, so they cannot simply
    accumulate. Expired sessions are swept on access rather than by a background
    thread: no timer to leak, and a deployment nobody is using does no work.
    """

    def __init__(
        self,
        *,
        budget: CallBudget,
        base_directory: Path,
        assistant_factory: Any,
        authority_template: str,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        self.budget = budget
        self.base_directory = base_directory
        self.assistant_factory = assistant_factory
        self.authority_template = authority_template
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, VisitorSession] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str | None) -> tuple[VisitorSession, bool]:
        """Return this visitor's session, creating one when they have none."""
        self._sweep()
        with self._lock:
            if session_id and session_id in self._sessions:
                visitor = self._sessions[session_id]
                visitor.touched_at = time.monotonic()
                return visitor, False
            if len(self._sessions) >= self.max_sessions:
                oldest = min(self._sessions.values(), key=lambda item: item.touched_at)
                self._discard(oldest.session_id)
        new_id = secrets.token_urlsafe(16)
        visitor = self._build(new_id)
        with self._lock:
            self._sessions[new_id] = visitor
        return visitor, True

    def _build(self, session_id: str) -> VisitorSession:
        artifact_root = Path(
            tempfile.mkdtemp(
                prefix=f"session-{session_id[:8]}-", dir=self.base_directory
            )
        )
        usage = SessionUsage()
        assistant = BudgetedAssistant(self.assistant_factory(), self.budget, usage)
        session = ConversationalStudySession(
            template_contract=APPROVED_STUDY_CONTRACT.contract,
            assistant=assistant,
            executor=PhysioNetConversationalDemoExecutor(),
            artifact_directory=artifact_root,
            # Never a person's name. A visitor clicking approve is not a
            # researcher approving a study, and the approval record has to say
            # so -- it is the field the whole architecture rests on.
            researcher_authority=self.authority_template.format(session=session_id[:8]),
        )
        return VisitorSession(session_id, session, usage, artifact_root)

    def _sweep(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        with self._lock:
            expired = [
                key
                for key, visitor in self._sessions.items()
                if visitor.touched_at < cutoff
            ]
            for key in expired:
                self._discard(key)

    def _discard(self, session_id: str) -> None:
        """Drop a session and its artifacts. Caller holds the lock."""
        visitor = self._sessions.pop(session_id, None)
        if visitor is not None:
            shutil.rmtree(visitor.artifact_root, ignore_errors=True)

    @property
    def live_sessions(self) -> int:
        with self._lock:
            return len(self._sessions)


def build_handler(
    registry: SessionRegistry, assistant_mode: str, *, secure_cookie: bool = True
) -> type:
    """Bind one registry into a request handler class.

    ``secure_cookie`` is on for the deployment, which is served over TLS, and
    off for a plain-HTTP local run where a Secure cookie would never be stored
    and every request would look like a new visitor.
    """
    cookie_flags = "Secure; " if secure_cookie else ""

    class AssistantRequestHandler(BaseHTTPRequestHandler):
        """Route one visitor's requests to their own session."""

        server_version = "FeatureGraphAssistant"
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self._send_bytes(
                    INTERFACE_PATH.read_bytes(), "text/html; charset=utf-8"
                )
                return
            if parsed.path == "/healthz":
                self._send_json({"ok": True, "sessions": registry.live_sessions})
                return
            if parsed.path == "/api/state":
                visitor = self._visitor()
                with visitor.lock:
                    self._send_state(visitor)
                return
            if parsed.path.startswith("/artifacts/"):
                visitor = self._visitor()
                self._send_artifact(
                    visitor, unquote(parsed.path.removeprefix("/artifacts/"))
                )
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path not in ("/api/message", "/api/approve"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            visitor = self._visitor()
            # One turn at a time per visitor. Two tabs posting at once would
            # otherwise interleave phase transitions inside one session.
            with visitor.lock:
                if parsed.path == "/api/message":
                    payload = self._read_json()
                    message = payload.get("message")
                    if not isinstance(message, str):
                        self._send_json(
                            {"error": "message must be a string"},
                            status=HTTPStatus.BAD_REQUEST,
                        )
                        return
                    if len(message) > 4000:
                        self._send_json(
                            {"error": "message is too long"},
                            status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        )
                        return
                    self._run(visitor, lambda: visitor.session.handle_message(message))
                    return
                self._run(visitor, visitor.session.approve_and_run)

        def _run(self, visitor: VisitorSession, work: Any) -> None:
            try:
                work()
            except BudgetExceeded as refusal:
                # A spent budget is a state of the deployment, not a fault in
                # the request, so the conversation is returned intact with the
                # refusal alongside it.
                self._send_state(visitor, error=str(refusal))
                return
            except Exception as error:  # noqa: BLE001 - boundary for one turn
                print(f"assistant turn failed: {error!r}", file=sys.stderr)
                self._send_state(
                    visitor,
                    error=(
                        "The assistant could not complete this turn. The "
                        "conversation is unchanged; please try again."
                    ),
                )
                return
            self._send_state(visitor)

        #: Set by :meth:`_visitor`, and the only thing the cookie header reads.
        _issue_cookie_for: str | None = None

        def _visitor(self) -> VisitorSession:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            morsel = cookies.get(COOKIE_NAME)
            visitor, created = registry.get_or_create(morsel.value if morsel else None)
            if created:
                self._issue_cookie_for = visitor.session_id
            return visitor

        def _send_state(
            self, visitor: VisitorSession, *, error: str | None = None
        ) -> None:
            state = visitor.session.state()
            state["assistant_mode"] = assistant_mode
            state["budget"] = {
                "session_calls_used": visitor.usage.calls,
                "session_call_limit": registry.budget.session_limit,
                "global_calls_reserved": registry.budget.global_used,
                "global_call_limit": registry.budget.global_limit,
                "global_window_resets_in_seconds": registry.budget.window_remaining,
            }
            if error is not None:
                state["error"] = error
            self._send_json(state)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 64_000:
                return {}
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return {}
            return payload if isinstance(payload, dict) else {}

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self._send_bytes(
                json.dumps(payload).encode(),
                "application/json; charset=utf-8",
                status=status,
            )

        def _send_artifact(self, visitor: VisitorSession, relative_path: str) -> None:
            root = visitor.artifact_root.resolve()
            candidate = (root / relative_path).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = (
                "text/markdown; charset=utf-8"
                if candidate.suffix == ".md"
                else "application/json; charset=utf-8"
            )
            self._send_bytes(candidate.read_bytes(), content_type)

        def _send_bytes(
            self,
            payload: bytes,
            content_type: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if self._issue_cookie_for:
                self.send_header(
                    "Set-Cookie",
                    f"{COOKIE_NAME}={self._issue_cookie_for}; Path=/; HttpOnly; "
                    f"SameSite=Lax; {cookie_flags}Max-Age={registry.ttl_seconds}",
                )
            self.end_headers()
            self.wfile.write(payload)

    return AssistantRequestHandler


def build_assistant_factory(model: str) -> tuple[Any, str]:
    """Choose the model boundary from the environment, and say which was used.

    Without a key the deployment still serves: the offline assistant replays a
    maintained example, so the execution boundary stays demonstrable even when
    the budget is spent or the key is absent.
    """
    api_key = os.environ.get("COHERE_API_KEY", "").strip()
    if not api_key:
        return OfflineResearchAssistant, "offline frozen example"
    return (lambda: CohereResearchAssistant(api_key=api_key, model=model)), "Cohere"


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise SystemExit(f"{name} must be an integer, got {raw!r}.") from error
    if value < 1:
        raise SystemExit(f"{name} must be at least 1, got {value}.")
    return value


def main() -> None:
    """Run the assistant on the port the platform assigns."""
    host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104 - the platform routes to it
    port = _int_env("PORT", 8080)
    model = os.environ.get("FEATUREGRAPH_ASSISTANT_MODEL", "command-a-plus-05-2026")
    authority = os.environ.get(
        "FEATUREGRAPH_ASSISTANT_AUTHORITY",
        "public demonstration session {session}",
    )
    secure_cookie = os.environ.get("FEATUREGRAPH_INSECURE_COOKIE", "") == ""

    factory, mode = build_assistant_factory(model)
    budget = CallBudget(
        session_limit=_int_env(
            "FEATUREGRAPH_SESSION_CALL_LIMIT", DEFAULT_SESSION_CALL_LIMIT
        ),
        global_limit=_int_env(
            "FEATUREGRAPH_GLOBAL_CALL_LIMIT", DEFAULT_GLOBAL_CALL_LIMIT
        ),
    )
    base_directory = Path(
        os.environ.get("FEATUREGRAPH_SESSION_DIR", tempfile.gettempdir())
    )
    base_directory.mkdir(parents=True, exist_ok=True)
    registry = SessionRegistry(
        budget=budget,
        base_directory=base_directory,
        assistant_factory=factory,
        authority_template=authority,
        ttl_seconds=_int_env("FEATUREGRAPH_SESSION_TTL", DEFAULT_SESSION_TTL_SECONDS),
        max_sessions=_int_env("FEATUREGRAPH_MAX_SESSIONS", DEFAULT_MAX_SESSIONS),
    )
    handler = build_handler(registry, mode, secure_cookie=secure_cookie)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    print(
        f"FeatureGraph assistant on http://{host}:{port} "
        f"(assistant: {mode}, model: {model})",
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
