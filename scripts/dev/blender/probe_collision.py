"""探查：怎样给一个 mesh 副本对象加 Collision 修改器。"""
import bpy, sys

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
src = bpy.context.active_object
src.name = "src"
src.dimensions = (1, 1, 0.2)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# 方式1：bpy.data.objects.new + data.copy()
c1 = bpy.data.objects.new("c1", src.data.copy())
print("方式1 未链接时 modifiers.new ->", c1.modifiers.new("Collision", 'COLLISION'))
bpy.context.collection.objects.link(c1)
m = c1.modifiers.new("Collision", 'COLLISION')
print("方式1 链接后 ->", m, "settings:", m.settings if m else None)

# 方式2：object.copy()（复制整个对象）
c2 = src.copy()
print("方式2 copy() ->", c2)
bpy.context.collection.objects.link(c2)
m2 = c2.modifiers.new("Collision", 'COLLISION')
print("方式2 链接后 modifiers.new ->", m2)
if m2:
    print("   settings ok:", m2.settings is not None)

# 方式3：mesh copy 到新 mesh 再 new
me = src.data.copy()
c3 = bpy.data.objects.new("c3", me)
bpy.context.collection.objects.link(c3)
m3 = c3.modifiers.new("Collision", 'COLLISION')
print("方式3 ->", m3)

# 真实原因探测：Collision 修改器是否需要特定上下文
print("--- Collision modifier type 枚举是否存在 ---")
print([i.identifier for i in bpy.types.Modifier.bl_rna.properties['type'].enum_items
       if 'COLL' in i.identifier])