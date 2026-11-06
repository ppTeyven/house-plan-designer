"""【材质规范修复】把残留的非 U_ 材质名改成 U_<role>。

【背景】
  kv() 的规则：材质名以 "U_" 开头 → 走 __furnMat(role) 挂外部扫描 PBR；
                否则 → 保留 GLB 自带材质。
  历史上有 2 件外部资源的材质名没带 U_ 前缀：
    miniHeater : vintage_electric_kettle
    wallClock  : wall_clock
  它们【自带内嵌贴图】，所以渲染上没坏（kv 会保留原材质），
  但破坏了"所有材质都遵循 U_<role> 规范"这条约定，
  验收脚本 / 贴图审计 / 后续换贴图流程都会漏掉它们。

【做法】
  只改材质名，不动贴图、不动几何、不动 buffer。
  映射：
    vintage_electric_kettle → U_metal_steel（电热水壶主体：金属）
    wall_clock               → U_metal_black（挂钟外框：金属）
  改完后它们会走 __furnMat 路径 —— 但 __GLB_PBR_ROLE 里有 metal_steel /
  metal_black，会挂上外部 role_* 扫描贴图，覆盖内嵌贴图。
  这是【期望行为】：全部家具统一走同一套 role PBR 管线。

【安全】
  写回时保持 GLB chunk 结构与 buffer 字节完全不变，只重写 JSON chunk。
"""
import hashlib
import json
import os
import struct
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FURN = os.path.join(ROOT, "assets", "furnlib")
ACCM = os.path.join(ROOT, "验收", "models")
CT_JSON = 0x4E4F534A
CT_BIN = 0x004E4942

RENAME = {
    "vintage_electric_kettle": "U_metal_steel",
    "wall_clock": "U_metal_black",
}


def read(path):
    with open(path, "rb") as f:
        blob = f.read()
    off = 12
    js = None
    bin_ = b""
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if ctype == CT_JSON:
            js = json.loads(data.decode("utf-8"))
        elif ctype == CT_BIN:
            bin_ = data
        off += 8 + clen
    return js, bin_


def write(path, js, bin_):
    jsb = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    jsb += b" " * ((4 - len(jsb) % 4) % 4)
    total = 12 + 8 + len(jsb) + (8 + len(bin_) if bin_ else 0)
    out = b"glTF" + struct.pack("<II", 2, total)
    out += struct.pack("<II", len(jsb), CT_JSON) + jsb
    if bin_:
        bb = bin_ + b"\x00" * ((4 - len(bin_) % 4) % 4)
        out += struct.pack("<II", len(bb), CT_BIN) + bb
    with open(path, "wb") as f:
        f.write(out)


def main():
    idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
    key2file = {}
    for k, v in idx.items():
        if isinstance(v, dict) and v.get("file"):
            key2file.setdefault(k, v["file"])

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(ROOT, "assets", "_asset_cache", "matfix_" + stamp)
    os.makedirs(bdir, exist_ok=True)

    n = 0
    for key, fn in key2file.items():
        p = os.path.join(FURN, fn)
        if not os.path.exists(p):
            continue
        js, bin_ = read(p)
        if not js:
            continue
        changed = False
        for m in js.get("materials") or []:
            old = m.get("name")
            if old in RENAME:
                m["name"] = RENAME[old]
                changed = True
                print("  %-16s %s -> %s" % (key, old, RENAME[old]))
        if not changed:
            continue
        shutil.copy2(p, os.path.join(bdir, fn))
        write(p, js, bin_)
        n += 1
        # 同步到验收站
        pa = os.path.join(ACCM, fn)
        if os.path.exists(pa):
            shutil.copy2(p, pa)

    print("\n改名 %d 件，备份 -> %s" % (n, bdir))
    if n:
        # 重打 index.json 哈希
        def sha1_8(x):
            h = hashlib.sha1()
            with open(x, "rb") as f:
                for c in iter(lambda: f.read(1 << 20), b""):
                    h.update(c)
            return h.hexdigest()[:8]
        idx = json.load(open(os.path.join(FURN, "index.json"), encoding="utf-8"))
        for k, v in idx.items():
            if isinstance(v, dict) and v.get("file"):
                fp = os.path.join(FURN, v["file"])
                if os.path.exists(fp):
                    v["v"] = sha1_8(fp)
        json.dump(idx, open(os.path.join(FURN, "index.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        print("index.json 哈希已重打")


if __name__ == "__main__":
    main()
