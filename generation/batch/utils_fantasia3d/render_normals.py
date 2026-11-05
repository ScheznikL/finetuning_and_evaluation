#
# import os
import argparse
import sys
import os
import shutil
# ----------------------------------------------------------------------------
# MODE DETECTION
# ----------------------------------------------------------------------------
try:
    import bpy
    import math
    IS_INSIDE_BLENDER = True
except ImportError:
    IS_INSIDE_BLENDER = False
    import open3d as o3d
    import numpy as np

def render_normal_open3d(path_to_obj, out_dir="./temp"):
    os.makedirs(out_dir, exist_ok=True)

    # 1. Load the mesh
    mesh = o3d.io.read_triangle_mesh(path_to_obj)
    
    # 2. Compute Normals
    mesh.compute_vertex_normals()

    # 3. Paint Normals to Vertex Colors
    # Normals range [-1, 1] -> Colors [0, 1]
    normals = np.asarray(mesh.vertex_normals)
    colors = (normals + 1.0) / 2.0
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

    # 4. Setup OffscreenRenderer (Headless friendly)
    width, height = 512, 512
    render = o3d.visualization.rendering.OffscreenRenderer(width, height)
    
    # Material Settings: "defaultUnlit" mimics light_on = False (Shadeless)
    material = o3d.visualization.rendering.MaterialRecord()
    material.shader = "defaultUnlit"
    
    # Add geometry to the scene
    render.scene.add_geometry("mesh_normal", mesh, material)
    
    # 5. Camera Setup
    # Calculate center and extent to position camera automatically
    center = mesh.get_center()
    bbox = mesh.get_axis_aligned_bounding_box()
    max_extent = np.max(bbox.get_extent())
    
    # Distance heuristic: fits the object within the FOV (default 60 degrees)
    # 1.5 multiplier serves as a safe "zoom" factor similar to the original 0.8
    distance = max_extent * 1.5 
    up_vector = np.array([0, 1, 0])

    # --- FRONT VIEW ---
    # Original: front=[0, 0, -1] (Looking towards -Z, so Eye is at +Z)
    eye_front = center + np.array([0, 0, distance])
    render.scene.camera.look_at(center, eye_front, up_vector)
    
    img_front = render.render_to_image()
    o3d.io.write_image(os.path.join(out_dir, "o3d_normal_front.png"), img_front)

    # --- SIDE VIEW ---
    # Original: front=[-1, 0, 0] (Looking towards -X, so Eye is at +X)
    eye_side = center + np.array([distance, 0, 0])
    render.scene.camera.look_at(center, eye_side, up_vector)
    
    img_side = render.render_to_image()
    o3d.io.write_image(os.path.join(out_dir, "o3d_normal_side.png"), img_side)

    # Cleanup not strictly necessary for OffscreenRenderer, but good practice
    # render objects are destroyed when they go out of scope
    
    return [os.path.join(out_dir, "o3d_normal_front.png"), 
            os.path.join(out_dir, "o3d_normal_side.png")]

import sys
import os
import shutil

# ----------------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------------
# Blender Executable Path
BLENDER_EXE = '/local/java/blender-4.2.1-linux-x64/blender'

# Hardcoded Input/Output Paths
PRIOR_PATH = "/dcs/large/u5745134/dataset/raw/cover_prior/coverC_to_obj_pipe.obj"
TEMP_RESULTS = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/tmp_results"

# ----------------------------------------------------------------------------
# MODE DETECTION
# ----------------------------------------------------------------------------
try:
    import bpy
    import math
    IS_INSIDE_BLENDER = True
except ImportError:
    IS_INSIDE_BLENDER = False

