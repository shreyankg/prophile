#!/usr/bin/env python3
"""Dependency-free localhost server for Roast Profile Overlay."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .roast_parser import RoastParseError, parse_alog

HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"


class AppServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], profile_dir: Path):
        super().__init__(address, AppHandler)
        self.profile_dir = profile_dir


class AppHandler(BaseHTTPRequestHandler):
    server_version = "RoastProfileOverlay/1.0"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/api/parse":
            self._json(404, {"error": "Not found."})
            return

        filename = unquote(self.headers.get("X-Filename", ""))
        profile_id = self.headers.get("X-Profile-Id", "")
        if not filename.lower().endswith(".alog"):
            self._json(415, {"error": "Only .alog files are supported."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Invalid upload length."})
            return
        if length <= 0:
            self._json(400, {"error": "The selected file is empty."})
            return
        if length > MAX_UPLOAD_BYTES:
            self._json(413, {"error": "The selected file exceeds the 5 MB limit."})
            return

        raw = self.rfile.read(length)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            self._json(400, {"error": "The .alog file is not valid UTF-8 text."})
            return

        try:
            profile = parse_alog(text, filename, profile_id)
        except RoastParseError as exc:
            self._json(422, {"error": str(exc)})
            return
        except Exception:
            self._json(500, {"error": "The profile could not be processed."})
            return
        self._json(200, profile)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/api/local-profiles":
            profiles = []
            errors = []
            directory = self.server.profile_dir
            try:
                files = sorted(directory.iterdir(), key=lambda file: file.name.casefold())
            except OSError as exc:
                self._json(500, {"error": f"Cannot list profiles in {directory}: {exc}"})
                return
            for file in files:
                if file.suffix.lower() != ".alog" or not file.is_file():
                    continue
                try:
                    # Never follow a symlink outside the directory being served.
                    if file.resolve().parent != directory:
                        continue
                    if file.stat().st_size > MAX_UPLOAD_BYTES:
                        raise RoastParseError("File exceeds the 5 MB limit.")
                    profile = parse_alog(file.read_text(encoding="utf-8"), file.name, f"local:{file.name}")
                    profile["fileSize"] = file.stat().st_size
                    profiles.append(profile)
                except (OSError, UnicodeError, RoastParseError) as exc:
                    errors.append(f"{file.name}: {exc}")
            self._json(200, {"profiles": profiles, "errors": errors, "directory": str(directory)})
            return
        if path == "/":
            path = "/index.html"
        relative = path.lstrip("/")
        candidate = (STATIC_DIR / relative).resolve()
        try:
            candidate.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            self.send_error(404)
            return

        body = candidate.read_bytes()
        content_type, _ = mimetypes.guess_type(candidate.name)
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Roast Profile Overlay web app.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="localhost port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    profile_dir = Path.cwd().resolve()
    server = AppServer((HOST, args.port), profile_dir)
    print(f"Roast Profile Overlay is running at http://{HOST}:{args.port}")
    print(f"Loading .alog files from {profile_dir}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
