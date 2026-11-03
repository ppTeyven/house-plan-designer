"""检查 GLB 内材质是否真的带了颜色/参数（读 glTF JSON，不靠猜）。"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_glb import read_glb

js = read_glb(sys.argv[1])
print("materials:", len(js.get("materials", [])))
for m in js.get("materials", []):
    pbr = m.get("pbrMetallicRoughness", {})
    bc = pbr.get("baseColorFactor")
    bcS = ("[" + ",".join(f"{v:.3f}" for v in bc) + "]") if bc else "None"
    print(f"  {m.get('name','?'):<18} baseColor={bcS} rough={pbr.get('roughnessFactor')} "
          f"metal={pbr.get('metallicFactor')} tex={[t.get('index') for t in pbr.get('baseColorTexture',[])]}")
print("textures:", len(js.get("textures", [])), "images:", len(js.get("images", [])))