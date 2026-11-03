"""启动「验收」站本地服务。

【为什么需要单独脚本】
验收站的 index.html 在 验收/ 目录下，它用相对路径加载：
    fetch('models/catalog.json')
    fetch('models/roadmap.json')
    src="models/preview_sofa_studio.png"
这些相对路径是相对于【页面所在目录 验收/】解析的。
如果用项目根目录起服务（python -m http.server），页面里的
'models/xxx' 会解析到 <项目根>/models/xxx —— 不存在 → 404。

所以验收站必须以 验收/ 为服务根目录启动。
主程序则是另一种情况：assets/template.html 用 fetch("furnlib/index.json")，
相对 assets/ 解析，所以 furnlib 必须放在 assets/ 下（见 sync_furnlib.py）。

用法：
  python 验收/serve.py            # 默认 8099
  python 验收/serve.py 8123       # 指定端口
"""
import http.server
import functools
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099


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
    print('验收站 -> http://127.0.0.1:%d/index.html' % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
