import bpy, os
ROOT = r"D:\house planner\house-plan-designer-main\furnlib"
name = os.environ.get("ONLY", "sofa")
f = os.path.join(ROOT, name + ".glb")
out = os.path.join(ROOT, "preview_" + name + ".png")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=f)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
gp = bpy.context.active_object
m = bpy.data.materials.new("gmat")
m.use_nodes = True
bsdf = m.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.82, 0.82, 0.82, 1.0)
bsdf.inputs["Roughness"].default_value = 0.95
gp.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -2, 5))
bpy.context.active_object.data.energy = 3.0
bpy.ops.object.light_add(type='AREA', location=(-2.5, 2.5, 3))
a = bpy.context.active_object
a.data.energy = 150
a.data.size = 2.0
bpy.ops.object.camera_add(location=(2.7, -2.7, 1.9))
cam = bpy.context.active_object
bpy.context.scene.camera = cam
bpy.ops.object.empty_add(location=(0, 0, 0.45))
emp = bpy.context.active_object
con = cam.constraints.new('TRACK_TO')
con.target = emp
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.render.resolution_x = 900
bpy.context.scene.render.resolution_y = 700
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDERED " + out)
