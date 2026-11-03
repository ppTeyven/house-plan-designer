"""打印验收站当前所有已建模款式的体检结果（哪些达标、哪些有偏差）。"""
import json, pathlib

p = pathlib.Path(__file__).resolve().parents[3] / "验收" / "models" / "manifest.json"
m = json.load(open(p, encoding="utf-8"))
print(f"{'key':<14}{'状态':<6}{'三角面':>10}  {'材质':>4}   偏差项")
print("-" * 76)
for it in m.get("items", []):
    if it.get("status") in (None, "none"):
        continue
    bad = [c for c in it.get("checks", []) if c.get("level") != "ok"]
    print(f"{it['key']:<14}{it['status']:<6}{it['tris']:>10,}  {len(it.get('materials', [])):>4}   "
          + ("全部通过" if not bad else ""))
    for c in bad:
        print(f"      [{c['level']}] {c['text']} → {c['value']}")

none_cnt = sum(1 for it in m.get("items", []) if it.get("status") in (None, "none"))
print("-" * 76)
print(f"已建模 {len(m.get('items', [])) - none_cnt} 件，待建模 {none_cnt} 件")