# ----------------------------------------------------------------------------
# 1. WRAPPER MODE (Runs in your Conda/Shell environment)
# ----------------------------------------------------------------------------
if not IS_INSIDE_BLENDER:
    import subprocess
    
    def render_normals_blender(prior_path=None, norm_out_dir=None):
        print(f"--- Initialization [Wrapper] ---")
        
        # 1. Validate Blender Path
        blender_bin = BLENDER_EXE
        if not os.path.exists(blender_bin):
            print(f"Warning: Specific Blender path not found: {blender_bin}")
            print("Attempting to use system 'blender' from 'module load'...")
            if shutil.which("blender"):
                blender_bin = "blender"
            else:
                print("Error: Could not find Blender executable.")
                sys.exit(1)

        if not prior_path and not norm_out_dir:
            prior_path = PRIOR_PATH
            norm_out_dir = TEMP_RESULTS
            
        print(f"Using Blender: {blender_bin}")
        print(f"Input: {prior_path}")
        print(f"Output: {norm_out_dir}")

        # 2. Construct Command
        # We don't pass args for paths anymore, the script inside Blender uses the same hardcoded constants
        this_script = os.path.abspath(__file__)
        cmd = [ 
            blender_bin,
            '--background',
            '--python', this_script, 
            '--',
            '--object', prior_path,
            '--output_folder', norm_out_dir
            ]
        
        print(f"Launching subprocess...")
        subprocess.check_call(cmd)
        print("--- Rendering Complete ---")

    if __name__ == "__main__":
        render_normals_blender()

# ----------------------------------------------------------------------------
# 2. BLENDER MODE (Runs inside Blender)
# ----------------------------------------------------------------------------
else:
    def main_blender():
        print(f"--- Initialization [Blender Internal] ---")
        parser = argparse.ArgumentParser()
        parser.add_argument('--object', type=str, default=PRIOR_PATH)
        parser.add_argument('--output_folder', type=str, default=TEMP_RESULTS)
        args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
        
        # if not args.object and not args.output_folder:
        #     prior_path = PRIOR_PATH
        #     norm_out_dir = TEMP_RESULTS
        # else:
        #     prior_path = args.object
        #     norm_out_dir = args.output_folder
        
        render_normal_logic(args.object, args.output_folder)

    def render_normal_logic(path_to_obj, out_dir):
        if not os.path.exists(path_to_obj):
            print(f"Error: Input file not found at {path_to_obj}")
            return

        os.makedirs(out_dir, exist_ok=True)
        
        # --- Clean Scene ---
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # --- Import OBJ/GLB ---
        # Detect extension to use correct importer
        ext = os.path.splitext(path_to_obj)[1].lower()
        if ext == '.glb' or ext == '.gltf':
            bpy.ops.import_scene.gltf(filepath=path_to_obj)
        elif ext == '.obj':
            # Blender 4.2+ uses wm.obj_import, older uses import_scene.obj
            if hasattr(bpy.ops.wm, 'obj_import'):
                bpy.ops.wm.obj_import(filepath=path_to_obj)
            else:
                bpy.ops.import_scene.obj(filepath=path_to_obj)
        
        # --- Select and Normalize ---
        # Select all meshes
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj.select_set(True)
        
        if not bpy.context.selected_objects:
            print("No mesh imported.")
            return

        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.join() # Join into one object
        obj = bpy.context.active_object

        # Center and Scale
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        obj.location = (0, 0, 0)
        max_dim = max(obj.dimensions)
        if max_dim > 0:
            s = 1.0 / max_dim
            obj.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # --- Normal Shader (World Normals) ---
        mat = bpy.data.materials.new(name="NormalMat")
        mat.use_nodes = True
        tree = mat.node_tree
        tree.nodes.clear()
        
        # Geometry -> Vector Math(Multiply Add) -> Emission -> Output
        geo = tree.nodes.new('ShaderNodeNewGeometry')
        
        # Map (-1,1) to (0,1) -> (Normal * 0.5) + 0.5
        math_node = tree.nodes.new('ShaderNodeVectorMath')
        math_node.operation = 'MULTIPLY_ADD'
        math_node.inputs[1].default_value = (0.5, 0.5, 0.5)
        math_node.inputs[2].default_value = (0.5, 0.5, 0.5)
        
        emit = tree.nodes.new('ShaderNodeEmission')
        out = tree.nodes.new('ShaderNodeOutputMaterial')
        
        tree.links.new(geo.outputs['True Normal'], math_node.inputs[0])
        tree.links.new(math_node.outputs['Vector'], emit.inputs['Color'])
        tree.links.new(emit.outputs['Emission'], out.inputs['Surface'])
        
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

