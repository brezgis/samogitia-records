"""Static file server for the book and review sites with correct media types.

Python's default server sends .webp as application/octet-stream, which Safari refuses to
draw as an image (the book's ribbon). Usage:
  python3 site/serve.py PORT BIND_ADDRESS DIRECTORY
"""
import functools
import http.server
import sys

TYPES = {'.webp': 'image/webp', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
         '.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml', '.woff2': 'font/woff2'}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TYPES}

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')   # rebuilt data shows up on reload
        super().end_headers()


if __name__ == '__main__':
    port, bind, directory = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    http.server.ThreadingHTTPServer((bind, port), functools.partial(Handler, directory=directory)).serve_forever()
