# -*- coding: utf-8 -*-
"""检查本地静态服务器是否在运行，缺失则自动拉起。

【为什么需要这个】
本项目的页面（assets/template.html）通过相对路径加载：
    furnlib/index.json      家具模型索引
    furnlib/*.glb           251 个家具模型
    furnlib/tex/*.jpg       195 张 PBR 扫描贴图
如果静态服务器没起来，这些全部 404 ->
    · 家具材质退化成默认灰白（"材质变样"）
    · 房间铺装贴图加载失败（"地板没了"）
    · 环境贴图缺失 -> 光影异常
所以服务器必须常驻，不能被"清理进程"误杀。

用法：
    python scripts/dev/blender/ensure_server.py          # 检查+拉起
    python scripts/dev/blender/ensure_server.py --check  # 只检查不拉起
"""
import http.server
import os
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
# scripts/dev/blender -> 项目根
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ASSETS = os.path.join(ROOT, 'assets')

PORTS = {
    8100: ASSETS,   # 主程序（template.html）
    8899: ASSETS,   # 主程序（serve.py，no-store 头）
    8124: os.path.join(ROOT, '验收'),  # 验收站
    # 注意：8123 被 collect_img.py 占用，不要用。
}


def is_up(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.6)
    try:
        s.connect(('127.0.0.1', port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def serve_forever(port, root):
    class H(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # 必须 no-store：否则浏览器缓存会造成"改了没生效"的假象
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            super().end_headers()

        def log_message(self, *a):
            pass

    handler = lambda *a, **kw: H(*a, directory=root, **kw)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    srv.serve_forever()


def main():
    check_only = '--check' in sys.argv
    missing = [p for p in PORTS if not is_up(p)]

    for p in sorted(PORTS):
        print('port %-5d %-8s root=%s' % (
            p, 'UP' if is_up(p) else 'DOWN', PORTS[p]))

    if not missing:
        print('\n所有静态服务器正常。')
        return 0

    if check_only:
        print('\n缺失: %s（--check 模式不拉起）' % missing)
        return 1

    print('\n拉起缺失的服务器: %s' % missing)
    for p in missing:
        root = PORTS[p]
        if not os.path.isdir(root):
            print('  跳过 %d：目录不存在 %s' % (p, root))
            continue
        t = threading.Thread(target=serve_forever, args=(p, root), daemon=True)
        t.start()
        print('  已在后台启动 %d -> %s' % (p, root))

    import time
    time.sleep(1.2)
    ok = True
    for p in missing:
        up = is_up(p)
        print('  %d %s' % (p, 'OK' if up else 'FAIL'))
        ok = ok and up
    print('\n完成。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
