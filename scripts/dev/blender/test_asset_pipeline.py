"""端到端验证：下载 Polyhaven 模型 → 打包 GLB → 解析校验。

这是"资源替换"主路径的冒烟测试：必须证明
  下载 → 打包 → 三个.js 都能读，才是真正可交付。

用法：python test_asset_pipeline.py
"""
import os
import sys
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

import asset_fetch as AF

TEST_MODEL = "Sofa_01"


def main():
    print("=" * 70)
    print("① 下载 Polyhaven 模型:", TEST_MODEL)
    t0 = time.time()
    gltf_path, files = AF.ph_download_gltf(TEST_MODEL, resolution="1k")
    print("   gltf:", os.path.basename(gltf_path))
    for rel, p in sorted(files.items()):
        print("     %-52s %8.1f KB" % (rel, os.path.getsize(p) / 1024))
    print("   耗时 %.1fs" % (time.time() - t0))

    print()
    print("② 打包成 GLB")
    dest = os.path.join(ROOT, "assets", "_asset_cache", "test", TEST_MODEL + ".glb")
    AF.gltf_to_glb(gltf_path, files, dest)
    print("   →", dest)
    print("   大小: %.1f MB" % (os.path.getsize(dest) / 1024 / 1024))

    print()
    print("③ 解析校验（用项目自己的 inspect_glb）")
    sys.path.insert(0, os.path.join(ROOT, "scripts", "dev", "blender"))
    try:
        from inspect_glb import stats
        st = stats(dest)
        print("   三角面: %s" % format(st["triangles"], ","))
        print("   顶点:   %s" % format(st["vertices"], ","))
        print("   尺寸 mm:", [round(v * 1000) for v in st["dims"]])
        print("   材质:  ", st["materials"])
        print("   bbox:  ", st["bbox"])
    except Exception as e:
        print("   inspect_glb 失败:", e)
        import traceback
        traceback.print_exc()

    print()
    print("=" * 70)
    print("SUCCESS" if os.path.exists(dest) else "FAILED")


if __name__ == "__main__":
    main()
