"""对「二次单位换算修复」涉及的款式批量重嵌 PBR 贴图。

用法：python embed_pbr_mm.py [--apply]
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

KEYS = [
    "barCounter", "barStool", "bayCushion", "booth", "bunkBed",
    "cabCorner", "cabSlide", "cabTV", "crib", "curveTrainingTable",
    "fireplace", "gamingChair", "lDesk", "lectern", "ovalTable",
    "reception", "speaker", "tatami", "theaterSofa",
]

apply_flag = ["--apply"] if "--apply" in sys.argv else []
fail = []
for k in KEYS:
    cmd = [sys.executable, os.path.join(HERE, "embed_pbr.py"),
           "--only", k] + apply_flag
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        fail.append((k, out.strip()[-300:]))
        print("FAIL %-18s" % k)
    else:
        line = [l for l in out.splitlines() if l.strip().startswith(k)]
        print("OK   %-18s %s" % (k, line[0].strip() if line else ""))

if fail:
    print("\n失败 %d 个:" % len(fail))
    for k, e in fail:
        print("  ", k, e)
    sys.exit(1)
print("\n全部 %d 项完成" % len(KEYS))
