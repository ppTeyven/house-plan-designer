"""校准探针：已知 Blender 世界坐标的盒子 → 检查解析出的 (宽X, 深Z, 高Y) 是否正确。
Blender: X=宽, Y=深, Z=高。盒子放在 x 0~1.0, y 0~2.0, z 0~0.5
期望解析: dims=[1.0, 2.0, 0.5]（宽, 深, 高），zmin=0.0
"""
import bpy, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_glb import stats, read_glb

OUT = r"D:\house planner\house-plan-designer-main\验收\models\_probe4.glb"
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
o = bpy.context.active_object
o.name = "probe"
o.dimensions = (1.0, 2.0, 0.5)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
for v in o.data.vertices:
    v.co.x += 0.5; v.co.y += 1.0; v.co.z += 0.25
o.location = (0, 0, 0)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_cameras=False, export_lights=False)

js = read_glb(OUT)
print("[gltf] node:", json.dumps(js["nodes"][0]))
for m in js["meshes"]:
    for p in m["primitives"]:
        acc = js["accessors"][p["attributes"]["POSITION"]]
        print("[gltf] accessor min=", acc.get("min"), "max=", acc.get("max"))

s = stats(OUT)
print("解析 dims(宽,深,高) =", [round(v, 4) for v in s["dims"]], " zmin=", round(s["zmin"], 4))
print("期望 dims = [1.0, 2.0, 0.5]  zmin = 0.0")
print("gltf_dims =", [round(v, 4) for v in s["gltf_dims"]])