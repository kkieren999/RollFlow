"""Serve only the bundled fictional website on a separate loopback origin."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import functools
import webbrowser

ROOT = Path(__file__).resolve().parents[1] / "training"
PORT = 18086

class TrainingHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlsplit(self.path).path not in {"/", "/index.html", "/design-system.html", "/styles/rollflow-design.css"}:
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path not in {"/", "/index.html", "/design-system.html", "/styles/rollflow-design.css"}:
            self.send_error(404)
            return
        super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
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
