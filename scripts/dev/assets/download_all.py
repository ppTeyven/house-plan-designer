"""统一下载编排器：把 Poly Haven 映射 + 多源缺口映射合并，按 type 下载。

【流程】
  ① 读 assets/external/catalog_map.json（Poly Haven 候选）
  ② 读 assets/external/gap_map.json（多源候选）
  ③ 合并为 type → 候选列表（Poly Haven 优先）
  ④ 逐 type 下载首选候选；失败则回退到第 2、3 候选
  ⑤ 记录到 assets/external/plan.json（含 provider/license/来源 url，可追溯）

【为什么不直接下载再处理】
先做映射再下载，是因为下载要带贴图（动辄几十 MB）。
先把"哪个 type 用哪个资产"定下来，能避免重复下载与错配。

用法：
  python download_all.py --dry-run          # 只看计划
  python download_all.py --type sofa        # 只下指定 type
  python download_all.py --limit 20         # 下前 20 个
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

import fetch_multi as FM          # noqa
import fetch_assets as FA         # noqa

EXT = os.path.join(ROOT, "assets", "external")
PLAN = os.path.join(EXT, "plan.json")


def load_maps():
    ph = {}
    gp = {}
    p1 = os.path.join(EXT, "catalog_map.json")
    p2 = os.path.join(EXT, "gap_map.json")
    if os.path.exists(p1):
        with open(p1, encoding="utf-8") as f:
            ph = json.load(f)
    if os.path.exists(p2):
        with open(p2, encoding="utf-8") as f:
            gp = json.load(f)
    return ph, gp


def merge_maps(ph, gp):
    """type → [ {source, slug/id, dims_mm, ...} ]"""
    out = {}
    for t, v in ph.items():
        cands = []
        for c in (v.get("candidates") or [])[:3]:
            cands.append({
                "source": "polyhaven",
                "slug": c["slug"],
                "id": "polyhaven:%s" % c["slug"],
                "dims_mm": c.get("dims_mm"),
                "tri": c.get("tri"),
                "score": c.get("score"),
                "why": c.get("why"),
            })
        out[t] = {"candidates": cands, "size_mm": v.get("size_mm"),
                  "style": v.get("style")}
    for t, v in gp.items():
        cands = out.setdefault(t, {"candidates": []})
        cands.setdefault("size_mm", None)
        for c in (v.get("candidates") or [])[:3]:
            cands["candidates"].append({
                "source": "shep:%s" % c.get("provider"),
                "slug": c.get("nativeId"),
                "id": c.get("id"),
                "title": c.get("title"),
                "license": c.get("license"),
                "tri": c.get("polyCount"),
                "url": c.get("url"),
            })
    return out


def download_polyhaven(slug, dest):
    """走 Poly Haven 官方 API（带 md5 校验 + 贴图依赖）"""
    try:
        r = FA.fetch_one(slug, "2k", dest)
        return True, r
    except Exception as e:
        return False, str(e)


def download_shep(aid, dest):
    try:
        d, files = FM.download_asset(aid, dest_root=dest)
        if d is None:
            return False, str(files)
        return True, {"dir": d, "files": files}
    except Exception as e:
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--type", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--types-only", action="store_true")
    args = ap.parse_args()

    ph, gp = load_maps()
    merged = merge_maps(ph, gp)
    print("Poly Haven 覆盖 type: %d" % len(ph))
    print("多源补充 type:       %d" % len(gp))
    print("合计 type:           %d" % len(merged))

    # 目录里所有 type（用于查漏）
    with open(os.path.join(ROOT, "验收", "models", "catalog.json"),
              encoding="utf-8") as f:
        cat = json.load(f)
    all_types = sorted({it["type"] for g in cat["groups"] for it in g["items"]})
    missing = [t for t in all_types if t not in merged]
    print("目录 type 总数: %d，仍未覆盖: %d" % (len(all_types), len(missing)))
    if missing:
        print("   ", ", ".join(missing))

    todo = []
    for t in all_types:
        if args.type and t != args.type:
            continue
        e = merged.get(t)
        if not e or not e.get("candidates"):
            continue
        todo.append((t, e))
    if args.limit:
        todo = todo[:args.limit]

    print("\n=== 计划下载 %d 个 type ===" % len(todo))
    for t, e in todo:
        c = e["candidates"][0]
        print("  %-20s <- %-42s %s" % (t, c.get("slug") or c.get("title"),
                                       c.get("source")))

    if args.types_only:
        return
    if args.dry_run:
        return

    rawroot = os.path.join(EXT, "raw")
    plan = []
    if os.path.exists(PLAN):
        with open(PLAN, encoding="utf-8") as f:
            plan = json.load(f)
    done = {p["type"] for p in plan if p.get("ok")}

    for i, (t, e) in enumerate(todo, 1):
        if t in done:
            print("[%3d/%3d] SKIP %s" % (i, len(todo), t))
            continue
        ok = False
        err = []
        for c in e["candidates"]:
            dest = os.path.join(rawroot, "%s__%s" % (t, c.get("slug") or "x"))
            if c.get("source") == "polyhaven":
                good, info = download_polyhaven(c["slug"], dest)
            else:
                good, info = download_shep(c["id"], dest)
            if good:
                ok = True
                plan.append({"type": t, "ok": True, "cand": c,
                             "dir": info.get("dir") if isinstance(info, dict) else dest,
                             "dims_mm": c.get("dims_mm")})
                print("[%3d/%3d] OK   %-20s %s" % (i, len(todo), t,
                                                  c.get("slug") or c.get("title")))
                break
            err.append("%s:%s" % (c.get("slug") or c.get("id"), info))
            print("[%3d/%3d] RETRY %-20s %s" % (i, len(todo), t, err[-1][:80]))
            time.sleep(0.2)
        if not ok:
            plan.append({"type": t, "ok": False, "errors": err,
                         "cand": e["candidates"][0]})
        with open(PLAN, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)

    print("\n完成。计划文件 ->", PLAN)


if __name__ == "__main__":
    main()
