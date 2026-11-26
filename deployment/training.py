"""Serve only the bundled fictional website on a separate loopback origin."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import functools
import webbrowser

ROOT = Path(__file__).resolve().parents[1] / "training"
PORT = 18086

class TrainingHandler(SimpleHTTPRequestHandler):
    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        if urlsplit(self.path).path not in {"/", "/index.html", "/design-system.html", "/styles/rollflow-design.css"}:
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        if urlsplit(self.path).path not in {"/", "/index.html", "/design-system.html", "/styles/rollflow-design.css"}:
            self.send_error(404)
            return
        super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data: blob:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        super().end_headers()

def main():
    if not (ROOT / "index.html").is_file():
        raise SystemExit("Training demo files are missing. Extract a complete RollFlow bundle.")
    handler = functools.partial(TrainingHandler, directory=str(ROOT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    except OSError as exc:
        raise SystemExit("Training port is in use. Close the previous training session or contact ICT.") from exc
    url = f"http://127.0.0.1:{PORT}/"
    print("Fictional training only. Do not enter real student or staff data.")
    print(url + " — close this window to stop training.")
    webbrowser.open(url)
    with server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
