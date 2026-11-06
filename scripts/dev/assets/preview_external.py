"""外部模型处理后的【质量核验】—— 渲染出来亲眼看，不能只看数字。

用户要求："找好以后将验收界面里所有的物品全部替换不能有疏漏"
以及"必须找与原本建模形状大小完全一致的模型""每个家具的正确方向搞清楚"

本脚本对处理后的 GLB 做：
  ① 三视角渲染（正/侧/3/4）
  ② 落地检查（底面 z=0）
  ③ 输出到 scripts/dev/_previews/ext_<slug>.png 供人工比对

用法：blender --background --python preview_external.py -- [--only slug,slug]
"""
import bpy
import sys
import os
import math
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "dev", "blender"))

# 复用项目既有的棚拍灯光配置
import render_preview as RP   # noqa

OUTDIR = os.path.join(ROOT, "scripts", "dev", "_previews")
SRC = os.path.join(ROOT, "assets", "external", "processed")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))

    os.makedirs(OUTDIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".glb"))
    if only:
        files = [f for f in files if f[:-4] in only]
    print("[PREVIEW] 处理 %d 个" % len(files))

    for f in files:
        slug = f[:-4]
        try:
            RP.preview(os.path.join(SRC, f),
                       os.path.join(OUTDIR, "ext_%s.png" % slug))
            print("[PREVIEW] OK", slug)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("[PREVIEW] FAIL", slug, e)


if __name__ == "__main__":
    main()
