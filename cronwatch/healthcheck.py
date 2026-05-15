"""Simple HTTP healthcheck endpoint for cronwatch daemon."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional


class _Handler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves /health and /status."""

    status_fn: Callable[[], dict] = lambda: {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        elif self.path == "/status":
            try:
                data = self.server.status_fn()  # type: ignore[attr-defined]
                self._respond(200, data)
            except Exception as exc:  # pragma: no cover
                self._respond(500, {"error": str(exc)})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:  # pragma: no cover
        pass  # suppress default stderr logging


class HealthCheckServer:
    """Runs a tiny HTTP server in a background thread."""

    def __init__(
        self,
        status_fn: Callable[[], dict],
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self._status_fn = status_fn
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the healthcheck server in a daemon thread."""
        self._server = HTTPServer((self._host, self._port), _Handler)
        self._server.status_fn = self._status_fn  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the server gracefully."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"
