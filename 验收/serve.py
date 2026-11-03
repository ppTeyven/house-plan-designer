"""验收站服务：静态文件 + no-store 禁缓存头（附录A 三层对账前提）."""
import http.server, socketserver, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def guess_type(self, path):
        # 显式指定 JSON / JS / GLB 的 MIME，否则 JSON 会以 text/plain 返回，
        # 中文乱码导致 JSON.parse 失败
        p = str(path).lower()
        if p.endswith(".json"):
            return "application/json; charset=utf-8"
        if p.endswith(".js") or p.endswith(".mjs"):
            return "text/javascript; charset=utf-8"
        if p.endswith(".html") or p.endswith(".htm"):
            return "text/html; charset=utf-8"
        if p.endswith(".css"):
            return "text/css; charset=utf-8"
        if p.endswith(".glb"):
            return "model/gltf-binary"
        if p.endswith(".png"):
            return "image/png"
        if p.endswith(".jpg") or p.endswith(".jpeg"):
            return "image/jpeg"
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] %s\n" % (fmt % args))


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    os.chdir(ROOT)
    print("验收站: http://127.0.0.1:%d/index.html" % PORT, flush=True)
    S(("127.0.0.1", PORT), H).serve_forever()
