"""把 assets/furnlib/*.glb 同步到主程序的高清家具库 furnlib/。

【为什么必须做这一步】
git 里 `furnlib/` 从来没有提交过（`git ls-files | grep furnlib` = 0 个文件），
而主程序 assets/template.html 里写着：
    const r = await fetch("furnlib/index.json"); if (!r.ok) return;
    __FURN.set(t, {g, w, h, d})          // 按 type 键取模型
    __g.scale.set(i/__m.w, o/__m.h, s/__m.d)
也就是说：
  · 主程序本来【设计成】用 GLB 高模替换程序化基础几何体
  · 但 furnlib 从未入库 → fetch 404 → __FURN 为空
  → 所有家具都在跑 `switch(n.type)` 的程序化分支（几个 Box/Cylinder 拼的）
  → 这就是用户说的"整体依旧是简陋几何体拼凑的"的【真正根源】

【坐标轴处理】Blender 导出是 Z-up，Three.js 是 Y-up。
主程序直接 `new z0().setFromObject(g).getSize()` 取尺寸，
若不转换，w/h/d 会错位（Z 变成 height），家具会躺倒或拉伸。
所以这里在 Blender 里把 GLB 导出为 Y-up（glTF 规范的 +Y up），
再验证尺寸与验收站一致。

用法：
  blender --background --python sync_furnlib.py
"""
import bpy, os, sys, json, math, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SRC = os.path.join(ROOT, "assets", "furnlib")
# 【关键路径】主程序 assets/template.html 里写的是 fetch("furnlib/index.json")，
# 相对路径是相对于【页面所在目录 assets/】解析的，不是项目根。
# 所以 furnlib 必须放在 assets/ 下，否则 fetch('furnlib/sofa.glb') 会 404，
# 主程序就静默退回程序化基础几何体（这正是"简陋几何体"的根源）。
DST = os.path.join(ROOT, "assets", "furnlib")
os.makedirs(DST, exist_ok=True)

# 主程序 __FURN 的键 = 家具的 type（见 assets/template.html 的 palette key）
# 验收站的 key 已与目录条目一一绑定，这里直接沿用。
MAP = {
    "sofa": "sofa",
    "bed": "bed",
    "chair": "chair",
    "diningTable": "diningTable",
    "coffeeTable": "coffeeTable",
    "tvCabinet": "tvCabinet",
    "wardrobe": "wardrobe",
    "nightstand": "nightstand",
}


def export_yup(src, dst):
    """导入 GLB → 落地 + 居中 → 重新导出到 furnlib

    【坐标系陷阱（实测踩坑）】
    Blender 的 glTF 导出器在 export_yup=True 时【已经自动做了 Z-up → Y-up 转换】。
    如果再手动转一次，就会转两次 —— 结果是 Y 轴变成原来的 Z（深度），
    家具在 Three.js 里就"躺倒"了。
    实测：手动转换后 sofa 读到 w=2.265 h=0.874 d=0.875（h/d 互换），
          正确的应该是 w=2.265 h=0.875 d=0.874。

    所以这里【不再手动交换 Y/Z】，只做：
      1. 落地（min z = 0）
      2. 水平居中（x、y 居中）
    然后直接导出，让导出器做那一次正确的 Y-up 转换。
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)

    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not objs:
        print("EMPTY", src)
        return None

    import mathutils
    # 落地 + 水平居中（在 Blender 的 Z-up 空间里做，z 是高度）
    mn = [1e9] * 3
    mx = [-1e9] * 3
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    size = [mx[i] - mn[i] for i in range(3)]
    cx = (mn[0] + mx[0]) / 2
    cy = (mn[1] + mx[1]) / 2

    for o in objs:
        for v in o.data.vertices:
            v.co.x -= cx
            v.co.y -= cy
            v.co.z -= mn[2]
        o.location = (0, 0, 0)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB',
                              export_materials='EXPORT', export_extras=True,
                              export_cameras=False, export_lights=False,
                              export_yup=True, export_apply=True)
    # 导出后尺寸（Y-up: w=x, h=y, d=z）
    return {"w": round(size[0], 4), "h": round(size[2], 4), "d": round(size[1], 4),
            "raw": [round(v, 4) for v in size]}


index = {}
report = []
for key, typ in MAP.items():
    src = os.path.join(SRC, key + ".glb")
    if not os.path.exists(src):
        print("MISS", key)
        continue
    dst = os.path.join(DST, key + ".glb")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    info = export_yup(src, dst)
    index[typ] = {"file": key + ".glb"}
    report.append((typ, info, os.path.getsize(dst) / 1024 / 1024))
    print("OK %-14s -> %-14s  w=%.3f h=%.3f d=%.3f  %.2fMB" %
          (key, typ, info["w"], info["h"], info["d"], report[-1][2]))

with open(os.path.join(DST, "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=1)

print("\nfurnlib/index.json ->", list(index.keys()))
