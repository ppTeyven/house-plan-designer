"""验收站 251 件模型全量自检 —— 逐个 GET 每个 GLB，校验 HTTP 状态 / 体积 / GLB 魔数 / 三角面数。

用法：python verify_all_251.py [base_url] [--browser]
"""
import json
import os
import struct
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8099"
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    BASE = sys.argv[1].rstrip("/")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CATALOG = os.path.join(ROOT, "assets", "furnlib", "index.json")


def load_catalog():
    global CATALOG
    if not os.path.exists(CATALOG):
        cands = []
        for base in [ROOT, os.path.dirname(ROOT)]:
            for rel in ["assets/furnlib/index.json", "验收/models/catalog.json",
                        "assets/models/catalog.json", "验收/assets/models/catalog.json"]:
                p = os.path.join(base, rel.replace("/", os.sep))
                if os.path.exists(p):
                    cands.append(p)
        if not cands:
            sys.exit("找不到 catalog：%s" % CATALOG)
        CATALOG = cands[0]
    with open(CATALOG, encoding="utf-8") as f:
        return CATALOG, json.load(f)


def glb_stats(blob):
    """返回 (顶点数, 三角面数, 材质名列表)"""
    if len(blob) < 12 or blob[:4] != b"glTF":
        return None
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    bin_ = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        chunk = blob[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    if js is None:
        return None
    verts = 0
    tris = 0
    mats = set()
    for m in js.get("meshes", []):
        for pr in m.get("primitives", []):
            attrs = pr.get("attributes", {})
            if "POSITION" in attrs:
                verts += js["accessors"][attrs["POSITION"]]["count"]
            idx = pr.get("indices")
            if idx is not None:
                tris += js["accessors"][idx]["count"] // 3
            mat = pr.get("material")
            if mat is not None:
                nm = js["materials"][mat].get("name", "")
                if nm:
                    mats.add(nm)
    return verts, tris, sorted(mats)


def main():
    cat_path, cat = load_catalog()
    items = cat["items"] if isinstance(cat, dict) and "items" in cat else cat
    if isinstance(items, dict):
        items = list(items.values())
    print("=" * 78)
    print("全量验收 %d 件模型  ->  %s" % (len(items), BASE))
    print("catalog: %s" % cat_path)
    print("=" * 78)

    ok = 0
    fail = 0
    empty = []
    no_mat = []
    errs = []
    total_mb = 0.0
    for i, it in enumerate(items, 1):
        rel = it.get("url") or it.get("file") or it.get("path") or ""
        if not rel:
            rel = "models/%s.glb" % it.get("id")
        rel = rel.lstrip("/")
        if rel.startswith("models/"):
            url = "%s/%s" % (BASE, rel)
        else:
            url = "%s/models/%s" % (BASE, rel)
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as r:
                blob = r.read()
            if len(blob) < 12 or blob[:4] != b"glTF":
                errs.append((rel, "bad magic"))
                fail += 1
                continue
            st = glb_stats(blob)
            if st is None:
                errs.append((rel, "parse fail"))
                fail += 1
                continue
            verts, tris, mats = st
            total_mb += len(blob) / 1048576.0
            if tris <= 0:
                empty.append(rel)
                fail += 1
                continue
            if not mats:
                no_mat.append(rel)
            ok += 1
            if i <= 6 or i % 50 == 0:
                print("  [%3d/%d] %-28s %7.2f MB  verts=%-7d tris=%-8d mats=%s"
                      % (i, len(items), rel.split("/")[-1][:28], len(blob) / 1048576.0,
                         verts, tris, ",".join(mats) or "(none)"))
        except urllib.error.HTTPError as e:
            errs.append((rel, "HTTP %d" % e.code))
            fail += 1
        except Exception as e:
            errs.append((rel, str(e)[:60]))
            fail += 1

    print("-" * 78)
    print("  通过 %d / 失败 %d   总体积 %.1f MB" % (ok, fail, total_mb))
    if no_mat:
        print("  ⚠ 无材质名 %d 个: %s" % (len(no_mat), ", ".join(no_mat[:8])))
    if empty:
        print("  ✗ 零三角面 %d 个: %s" % (len(empty), ", ".join(empty[:8])))
    if errs:
        print("  ✗ 错误 %d 个:" % len(errs))
        for r, e in errs[:15]:
            print("      %-30s %s" % (r, e))
    print("=" * 78)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
