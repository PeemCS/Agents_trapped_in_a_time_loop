"""Authenticated, bounded Qwen inference service for Colab."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading

from .model import MODEL_ID, QwenModel, RequestError


LIMIT = 192_000


def create_server(host: str, port: int, token: str, model) -> ThreadingHTTPServer:
    expected = f"Bearer {token}".encode()
    if not token:
        raise ValueError("Set a nonempty inference token.")
    available = threading.BoundedSemaphore(1)

    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.request.settimeout(8)

        def send_json(self, status: int, item: dict) -> None:
            body = json.dumps(item, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_request(self, code="-", size="-") -> None:
            # Paths and request-targets may accidentally contain copied secrets.
            self.log_message("HTTP %s", code)

        def do_GET(self) -> None:
            if self.path == "/health":
                info = model.metadata() if isinstance(model, QwenModel) else {"model": MODEL_ID}
                # Details such as the adapter fingerprint travel only in authenticated output.
                self.send_json(200, {"ready": True, "model": info["model"]})
            else:
                self.send_json(404, {"error": "Unknown route."})

        def do_POST(self) -> None:
            if self.path != "/generate":
                self.send_json(404, {"error": "Unknown route."})
                return
            raw_token = self.headers.get("Authorization", "")
            if not secrets.compare_digest(raw_token.encode(), expected):
                self.send_json(401, {"error": "Unauthorized."})
                return
            try:
                raw_size = self.headers.get("Content-Length", "")
                if len(raw_size) > 6 or not raw_size.isascii() or not raw_size.isdecimal():
                    raise ValueError
                size = int(raw_size)
                if not 0 < size <= LIMIT or self.headers.get("Transfer-Encoding"):
                    raise ValueError
                body = self.rfile.read(size)
                if len(body) != size:
                    raise ValueError
                request = json.loads(body)
                if not isinstance(request, dict):
                    raise ValueError
            except (OSError, ValueError, RecursionError):
                self.send_json(400, {"error": "Expected a complete JSON object with a valid content length."})
                return
            if not available.acquire(blocking=False):
                self.send_json(429, {"error": "The inference device is busy."})
                return
            try:
                response = model.generate(request)
            except RequestError as error:
                self.send_json(400, {"error": str(error)})
            except Exception as error:
                self.log_error("Inference failed with %s", type(error).__name__)
                self.send_json(500, {"error": "Inference failed."})
            else:
                self.send_json(200, response)
            finally:
                available.release()

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--revision", help="Exact Hugging Face model commit.")
    parser.add_argument("--quantize-4bit", action="store_true", help="Use NF4 weights on a smaller CUDA GPU.")
    parser.add_argument("--persona-bank", type=Path, help="Locally calibrated persona JSON.")
    parser.add_argument("--adapter", type=Path, help="Local LoRA directory that passed held-out evaluation.")
    parser.add_argument("--default-longing", action="store_true", help="Apply the validated longing coefficient.")
    args = parser.parse_args()
    token = os.environ.get("PHIL_TOKEN", "")
    if len(token) < 24 or not token.isascii() or not all(33 <= ord(c) <= 126 for c in token):
        parser.error("Set PHIL_TOKEN to a generated service secret of at least 24 printable ASCII characters.")
    try:
        model = QwenModel(revision=args.revision, quantize=args.quantize_4bit,
                          persona_bank=args.persona_bank, adapter=args.adapter,
                          default_longing=args.default_longing)
    except (ImportError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    with create_server("127.0.0.1", args.port, token, model) as server:
        print(f"{MODEL_ID} at {model.revision} ready on port {args.port} ({model.precision}, {model.adapter})",
              flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
