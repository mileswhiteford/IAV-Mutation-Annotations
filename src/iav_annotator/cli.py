import argparse
import socket
import threading
import webbrowser
from pathlib import Path

import uvicorn

from .app import create_app, default_database
from .resources import PACKAGE


def main():
    parser = argparse.ArgumentParser(description="Open the local IAV literature annotator")
    parser.add_argument("--database", type=Path, default=default_database(), help="Local SQLite file")
    parser.add_argument("--port", type=int, default=0, help="Loopback port (default: choose a free port)")
    parser.add_argument("--no-browser", action="store_true", help="Print the URL without opening it")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    if not (PACKAGE / "static" / "index.html").is_file():
        parser.error("Frontend assets are missing. Developers: run npm ci and npm run build in frontend/ first.")
    try:
        app = create_app(args.database)
    except ValueError as exc:
        parser.error(str(exc))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", args.port))
        listener.listen(128)
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        print(f"IAV Annotator: {url}\nDatabase: {args.database.resolve()}\nPress Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            timer = threading.Timer(1, webbrowser.open, args=(url,))
            timer.daemon = True
            timer.start()
        # Reserve the socket before opening the browser, including when port=0.
        uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[listener])


if __name__ == "__main__":
    main()
