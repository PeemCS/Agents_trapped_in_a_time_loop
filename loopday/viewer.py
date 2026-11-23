"""Serve or export a self-contained LOOPDAY film and decision ledger."""

from __future__ import annotations

from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from .film import MAX_SECONDS, MIN_SECONDS
from .film_follow import FollowSource
from .film_stage import build_bundle


WEB = Path(__file__).resolve().parent.parent / "web"
STATIC = {
    "/": ("index.html", "text/html"),
    "/index.html": ("index.html", "text/html"),
    "/renderer.js": ("renderer.js", "text/javascript"),
    "/sound.js": ("sound.js", "text/javascript"),
    "/viewer.css": ("viewer.css", "text/css"),
    "/viewer.js": ("viewer.js", "text/javascript"),
}


def _json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def export_html(bundle: dict, path: Path) -> None:
    """Inline the exact app modules and replay data for a portable file."""
    stylesheet = (WEB / "viewer.css").read_text(encoding="utf-8")
    names = ("renderer.js", "sound.js", "viewer.js")
    code = []
    for name in names:
        raw = (WEB / name).read_text(encoding="utf-8")
        source = re.sub(r"^import [^\n]+\n", "", raw, flags=re.MULTILINE)
        source = re.sub(r"^export ", "", source, flags=re.MULTILINE)
        code.append(source)

    # Escapes prevent replay text from terminating the inert JSON script node.
    payload = _json(bundle).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="/viewer.css">', "<style>\n" + stylesheet + "\n</style>")
    html = html.replace(
        '<script type="module" src="/viewer.js"></script>',
        '<script type="application/json" id="loopday-bundle">' + payload + '</script>\n'
        + '<script type="module">\n' + "\n".join(code) + '\n</script>',
    )
    policy = (
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; media-src blob:; '
        'img-src data: blob:; connect-src \'none\'">'
    )
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n  ' + policy, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def viewer_handler(bundle: dict | None = None, *, source: FollowSource | None = None) -> type[BaseHTTPRequestHandler]:
    resources = {route: ((WEB / file).read_bytes(), mime) for route, (file, mime) in STATIC.items()}
    if bundle is not None:
        for route, payload in (
            ("/bundle.json", bundle), ("/run.json", bundle["run"]), ("/film.json", bundle["film"]),
        ):
            resources[route] = (_json(payload).encode("utf-8"), "application/json")
    if source is not None:
        replay, mime = resources["/"]
        live = replay.replace(b"<body>", b'<body data-follow="true">', 1)
        resources.update({"/": (live, mime), "/index.html": (live, mime), "/replay.html": (replay, mime)})

    class ViewerHandler(BaseHTTPRequestHandler):
        def log_request(self, code="-", size="-") -> None:
            if urlsplit(self.path).path != "/follow.json" or str(code) not in {"200", "304"}:
                super().log_request(code, size)

        def do_HEAD(self) -> None:
            self._reply(write_body=False)

        def do_GET(self) -> None:
            self._reply(write_body=True)

        def _reply(self, *, write_body: bool) -> None:
            route = urlsplit(self.path).path
            if source is not None and route in {"/follow.json", "/bundle.json"}:
                try:
                    etag, encoded = source.response()
                except (OSError, TypeError, ValueError):
                    self.send_error(503, "Committed checkpoint temporarily unavailable")
                    return
                if route == "/follow.json" and self.headers.get("If-None-Match") == etag:
                    self.send_response(304)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("ETag", etag)
                    self.end_headers()
                    return
                if route == "/bundle.json":
                    current = json.loads(encoded)["bundle"]
                    if not current:
                        self.send_error(404, "This directory has no committed event yet")
                        return
                    encoded = _json(current).encode("utf-8")
                self._send(encoded, "application/json", write_body, etag)
            elif route in resources:
                self._send(*resources[route], write_body)
            else:
                self.send_error(404)

        def _send(self, content: bytes, mime: str, write_body: bool, etag: str | None = None) -> None:
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'")
            if etag:
                self.send_header("ETag", etag)
            self.end_headers()
            if write_body:
                self.wfile.write(content)

    return ViewerHandler


def _serve(port: int, handler: type[BaseHTTPRequestHandler], mode: str) -> None:
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"LOOPDAY {mode} at http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("runs/preflight/run.json"))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seconds", type=float, default=94, help="Target film length in seconds")
    parser.add_argument("--follow", action="store_true", help="Observe committed checkpoint updates from the run directory")
    parser.add_argument("--export-html", type=Path, help="Write a stand-alone replay instead of opening a server")
    parser.add_argument("--compare-run", type=Path, help="Include a second run in the clock-aligned comparison")
    parser.add_argument("--label", default="Main run", help="Name of the primary run in the comparison")
    parser.add_argument("--compare-label", default="Comparison run", help="Name of the second run")
    parser.add_argument("--compare-tick", type=int, default=0, help="Initial time slot for the comparison")
    parser.add_argument("--include-model-traces", action="store_true", help="Show opt-in model-emitted text on localhost")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not MIN_SECONDS <= args.seconds <= MAX_SECONDS:
        parser.error(f"Film target must be {MIN_SECONDS}–{MAX_SECONDS} seconds.")
    if args.follow and (args.export_html or args.include_model_traces or args.compare_run):
        parser.error("Use follow mode on its own. Use saved replay mode for exports, traces, or comparisons.")
    if args.export_html and args.include_model_traces:
        parser.error("Model-emitted text can be inspected only on localhost.")
    try:
        if args.follow:
            source = FollowSource(args.run.absolute(), args.seconds)
            _serve(args.port, viewer_handler(source=source), "follow view")
            return
        run = json.loads(args.run.read_text(encoding="utf-8"))
        bundle = build_bundle(run, seconds=args.seconds, model_traces=args.include_model_traces)
        bundle["label"] = args.label
        bundle["compare_tick"] = args.compare_tick
        if args.compare_run:
            comparison = json.loads(args.compare_run.read_text(encoding="utf-8"))
            loaded = build_bundle(comparison, seconds=args.seconds, model_traces=args.include_model_traces)
            bundle["comparison"] = {"label": args.compare_label, **{key: loaded[key] for key in ("run", "stages", "roads")}}
        if args.export_html:
            export_html(bundle, args.export_html)
            print(args.export_html)
            return
        _serve(args.port, viewer_handler(bundle), "replay")
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
