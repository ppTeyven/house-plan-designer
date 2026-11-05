"""验收站资源自检 —— 确认新模型能被前端加载。

用法：python check_acceptance.py [base_url]
"""
import sys
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8099"

PATHS = [
    ("index.html", "text/html"),
    ("app.js", "javascript"),
    ("styles.css", "css"),
    ("models/catalog.json", "json"),
    ("models/sofa.glb", "glb"),
    ("models/bed.glb", "glb"),
    ("models/preview_sofa_studio.png", "png"),
    ("vendor/three.module.js", "js"),
]

print("=" * 72)
print("验收站资源自检  ->  %s" % BASE)
print("=" * 72)

ok = 0
fail = 0
for path, kind in PATHS:
    url = "%s/%s" % (BASE, path)
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            size = r.headers.get("Content-Length", "?")
            print("  [OK]   %-38s %s  %s bytes" % (path, r.status, size))
            ok += 1
    except urllib.error.HTTPError as e:
        print("  [%s] %-38s HTTP %s" % ("FAIL", path, e.code))
        fail += 1
    except Exception as e:
        print("  [%s] %-38s %s" % ("FAIL", path, e))
        fail += 1

print("-" * 72)
print("  通过 %d / 失败 %d" % (ok, fail))
