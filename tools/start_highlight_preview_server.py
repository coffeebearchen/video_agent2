from __future__ import annotations

import argparse
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREVIEW_PATH = PROJECT_ROOT / "preview" / "highlight_ab_preview.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local Highlight A/B preview server.")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local preview server.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without opening the browser automatically.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    handler = lambda *handler_args, **handler_kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(PROJECT_ROOT),
        **handler_kwargs,
    )

    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        preview_url = f"http://127.0.0.1:{args.port}/preview/{PREVIEW_PATH.name}"
        print(f"[PREVIEW] serving workspace root: {PROJECT_ROOT}")
        print(f"[PREVIEW] open: {preview_url}")

        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(preview_url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[PREVIEW] server stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())