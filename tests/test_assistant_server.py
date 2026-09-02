"""The public assistant separates visitors, budgets calls, and names authority."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from apps.assistant.server import (
    BudgetedAssistant,
    BudgetExceeded,
    CallBudget,
    SessionRegistry,
    SessionUsage,
    build_handler,
)
from featuregraph.study_builder import OfflineResearchAssistant


@pytest.fixture
def registry(tmp_path: Path) -> SessionRegistry:
    return SessionRegistry(
        budget=CallBudget(session_limit=3, global_limit=5),
        base_directory=tmp_path,
        assistant_factory=OfflineResearchAssistant,
        authority_template="public demonstration session {session}",
    )


class Client:
    """A browser-shaped client: one cookie jar, absolute URLs."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.cookie: str | None = None

    def request(self, path: str, body: dict | None = None) -> dict:
        request = urllib.request.Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        if self.cookie:
            request.add_header("Cookie", self.cookie)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
                issued = response.headers.get("Set-Cookie")
                status = response.status
        except urllib.error.HTTPError as error:
            raw, issued, status = error.read(), None, error.code
        if issued:
            self.cookie = issued.split(";", 1)[0]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"_body": raw.decode("utf-8", "replace")}
        payload["_status"] = status
        return payload


@pytest.fixture
def client(registry: SessionRegistry):
    handler = build_handler(registry, "offline frozen example", secure_cookie=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield lambda: Client(f"http://{host}:{port}")
    finally:
        server.shutdown()
        server.server_close()


def test_two_visitors_do_not_share_a_conversation(client) -> None:
    first, second = client(), client()

    first.request("/api/message", {"message": "How do the protocol versions align?"})
    second_state = second.request("/api/state")

    assert first.cookie != second.cookie
    # The second visitor sees the opening prompt only, not the first one's turn.
    assert len(second_state["messages"]) == 1
    assert len(first.request("/api/state")["messages"]) == 3


def test_a_session_is_kept_across_requests(client) -> None:
    visitor = client()

    visitor.request("/api/message", {"message": "How do the protocol versions align?"})
    visitor.request("/api/message", {"message": "Yes, exactly. Preserve those."})
    state = visitor.request("/api/state")

    assert state["phase"] == "awaiting_approval"
    assert state["can_approve"] is True


def test_the_approval_authority_is_the_session_not_a_person(client, tmp_path) -> None:
    visitor = client()
    visitor.request("/api/message", {"message": "How do the protocol versions align?"})
    visitor.request("/api/message", {"message": "Yes, exactly. Preserve those."})

    visitor.request("/api/approve", {})

    contracts = list(tmp_path.rglob("study_contract_v1.json"))
    assert len(contracts) == 1
    approval = json.loads(contracts[0].read_text())["approval"]
    assert approval["authority"].startswith("public demonstration session ")
    assert "Nazia" not in approval["authority"]


def test_the_budget_is_reported_and_spent_per_call(client) -> None:
    visitor = client()

    first = visitor.request("/api/message", {"message": "How do these align?"})

    assert first["budget"]["session_calls_used"] == 1
    assert first["budget"]["session_call_limit"] == 3
    assert first["budget"]["global_call_limit"] == 5


def test_an_exhausted_session_keeps_its_conversation(client) -> None:
    visitor = client()
    for _ in range(3):
        visitor.request("/api/message", {"message": "Tell me more about the states."})

    spent = visitor.request("/api/message", {"message": "And once more."})

    assert "used its 3 assistant calls" in spent["error"]
    # A refusal is a state of the deployment, not a lost conversation.
    assert spent["messages"]
    assert spent["budget"]["session_calls_used"] == 3


def test_the_global_ceiling_stops_new_visitors(client) -> None:
    for _ in range(5):
        client().request("/api/message", {"message": "How do these align?"})

    blocked = client().request("/api/message", {"message": "How do these align?"})

    assert "used its assistant calls" in blocked["error"]


def test_a_visitor_cannot_read_outside_their_own_artifacts(client) -> None:
    visitor = client()
    visitor.request("/api/message", {"message": "How do these align?"})

    # Percent-encoded so the traversal survives URL normalisation and actually
    # reaches the handler's containment check rather than dying at routing.
    escaped = visitor.request("/artifacts/%2e%2e%2f%2e%2e%2fetc%2fpasswd")
    real = visitor.request("/artifacts/conversation_checkpoint.md")

    assert escaped["_status"] == 404
    assert real["_status"] == 200


def test_health_check_answers_without_a_session(client) -> None:
    assert client().request("/healthz")["ok"] is True


def test_budget_charges_calls_not_turns() -> None:
    budget = CallBudget(session_limit=2, global_limit=10)
    usage = SessionUsage()
    assistant = BudgetedAssistant(OfflineResearchAssistant(), budget, usage)

    assistant.clarify("a goal")
    assistant.draft("a goal", "yes, exactly")

    assert usage.calls == 2
    with pytest.raises(BudgetExceeded):
        assistant.clarify("a third")


def test_sessions_are_evicted_and_their_artifacts_removed(registry, tmp_path) -> None:
    visitor, _ = registry.get_or_create(None)
    root = visitor.artifact_root
    assert root.exists()

    registry.ttl_seconds = -1
    registry.get_or_create(None)

    assert not root.exists()
    assert registry.live_sessions == 1
