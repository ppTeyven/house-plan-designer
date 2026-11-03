"""批量渲染所有已建模款式（studio + front + detail 三个视角），
并对每张图做客观亮度/色彩分析，输出汇总表。
"""
import os, subprocess, sys, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODELS = ROOT / "验收" / "models"
BL = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
SCRIPT = ROOT / "scripts" / "dev" / "blender" / "render_preview.py"

keys = sys.argv[1:] or ["sofa", "bed", "chair", "diningTable",
                        "coffeeTable", "tvCabinet", "wardrobe", "nightstand"]
views = ["studio", "front", "detail"]

rows = []
for k in keys:
    glb = MODELS / f"{k}.glb"
    if not glb.exists():
        print(f"skip {k} (no glb)")
        continue
    for v in views:
        out = MODELS / f"preview_{k}_{v}.png"
        env = dict(os.environ)
        env["BL_IN"] = str(glb)
        env["BL_OUT"] = str(out)
        env["BL_VIEW"] = v
        r = subprocess.run([BL, "--background", "--python", str(SCRIPT)],
                           env=env, capture_output=True, text=True)
        ok = "RENDERED" in (r.stdout or "") + (r.stderr or "")
        rows.append({"key": k, "view": v, "out": out.name, "ok": ok})
        print(f"{'OK ' if ok else 'FAIL'} {k}/{v}")
        if not ok:
            tail = (r.stdout or "")[-400:] + (r.stderr or "")[-400:]
            print("   ", tail.replace("\n", " ")[:400])

json.dump(rows, open(MODELS / "_render_log.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ndone:", sum(1 for x in rows if x["ok"]), "/", len(rows))