"""Receive inquiry-form submissions from featuregraph.ai.

The marketing site is static, so it cannot keep what a visitor types. This
service takes the submission as JSON, stores it, and emails it to the owner.

Order matters: the row is written first and the email second. A mail provider
outage then loses nothing -- the submission is in the database with
``emailed = 0`` and can be re-sent -- whereas the other order loses the
submission whenever the provider is down.

Standard library only, so the image stays small and there is nothing to patch.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

#: Field name -> (label used in the email, maximum length). Anything not listed
#: is dropped, so a client cannot store arbitrary keys.
FORMS: dict[str, dict[str, tuple[str, int]]] = {
    "pilot": {
        "name": ("Name", 200),
        "email": ("Email", 254),
        "company": ("Company", 200),
        "data": ("Data", 4000),
        "storage": ("Where the data is stored", 500),
        "question": ("Question", 4000),
        "start": ("Start", 200),
    },
    "build": {
        "name": ("Name", 200),
        "email": ("Email", 254),
        "building": ("What they are building", 4000),
        "data": ("Data", 4000),
        "want": ("Wanted from FeatureGraph", 4000),
    },
}
REQUIRED = {
    "pilot": ("name", "email", "question"),
    "build": ("name", "email", "building"),
}
SUBJECTS = {
    "pilot": "FeatureGraph analysis pilot inquiry",
    "build": "FeatureGraph build-your-own inquiry",
}
#: A field real visitors never see. Bots fill every input they find.
HONEYPOT = "website"
MAX_BODY_BYTES = 32 * 1024
EMAIL_PATTERN = re.compile(r"^[^@\s<>,;:\"]+@[^@\s<>,;:\"]+\.[^@\s<>,;:\"]+$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    fields TEXT NOT NULL,
    emailed INTEGER NOT NULL DEFAULT 0
)
"""

SendEmail = Callable[[str, str, str], None]


class ValidationError(ValueError):
    """The submission is not one we can accept; the message is safe to show."""


def clean_submission(payload: Any) -> tuple[str, dict[str, str]] | None:
    """Return (kind, fields), or None for a honeypot hit. Raise on bad input."""
    if not isinstance(payload, dict):
        raise ValidationError("Expected a JSON object.")
    if str(payload.get(HONEYPOT, "")).strip():
        return None
    kind = payload.get("kind")
    if kind not in FORMS:
        raise ValidationError("Unknown form.")
    fields: dict[str, str] = {}
    for key, (_label, limit) in FORMS[kind].items():
        value = payload.get(key, "")
        if not isinstance(value, str):
            raise ValidationError(f"{key} must be text.")
        value = value.strip()
        if len(value) > limit:
            raise ValidationError(f"{key} is too long.")
        if value:
            fields[key] = value
    for key in REQUIRED[kind]:
        if key not in fields:
            raise ValidationError(f"{key} is required.")
    if not EMAIL_PATTERN.match(fields["email"]):
        raise ValidationError("email is not a valid address.")
    return kind, fields


class RateLimiter:
    """At most ``limit`` submissions per key in any ``window`` seconds."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


class InquiryStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._connection.execute(SCHEMA)
            self._connection.commit()

    def add(self, kind: str, fields: dict[str, str]) -> int:
        received = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO inquiries (received_at, kind, fields) VALUES (?, ?, ?)",
                (received, kind, json.dumps(fields)),
            )
            self._connection.commit()
            return int(cursor.lastrowid)

    def mark_emailed(self, inquiry_id: int) -> None:
        with self._lock:
            self._connection.execute(
                "UPDATE inquiries SET emailed = 1 WHERE id = ?", (inquiry_id,)
            )
            self._connection.commit()

    def unsent(self) -> list[tuple[int, str, dict[str, str]]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, kind, fields FROM inquiries WHERE emailed = 0 ORDER BY id"
            ).fetchall()
        return [(row[0], row[1], json.loads(row[2])) for row in rows]


def render_email(kind: str, fields: dict[str, str]) -> tuple[str, str]:
    """Subject is fixed text: nothing a visitor typed goes into a header."""
    lines = [
        f"{label}:\n{fields[key]}"
        for key, (label, _limit) in FORMS[kind].items()
        if key in fields
    ]
    return SUBJECTS[kind], "\n\n".join(lines)


def resend_sender(api_key: str, sender: str, recipient: str) -> SendEmail:
    """Build a function that sends through Resend's HTTP API."""

    def send(subject: str, body: str, reply_to: str) -> None:
        request = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(
                {
                    "from": sender,
                    "to": [recipient],
                    "reply_to": reply_to,
                    "subject": subject,
                    "text": body,
                }
            ).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Resend sits behind a firewall that rejects the default
                # Python-urllib agent with a bare 403.
                "User-Agent": "featuregraph-inquiries/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10):
            pass

    return send


