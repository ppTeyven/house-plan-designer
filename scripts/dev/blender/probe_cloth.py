import bpy
bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4)
o = bpy.context.active_object
col = o.modifiers.new("Collision", 'COLLISION')
print("=== CollisionSettings props ===")
print(", ".join(sorted(p.identifier for p in col.settings.bl_rna.properties if not p.is_readonly)))
print("=== ClothCollisionSettings props ===")
cl = o.modifiers.new("Cloth", 'CLOTH')
print(", ".join(sorted(p.identifier for p in cl.collision_settings.bl_rna.properties if not p.is_readonly)))
print("=== Collision modifier props ===")
print(", ".join(sorted(p.identifier for p in col.bl_rna.properties if not p.is_readonly)))
