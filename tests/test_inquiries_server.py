"""The inquiry service stores before it emails, and refuses what it should."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from apps.inquiries.server import (
    InquiryStore,
    RateLimiter,
    ValidationError,
    build_handler,
    clean_submission,
    render_email,
    resend_sender,
    resend_unsent,
)

ORIGIN = "https://featuregraph.ai"
PILOT = {
    "kind": "pilot",
    "name": "Ada",
    "email": "ada@example.com",
    "question": "How variable is the period?",
}


def test_clean_submission_keeps_only_known_fields() -> None:
    kind, fields = clean_submission({**PILOT, "company": " Acme ", "extra": "dropped"})
    assert kind == "pilot"
    assert fields["company"] == "Acme"
    assert "extra" not in fields


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {**PILOT, "kind": "other"},
        {k: v for k, v in PILOT.items() if k != "question"},
        {**PILOT, "email": "not-an-address"},
        {**PILOT, "email": "a@b.co\r\nBcc: x@y.z"},
        {**PILOT, "name": 5},
        {**PILOT, "question": "x" * 4001},
    ],
)
def test_clean_submission_rejects_bad_input(payload: object) -> None:
    with pytest.raises(ValidationError):
        clean_submission(payload)


def test_honeypot_hit_is_dropped_not_rejected() -> None:
    assert clean_submission({**PILOT, "website": "http://spam"}) is None


def test_email_subject_is_fixed_text() -> None:
    subject, body = render_email(
        "pilot", {**PILOT, "name": "Eve\r\nBcc: x@y.z"} | {"email": "e@x.co"}
    )
    assert "\n" not in subject and "Eve" not in subject
    assert "Question:\nHow variable" in body


def test_rate_limiter_window() -> None:
    limiter = RateLimiter(limit=2, window=10)
    assert limiter.allow("a", now=0) and limiter.allow("a", now=1)
    assert not limiter.allow("a", now=2)
    assert limiter.allow("b", now=2)
    assert limiter.allow("a", now=12)


class Service:
    def __init__(
        self, tmp_path: Path, fail_email: bool = False, limit: int = 5
    ) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.store = InquiryStore(tmp_path / "db" / "inquiries.db")

        def send(subject: str, body: str, reply_to: str) -> None:
            if fail_email:
                raise urllib.error.URLError("provider down")
            self.sent.append((subject, body, reply_to))

        handler = build_handler(
            self.store, send, RateLimiter(limit, 3600), frozenset({ORIGIN})
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def post(self, body: object, origin: str | None = ORIGIN, path: str = "/inquiries"):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read()), response.headers
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read()), error.headers

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def service(tmp_path: Path):
    svc = Service(tmp_path)
    yield svc
    svc.close()


def test_submission_is_stored_and_emailed(service: Service) -> None:
    status, body, headers = service.post(PILOT)
    assert (status, body) == (200, {"ok": True})
    assert headers["Access-Control-Allow-Origin"] == ORIGIN
    assert service.sent[0][2] == "ada@example.com"
    assert service.store.unsent() == []


def test_email_failure_keeps_the_submission(tmp_path: Path) -> None:
    svc = Service(tmp_path, fail_email=True)
    try:
        status, _, _ = svc.post(PILOT)
        assert status == 200
        unsent = svc.store.unsent()
        assert len(unsent) == 1 and unsent[0][2]["name"] == "Ada"
    finally:
        svc.close()


def test_honeypot_stores_nothing(service: Service) -> None:
    status, _, _ = service.post({**PILOT, "website": "x"})
    assert status == 200
    assert service.sent == [] and service.store.unsent() == []


def test_validation_error_is_400(service: Service) -> None:
    status, body, _ = service.post({**PILOT, "email": "nope"})
    assert status == 400 and "email" in body["error"]


def test_unknown_origin_is_refused(service: Service) -> None:
    status, _, _ = service.post(PILOT, origin="https://evil.example")
    assert status == 403
    assert service.sent == []


def test_rate_limit(tmp_path: Path) -> None:
    svc = Service(tmp_path, limit=2)
    try:
        assert [svc.post(PILOT)[0] for _ in range(3)] == [200, 200, 429]
    finally:
        svc.close()


def test_preflight_and_health(service: Service) -> None:
    request = urllib.request.Request(
        service.base + "/inquiries", headers={"Origin": ORIGIN}, method="OPTIONS"
    )
    with urllib.request.urlopen(request) as response:
        assert response.status == 204
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
    with urllib.request.urlopen(service.base + "/healthz") as response:
        assert response.status == 200


def test_resend_sender_identifies_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout):
        seen["headers"] = dict(request.header_items())
        seen["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    resend_sender("key", "A <a@x.co>", "to@x.co")("S", "B", "v@x.co")
    assert seen["headers"]["User-agent"].startswith("featuregraph-inquiries")
    assert seen["headers"]["Authorization"] == "Bearer key"
    assert seen["body"]["reply_to"] == "v@x.co"


def test_resend_unsent_sends_each_stored_row_once(tmp_path: Path) -> None:
    svc = Service(tmp_path, fail_email=True)
    try:
        svc.post(PILOT)
        svc.post({**PILOT, "name": "Bo"})
    finally:
        svc.close()
    sent: list[str] = []
    store = svc.store
    assert resend_unsent(store, lambda s, b, r: sent.append(r)) == 2
    assert store.unsent() == []
    assert resend_unsent(store, lambda s, b, r: sent.append(r)) == 0
    assert len(sent) == 2
