"""对比 验收/models/*.glb 与 assets/furnlib/*.glb 是否为同一批文件。

verify_all_251.py 之前是从 {BASE}/models/ 取文件校验的，
如果 验收/models 里还是旧模型，那次"251/251 通过"就验错了对象。

用法：python compare_models.py
"""
import hashlib
import json
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ACC = os.path.join(ROOT, "验收", "models")
NEW = os.path.join(ROOT, "assets", "furnlib")


def sha(path, n=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(n)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def glb_stats(path):
    with open(path, "rb") as f:
        blob = f.read()
    if blob[:4] != b"glTF":
        return None
    total = struct.unpack("<I", blob[8:12])[0]
    off = 12
    js = None
    while off + 8 <= min(total, len(blob)):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x4E4F534A:
            js = json.loads(blob[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    if js is None:
        return None
    tris = 0
    mats = set()
    for m in js.get("meshes", []):
        for pr in m.get("primitives", []):
            idx = pr.get("indices")
            if idx is not None:
                tris += js["accessors"][idx]["count"] // 3
            mat = pr.get("material")
            if mat is not None:
                nm = js["materials"][mat].get("name", "")
                if nm:
                    mats.add(nm)
    return tris, sorted(mats), len(blob)


acc_files = {os.path.splitext(f)[0]: os.path.join(ACC, f)
             for f in os.listdir(ACC) if f.endswith(".glb")}
new_files = {os.path.splitext(f)[0]: os.path.join(NEW, f)
             for f in os.listdir(NEW) if f.endswith(".glb")}

print("验收/models : %d 个 GLB, %.1f MB"
      % (len(acc_files), sum(os.path.getsize(p) for p in acc_files.values()) / 1048576.0))
print("assets/furnlib: %d 个 GLB, %.1f MB"
      % (len(new_files), sum(os.path.getsize(p) for p in new_files.values()) / 1048576.0))
print()

same = 0
diff = []
only_acc = set(acc_files) - set(new_files)
only_new = set(new_files) - set(acc_files)
for k in sorted(set(acc_files) & set(new_files)):
    if sha(acc_files[k]) == sha(new_files[k]):
        same += 1
    else:
        diff.append(k)

print("完全相同: %d" % same)
print("内容不同: %d" % len(diff))
print("只在验收/: %d  %s" % (len(only_acc), sorted(only_acc)[:10]))
print("只在furnlib: %d  %s" % (len(only_new), sorted(only_new)[:10]))
print()

print("=== 内容不同的模型（三角面 / 材质 / 体积）===")
print("%-22s %-34s %-34s" % ("id", "验收/models", "assets/furnlib"))
for k in diff[:30]:
    a = glb_stats(acc_files[k])
    b = glb_stats(new_files[k])
    fa = "%6d tri %6.2fMB %s" % (a[0], a[2] / 1048576.0, ",".join(a[1])[:14]) if a else "?"
    fb = "%6d tri %6.2fMB %s" % (b[0], b[2] / 1048576.0, ",".join(b[1])[:14]) if b else "?"
    print("%-22s %-34s %-34s" % (k, fa, fb))
