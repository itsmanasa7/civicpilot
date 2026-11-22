import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MIRROR_DIR = Path(__file__).resolve().parent.parent / "mirror"


class MirrorRequestHandler(SimpleHTTPRequestHandler):
    """Custom handler serving mirror static files with CORS headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(MIRROR_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # Keep logs concise
        sys.stderr.write(f"[PM-KISAN Mirror:4000] {args[0]} {args[1]}\n")


_server_instance: ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None


def start_mirror_in_background(port: int = 4000) -> ThreadingHTTPServer:
    """Starts the mirror server in a background daemon thread if not already running."""
    global _server_instance, _server_thread

    # Check if port is already listening
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_open = sock.connect_ex(("127.0.0.1", port)) == 0
    sock.close()
    if is_open:
        print(f"[PM-KISAN Mirror] Port {port} is already active.")
        return _server_instance

    _server_instance = ThreadingHTTPServer(("0.0.0.0", port), MirrorRequestHandler)
    _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
    _server_thread.start()
    print(f"[PM-KISAN Mirror] Server started in background on http://localhost:{port} (serving {MIRROR_DIR})")
    time.sleep(0.2)
    return _server_instance


def run_standalone(port: int = 4000):
    server = ThreadingHTTPServer(("0.0.0.0", port), MirrorRequestHandler)
    print(f"[PM-KISAN Mirror] Serving {MIRROR_DIR} at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[PM-KISAN Mirror] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    run_standalone(port_arg)
