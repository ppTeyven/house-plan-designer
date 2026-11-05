# -*- coding: utf-8 -*-
"""把 assets/furnlib/ 的模型同步成 验收/models/ 的工作副本。

【为什么需要】
  assets/furnlib/ 是家具模型的**唯一真源**（运行时依赖，见 assets/furnlib/index.json）。
  历史上 验收/models/ 还存了一份同名 .glb 副本，两份字节完全相同（实测 251/251），
  导致仓库凭空多出 66MB，且两边很容易不同步（HEAD 上就已经出现内容不一致）。

  现在把 验收/models/*.glb 加入 .gitignore —— 仓库只保留真源。
  但本地工具链（analyze_*.py / audit_*.py / check_*.py）仍按约定读
  验收/models/ 下的 .glb，所以需要一个可重复执行的同步动作。

  验收站前端（验收/app.js）已改为直接读 ../assets/furnlib/，不再依赖副本。

用法：
  python sync_furnlib_to_accept.py            # 增量同步（只复制缺失/不同的）
  python sync_furnlib_to_accept.py --check    # 只报告差异，不写入
  python sync_furnlib_to_accept.py --prune    # 删掉副本里多出来的孤儿文件
"""
import argparse
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FURNLIB = os.path.join(ROOT, "assets", "furnlib")
ACCEPT = os.path.join(ROOT, "验收", "models")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告差异，不写入")
    ap.add_argument("--prune", action="store_true", help="删除副本里多出的孤儿 glb")
    args = ap.parse_args()

    if not os.path.isdir(FURNLIB):
        print("ERR: 真源目录不存在:", FURNLIB)
        return 1
    os.makedirs(ACCEPT, exist_ok=True)

    src_files = sorted(f for f in os.listdir(FURNLIB) if f.endswith(".glb"))
    copied = missing = same = 0
    for name in src_files:
        src = os.path.join(FURNLIB, name)
        dst = os.path.join(ACCEPT, name)
        if not os.path.exists(dst):
            missing += 1
            if not args.check:
                shutil.copy2(src, dst)
                print("copy  ", name)
        elif sha256(src) != sha256(dst):
            missing += 1
            if not args.check:
                shutil.copy2(src, dst)
                print("sync  ", name, "(内容不同)")
        else:
            same += 1

    pruned = 0
    if args.prune:
        src_set = set(src_files)
        for name in os.listdir(ACCEPT):
            if name.endswith(".glb") and name not in src_set:
                if not args.check:
                    os.remove(os.path.join(ACCEPT, name))
                pruned += 1
                print("prune ", name)

    total = len(src_files)
    print("\n真源 assets/furnlib/ : %d 个 glb" % total)
    print("副本 验收/models/    : 同步 %d, 已一致 %d%s"
          % (missing, same, (", 清理孤儿 %d" % pruned) if pruned else ""))
    if args.check and missing:
        print("\n有 %d 个副本缺失/不一致，运行不带 --check 即可同步。" % missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
