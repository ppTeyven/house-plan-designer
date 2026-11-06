"""【A/B 对比渲染】同一件家具：旧版 vs 新版（同灯光、同角度、同材质）。

【目的】
  证明"重建"是真的把几何加密了，而不是换了贴图或者换了个角度。
  用 Blender 无头渲染两版，输出并排对比图。

用法:
  python 验收/ab_render.py bookshelf counter rug
"""
import json
import os
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "assets", "_asset_cache")
BACKUP = os.path.join(CACHE, "glb_backup_detail2_20261106_160146")
NEW = os.path.join(CACHE, "_geo_highpoly", "out2")
OUT = os.path.join(ROOT, "验收", "_ab")

BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
if not os.path.exists(BLENDER):
    for c in os.listdir(r"C:\Program Files\Blender Foundation"):
        BLENDER = os.path.join(r"C:\Program Files\Blender Foundation", c, "blender.exe")
        if os.path.exists(BLENDER):
            break

SCRIPT = r"""
import bpy, sys, os, math
argv = sys.argv[sys.argv.index("--")+1:]
src, out, angle = argv[0], argv[1], float(argv[2])

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

bpy.ops.import_scene.gltf(filepath=src)

# 归一化：整体缩放到 1m 边长，落在原点
objs = [o for o in scn.objects if o.type == 'MESH']
mn = [1e9]*3; mx=[-1e9]*3
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ __import__('mathutils').Vector(c)
        for i in range(3):
            mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
size = [mx[i]-mn[i] for i in range(3)]
m = max(size) or 1
for o in objs:
    o.scale = [s/m for s in o.scale]
    o.location.x -= (mn[0]+mx[0])/2*m/m
    o.location.z -= (mn[2]+mx[2])/2*m/m

# 统一哑光材质（隔离几何差异，不让贴图干扰）
for o in objs:
    mat = bpy.data.materials.new("flat")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.62,0.60,0.56,1)
    bsdf.inputs['Roughness'].default_value = 0.75
    o.data.materials.clear()
    o.data.materials.append(mat)

# 三点光
for loc, en, sz in [((3,-4,5),900,4),((-4,-2,3),350,3),((0,5,4),500,3)]:
    ld = bpy.data.lights.new('L','AREA'); ld.energy=en; ld.size=sz
    o = bpy.data.objects.new('L',ld); o.location=loc
    o.rotation_euler = (math.radians(60),0,math.radians(30))
    scn.collection.objects.link(o)

cam_d = bpy.data.cameras.new('C'); cam = bpy.data.objects.new('C',cam_d)
a = math.radians(angle)
cam.location = (math.cos(a)*2.6, -math.sin(a)*2.6, 1.5)
cam.rotation_euler = (math.radians(65), 0, math.radians(angle+90))
scn.collection.objects.link(cam); scn.camera = cam

w = bpy.data.worlds.new('W'); w.use_nodes=True
scn.world = w
scn.render.engine = 'BLENDER_EEVEE_NEXT'
scn.render.resolution_x = 480; scn.render.resolution_y = 480
scn.render.film_transparent = False
scn.render.filepath = out
scn.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
"""


def main():
    keys = sys.argv[1:] or ["bookshelf", "counter", "rug", "toilet", "officeChair"]
    os.makedirs(OUT, exist_ok=True)
    sp = os.path.join(OUT, "_r.py")
    open(sp, "w", encoding="utf-8").write(SCRIPT)
    for k in keys:
        old = os.path.join(BACKUP, k + ".glb.furn")
        new = os.path.join(NEW, k + ".glb")
        if not os.path.exists(old) or not os.path.exists(new):
            print("skip %s (缺文件)" % k)
            continue
        for tag, src in (("old", old), ("new", new)):
            out = os.path.join(OUT, "%s_%s.png" % (k, tag))
            r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", sp,
                                "--", src, out, "35"],
                               capture_output=True, text=True)
            if not os.path.exists(out):
                print("FAIL %s %s: %s" % (k, tag, r.stderr[-300:]))
        print("rendered", k)


if __name__ == "__main__":
    main()
