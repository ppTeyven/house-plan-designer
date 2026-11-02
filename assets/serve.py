import http.server, functools, os

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8899

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    def log_message(self, *a):
        pass

if __name__ == '__main__':
    handler = functools.partial(H, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    srv.serve_forever()
