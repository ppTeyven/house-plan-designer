"""极简图片收集服务：接收浏览器 POST 的 base64 图片并存盘。

【为什么需要】CDP 单次响应上限 25KB，WebGL 截图有几百 KB，
拿不回本地。起一个本地 POST 收集器，让页面直接把图发过来。

用法：python collect_img.py 8123
然后在页面里 fetch('http://127.0.0.1:8123/save?name=xxx', {method:'POST',body:dataURL})
"""
import base64
import http.server
import json
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                  "assets", "_shots"))
os.makedirs(OUT, exist_ok=True)


class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        name = "img.png"
        if "?" in self.path:
            q = self.path.split("?", 1)[1]
            for kv in q.split("&"):
                if kv.startswith("name="):
                    name = kv[5:]
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            body = json.loads(raw.decode("utf-8"))
            payload = body if isinstance(body, str) else body.get("data", "")
        except Exception:
            payload = raw.decode("utf-8", "replace")
        if payload.startswith("data:"):
            payload = payload.split(",", 1)[1]
        try:
            data = base64.b64decode(payload)
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(("bad b64: %s" % e).encode())
            return
        safe = "".join(c for c in name if c.isalnum() or c in "._-")
        path = os.path.join(OUT, safe or "img.png")
        with open(path, "wb") as f:
            f.write(data)
        print("saved %s  %d bytes" % (path, len(data)), flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "path": path,
                                     "bytes": len(data)}).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("collector -> http://127.0.0.1:%d/save?name=x.png" % PORT, flush=True)
    srv.serve_forever()
