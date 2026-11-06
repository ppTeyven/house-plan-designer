"""把 assets/furnlib/*.glb 同步到主程序的高清家具库 assets/furnlib/（按款式 key）。

【为什么必须做】
  主程序 assets/template.html 里：
      const r = await fetch("furnlib/index.json");
      __FURN.set(k, {g, w, h, d})        ← 【v2】键改为款式 key
      __g.scale.set(i/__m.w, o/__m.h, s/__m.d);
  → furnlib/ 必须存在，否则 fetch 404 → __FURN 为空
  → 所有家具都在跑 `switch(n.type)` 的程序化分支（几个 Box/Cylinder 拼的）
  → 这就是"整体依旧是简陋几何体拼凑的"的【真正根源】

【与旧版 sync_furnlib.py 的区别】
  旧版：只同步 8 个 type（sofa/bed/chair/...），且在 Blender 里重导出。
       一个 type 的所有款式共用一个模型 → 同 type 不同尺寸会被拉伸变形。
  新版：同步【全部 251 个款式 key】，每个 key 一个 GLB，
       直接复制字节（不再走 Blender 重导出）——
       因为验收站的 GLB 已经是 Y-up、已落地、已居中、尺寸精确，
       再过一遍 Blender 反而有把轴序搞错的风险
       （旧 sync_furnlib.py 的注释里就记着"手动转两次 → 家具躺倒"的坑）。

【尺寸口径】
  验收站 GLB：Y-up（y=高），已落地（min y=0）、已水平居中。
  主程序读取 setFromObject(g).getSize() → (x, y, z) = (w, h, d) —— 口径一致。

用法：python sync_furnlib_full.py [--dry]
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SRC = os.path.join(ROOT, "assets", "furnlib")
DST = os.path.join(ROOT, "assets", "furnlib")
TEX_DST = os.path.join(DST, "tex")


def _copy_atomic(src, dst):
    """原子复制：先写 .tmp，再 os.replace。

    【为什么要原子替换】
      Windows 上浏览器可能正持有目标文件句柄。
      直接 shutil.copyfile 会中途失败（Errno 22），
      留下【半个文件】—— 验收站加载到损坏的 GLB 就直接白屏。
      写 .tmp + os.replace 保证目标文件要么是旧的完整版，
      要么是新的完整版，不会出现半截。
    """
    tmp = dst + ".tmp"
    shutil.copyfile(src, tmp)
    for _ in range(5):
        try:
            os.replace(tmp, dst)
            return True
        except OSError:
            import time
            time.sleep(0.3)
    # 最后尝试：直接覆盖
    try:
        shutil.copyfile(src, dst)
        if os.path.exists(tmp):
            os.remove(tmp)
        return True
    except OSError:
        return False


def main():
    dry = "--dry" in sys.argv

    # 目录条目（款式 key 是唯一真源）
    cat = json.load(open(os.path.join(SRC, "catalog.json"), encoding="utf-8"))
    entries = []
    for g in cat["groups"]:
        for it in g["items"]:
            entries.append((it["key"], it.get("file") or (it["key"] + ".glb")))

    if not dry:
        os.makedirs(DST, exist_ok=True)
        os.makedirs(TEX_DST, exist_ok=True)

    index = {}
    missing = []
    failed = []
    total = 0
    for key, fn in entries:
        src = os.path.join(SRC, fn)
        if not os.path.exists(src):
            missing.append(key)
            continue
        dst = os.path.join(DST, fn)
        if not dry:
            if not _copy_atomic(src, dst):
                failed.append(key)
                continue
        sz = os.path.getsize(src)
        total += sz
        index[key] = {"file": fn}

    if not dry:
        with open(os.path.join(DST, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=1)

    print("款式数: %d" % len(entries))
    print("已同步: %d" % len(index))
    print("总大小: %.1f MB" % (total / 1048576))
    print("index.json -> %s" % os.path.join(DST, "index.json"))
    if missing:
        print("缺模型 %d 个: %s" % (len(missing), missing[:20]))
    if failed:
        print("复制失败 %d 个: %s" % (len(failed), failed[:20]))
    return 1 if (missing or failed) else 0


if __name__ == "__main__":
    sys.exit(main())
