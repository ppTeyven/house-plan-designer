# -*- coding: utf-8 -*-
"""本地截图接收端：浏览器 POST base64 PNG -> 落盘。

用途：three.js WebGL 默认 preserveDrawingBuffer=false，
浏览器截图工具抓到的是空帧（经典假象）。这里让页面在【同一次 JS 调用里】
同步渲染 + toDataURL，再 POST 回来，得到真实画面。

用法：python _shot_server.py [port]
"""
import base64
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_shots')
os.makedirs(OUT, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n)
        try:
            payload = json.loads(raw.decode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self._cors()
            self.end_headers()
            self.wfile.write(b'bad json')
            return
        name = os.path.basename(payload.get('name') or 'shot') + '.png'
        data = payload.get('data') or ''
        if ',' in data:
            data = data.split(',', 1)[1]
        try:
            buf = base64.b64decode(data)
        except Exception as e:
            self.send_response(400)
            self._cors()
            self.end_headers()
            self.wfile.write(str(e).encode())
            return
        path = os.path.join(OUT, name)
        with open(path, 'wb') as f:
            f.write(buf)
        print('saved', path, len(buf), 'bytes', flush=True)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'path': path, 'bytes': len(buf)}).encode())

    def do_GET(self):
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b'shot-server ok')

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8131
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
