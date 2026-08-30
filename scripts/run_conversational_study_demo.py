"""Serve the Cohere-assisted FeatureGraph conversational study demonstration."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import webbrowser
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from featuregraph.study_builder import (
    CohereResearchAssistant,
    ConversationalStudySession,
    OfflineResearchAssistant,
)
from scripts.conversational_demo_backend import (
    APPROVED_STUDY_CONTRACT,
    PhysioNetConversationalDemoExecutor,
    write_demo_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERFACE_PATH = REPO_ROOT / "apps" / "conversational_study_demo" / "index.html"


class DemoRequestHandler(BaseHTTPRequestHandler):
    """Single-session JSON and artifact server for the local demonstration."""

    session: ConversationalStudySession
    assistant_mode: str

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_bytes(
                INTERFACE_PATH.read_bytes(),
                "text/html; charset=utf-8",
            )
            return
        if parsed.path == "/api/state":
            state = self.session.state()
            state["assistant_mode"] = self.assistant_mode
            self._send_json(state)
            return
        if parsed.path.startswith("/artifacts/"):
            self._send_artifact(unquote(parsed.path.removeprefix("/artifacts/")))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/message":
            payload = self._read_json()
            message = payload.get("message")
            if not isinstance(message, str):
                self._send_json(
                    {"error": "message must be a string"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                response = self.session.handle_message(message)
            except Exception as error:  # pragma: no cover - UI recovery boundary
                print(
                    f"Cohere assistant request failed: {error}",
                    file=sys.stderr,
                )
                self._send_json(
                    {
                        "error": (
                            "The assistant could not process this turn. "
                            "Check the server console for details and retry."
                        )
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self._send_json(response.as_dict())
            return
        if parsed.path == "/api/approve":
            try:
                response = self.session.approve_and_run()
            except Exception as error:  # pragma: no cover - UI recovery boundary
                self._send_json(
                    {"error": f"The approved study could not run: {error}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self._send_json(response.as_dict())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the local demo console concise."""

        del format, args

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw or b"{}")
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

    def _send_artifact(self, relative_path: str) -> None:
        root = self.session.artifact_directory
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
        self.end_headers()
        self.wfile.write(payload)


def build_session(
    output_directory: Path,
    *,
    offline: bool,
    authority: str,
    model: str,
) -> tuple[ConversationalStudySession, str]:
    """Construct a session with Cohere when configured, otherwise frozen mode."""

    api_key = os.environ.get("COHERE_API_KEY")
    if offline or not api_key:
        assistant = OfflineResearchAssistant()
        mode = "offline frozen example"
        selected_model = None
    else:
        assistant = CohereResearchAssistant(api_key=api_key, model=model)
        mode = "Cohere"
        selected_model = model
    output_directory.mkdir(parents=True, exist_ok=True)
    write_demo_manifest(
        output_directory / "demo_manifest.json",
        mode=mode,
        model=selected_model,
    )
    session = ConversationalStudySession(
        template_contract=APPROVED_STUDY_CONTRACT.contract,
        assistant=assistant,
        executor=PhysioNetConversationalDemoExecutor(),
        artifact_directory=output_directory,
        researcher_authority=authority,
    )
    return session, mode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--authority", default="Nazia Habib")
    parser.add_argument("--model", default="command-a-plus-05-2026")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (
        REPO_ROOT / "outputs" / "conversational_study_demo" / timestamp
    )
    session, mode = build_session(
        output.resolve(),
        offline=args.offline,
        authority=args.authority,
        model=args.model,
    )
    DemoRequestHandler.session = session
    DemoRequestHandler.assistant_mode = mode
    server = ThreadingHTTPServer((args.host, args.port), DemoRequestHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"FeatureGraph conversational study demo: {url}")
    print(f"Assistant mode: {mode}")
    print(f"Artifacts: {output.resolve()}")
    if args.open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