def deliver(
    store: InquiryStore,
    send: SendEmail | None,
    inquiry_id: int,
    kind: str,
    fields: dict[str, str],
) -> bool:
    if send is None:
        return False
    subject, body = render_email(kind, fields)
    try:
        send(subject, body, fields["email"])
    except (urllib.error.URLError, OSError, ValueError) as error:
        detail = ""
        if isinstance(error, urllib.error.HTTPError):
            # The status line alone ("403 Forbidden") hides the provider's reason.
            detail = " " + error.read(300).decode("utf-8", "replace")
        print(f"inquiry {inquiry_id}: email failed: {error}{detail}", flush=True)
        return False
    store.mark_emailed(inquiry_id)
    return True


def resend_unsent(store: InquiryStore, send: SendEmail | None) -> int:
    """Email every stored inquiry that was never sent. Returns how many went."""
    sent = 0
    for inquiry_id, kind, fields in store.unsent():
        if deliver(store, send, inquiry_id, kind, fields):
            sent += 1
    return sent


def build_handler(
    store: InquiryStore,
    send: SendEmail | None,
    limiter: RateLimiter,
    allowed_origins: frozenset[str],
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "FeatureGraphInquiries"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # request lines would carry client addresses; keep logs quiet

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "")
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _reply(self, status: HTTPStatus, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._reply(HTTPStatus.OK, {"ok": True})
            else:
                self._reply(HTTPStatus.NOT_FOUND, {"error": "Not found."})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/inquiries":
                self._reply(HTTPStatus.NOT_FOUND, {"error": "Not found."})
                return
            origin = self.headers.get("Origin", "")
            if origin not in allowed_origins:
                self._reply(HTTPStatus.FORBIDDEN, {"error": "Origin not allowed."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length <= 0 or length > MAX_BODY_BYTES:
                self._reply(HTTPStatus.BAD_REQUEST, {"error": "Bad request size."})
                return
            # Fly's proxy sets Fly-Client-IP; fall back to the socket address.
            client = self.headers.get("Fly-Client-IP") or self.client_address[0]
            if not limiter.allow(client):
                self._reply(
                    HTTPStatus.TOO_MANY_REQUESTS, {"error": "Too many requests."}
                )
                return
            try:
                payload = json.loads(self.rfile.read(length))
                cleaned = clean_submission(payload)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._reply(HTTPStatus.BAD_REQUEST, {"error": "Expected JSON."})
                return
            except ValidationError as error:
                self._reply(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            if cleaned is None:  # honeypot: look successful, keep nothing
                self._reply(HTTPStatus.OK, {"ok": True})
                return
            kind, fields = cleaned
            inquiry_id = store.add(kind, fields)
            deliver(store, send, inquiry_id, kind, fields)
            self._reply(HTTPStatus.OK, {"ok": True})

    return Handler


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    store = InquiryStore(Path(os.environ.get("INQUIRIES_DB", "/data/inquiries.db")))
    api_key = os.environ.get("RESEND_API_KEY", "")
    send = (
        resend_sender(
            api_key,
            os.environ.get("INQUIRY_FROM", "FeatureGraph <inquiries@featuregraph.ai>"),
            os.environ.get("INQUIRY_TO", "nazia.habib@featuregraph.ai"),
        )
        if api_key
        else None
    )
    if send is None:
        print(
            "RESEND_API_KEY is not set: inquiries are stored but not emailed.",
            flush=True,
        )
    origins = frozenset(
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS", "https://featuregraph.ai,https://www.featuregraph.ai"
        ).split(",")
        if origin.strip()
    )
    limiter = RateLimiter(
        limit=int(os.environ.get("INQUIRY_RATE_LIMIT", "5")), window=3600
    )
    handler = build_handler(store, send, limiter, origins)
    ThreadingHTTPServer(("0.0.0.0", port), handler).serve_forever()  # noqa: S104


if __name__ == "__main__":
    main()
