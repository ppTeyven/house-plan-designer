"""核对 Blender 4.5 光源属性与单位语义（不靠记忆）。"""
import bpy
bpy.ops.object.light_add(type='AREA')
o = bpy.context.active_object
l = o.data
print("Light props:", ", ".join(sorted(p.identifier for p in l.bl_rna.properties if not p.is_readonly)))
print("energy =", l.energy)
print("default W for AREA:", bpy.data.lights.new("t", 'AREA').energy)
print("Scene view_settings view_transforms:", [v.identifier for v in bpy.context.scene.view_settings.bl_rna.properties['view_transform'].enum_items])
print("render engines:", [v.identifier for v in bpy.context.scene.render.bl_rna.properties['engine'].enum_items])
print("eevee props:", ", ".join(sorted(p.identifier for p in bpy.context.scene.eevee.bl_rna.properties if not p.is_readonly)[:40]))