# --- Camera Setup ---
        cam_data = bpy.data.cameras.new("Camera")
        cam = bpy.data.objects.new("Camera", cam_data)
        bpy.context.collection.objects.link(cam)
        bpy.context.scene.camera = cam

        # Add a "Track To" constraint so the camera always looks at the object (0,0,0)
        # This makes moving the camera much easier
        constraint = cam.constraints.new(type='TRACK_TO')
        constraint.target = obj
        constraint.track_axis = 'TRACK_NEGATIVE_Z' # Camera looks down -Z
        constraint.up_axis = 'UP_Y'             # Camera Up is Y
        
#         # --- Camera Setup ---
        # cam_data = bpy.data.cameras.new("Camera")
        # cam = bpy.data.objects.new("Camera", cam_data)
        # bpy.context.collection.objects.link(cam)
        # bpy.context.scene.camera = cam
        # cam.location = (0, -2, 0)
        # cam.rotation_euler = (math.radians(90), 0, 0)

        # --- Render Settings ---
        scene = bpy.context.scene
        # Auto-detect Eevee version (Blender 4.2 changed the ID to BLENDER_EEVEE_NEXT)
        scene.render.engine = 'BLENDER_EEVEE_NEXT' if bpy.app.version >= (4, 2, 0) else 'BLENDER_EEVEE'
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.view_settings.view_transform = 'Standard'

        # --------------------
        # VIEW 1: FRONT
        # --------------------
        # Position: Front (-Y axis)
        cam.location = (0, -2, 0)
        bpy.context.view_layer.update() # Update constraints
        
        scene.render.filepath = os.path.join(out_dir, "front_normal.png")
        print(f"Rendering: {scene.render.filepath}")
        bpy.ops.render.render(write_still=True)

        # --------------------
        # VIEW 2: SIDE (Profile)
        # --------------------
        # Position: Side (+X axis)
        # Instead of rotating the object, we just move the camera now that we have a constraint.
        cam.location = (2, 0, 0)
        bpy.context.view_layer.update()

        scene.render.filepath = os.path.join(out_dir, "side_normal.png")
        print(f"Rendering: {scene.render.filepath}")
        bpy.ops.render.render(write_still=True)

        # --------------------
        # VIEW 3: UPPER CORNER (Isometric-ish)
        # --------------------
        # "Middle of Front and Side" = 45 degrees azimuth
        # "Upper Vertex" = Add Z height
        # Position: (1.5, -1.5, 1.5) looks from the corner down at the center
        cam.location = (1, -1, 1.1)
        bpy.context.view_layer.update()

        scene.render.filepath = os.path.join(out_dir, "corner_normal.png")
        print(f"Rendering: {scene.render.filepath}")
        bpy.ops.render.render(write_still=True)
        
        # # Render Front
        # scene.render.filepath = os.path.join(out_dir, "front_normal.png")
        # print(f"Rendering: {scene.render.filepath}")
        # bpy.ops.render.render(write_still=True)

        # # Render Side
        # obj.rotation_euler[2] += math.radians(90)
        # scene.render.filepath = os.path.join(out_dir, "side_normal.png")
        # print(f"Rendering: {scene.render.filepath}")
        # bpy.ops.render.render(write_still=True)
        
        # # Render from vertex
        # # obj.rotation_euler[2] += math.radians(90)
        # # scene.render.filepath = os.path.join(out_dir, "vertex_normal.png")
        # # print(f"Rendering: {scene.render.filepath}")
        # # bpy.ops.render.render(write_still=True)

    if __name__ == "__main__":
        main_blender()
