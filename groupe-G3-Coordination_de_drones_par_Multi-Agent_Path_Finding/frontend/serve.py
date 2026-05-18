"""Dev HTTP server with Cache-Control: no-store to avoid stale JS modules."""
from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    print("Frontend dev server on http://localhost:8080 (no-cache)")
    HTTPServer(("", 8080), NoCacheHandler).serve_forever()
