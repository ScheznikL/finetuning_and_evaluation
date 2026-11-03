from typing import *

from mathutils import Vector, Matrix
import numpy as np
import json
import glob
import random
import shutil
import mathutils

import bpy
import argparse, sys, os, math, re
import shutil, json
import numpy as np

# --- Import the Hunyuan initialization helpers ---
# from hunyuan3d_init import (
#     init_scene, load_object, normalize_scene,
#     init_camera, init_lighting, get_transform_matrix
# )


IMPORT_FUNCTIONS: Dict[str, Callable] = {
    "obj": bpy.ops.wm.obj_import, #bpy.ops.import_scene.obj
    "glb": bpy.ops.import_scene.gltf,
    "gltf": bpy.ops.import_scene.gltf,
    "usd": bpy.ops.import_scene.usd,
    "fbx": bpy.ops.import_scene.fbx,
    "stl": bpy.ops.import_mesh.stl,
    "usda": bpy.ops.import_scene.usda,
    "dae": bpy.ops.wm.collada_import,
    "ply": bpy.ops.import_mesh.ply,
    "abc": bpy.ops.wm.alembic_import,
    "blend": bpy.ops.wm.append,
}

EXT = {
    'PNG': 'png',
    'JPEG': 'jpg',
    'OPEN_EXR': 'exr',
    'TIFF': 'tiff',
    'BMP': 'bmp',
    'HDR': 'hdr',
    'TARGA': 'tga'
}

def scene_bbox() -> Tuple[Vector, Vector]:
    """Returns the bounding box of the scene.

    Taken from Shap-E rendering script
    (https://github.com/openai/shap-e/blob/main/shap_e/rendering/blender/blender_script.py#L68-L82)

    Returns:
        Tuple[Vector, Vector]: The minimum and maximum coordinates of the bounding box.
    """
    bbox_min = (math.inf,) * 3
    bbox_max = (-math.inf,) * 3
    found = False
    scene_meshes = [obj for obj in bpy.context.scene.objects.values() if isinstance(obj.data, bpy.types.Mesh)]
    for obj in scene_meshes:
        found = True
        for coord in obj.bound_box:
            coord = Vector(coord)
            coord = obj.matrix_world @ coord
            bbox_min = tuple(min(x, y) for x, y in zip(bbox_min, coord))
            bbox_max = tuple(max(x, y) for x, y in zip(bbox_max, coord))
    if not found:
        raise RuntimeError("no objects in scene to compute bounding box for")
    return Vector(bbox_min), Vector(bbox_max)


def normalize_scene() -> Tuple[float, Vector]:
    """Normalizes the scene by scaling and translating it to fit in a unit cube centered
    at the origin.

    Mostly taken from the Point-E / Shap-E rendering script
    (https://github.com/openai/point-e/blob/main/point_e/evals/scripts/blender_script.py#L97-L112),
    but fix for multiple root objects: (see bug report here:
    https://github.com/openai/shap-e/pull/60).

    Returns:
        Tuple[float, Vector]: The scale factor and the offset applied to the scene.
    """
    scene_root_objects = [obj for obj in bpy.context.scene.objects.values() if not obj.parent]
    if len(scene_root_objects) > 1:
        # create an empty object to be used as a parent for all root objects
        scene = bpy.data.objects.new("ParentEmpty", None)
        bpy.context.scene.collection.objects.link(scene)

        # parent all root objects to the empty object
        for obj in scene_root_objects:
            obj.parent = scene
    else:
        scene = scene_root_objects[0]

    bbox_min, bbox_max = scene_bbox()
    scale = 1 / max(bbox_max - bbox_min)
    scene.scale = scene.scale * scale

    # Apply scale to matrix_world.
    bpy.context.view_layer.update()
    bbox_min, bbox_max = scene_bbox()
    offset = -(bbox_min + bbox_max) / 2
    scene.matrix_world.translation += offset
    bpy.ops.object.select_all(action="DESELECT")
    
    return scale, offset

def get_transform_matrix(obj: bpy.types.Object) -> list:
    pos, rt, _ = obj.matrix_world.decompose()
    rt = rt.to_matrix()
    matrix = []
    for ii in range(3):
        a = []
        for jj in range(3):
            a.append(rt[ii][jj])
        a.append(pos[ii])
        matrix.append(a)
    matrix.append([0, 0, 0, 1])
    return matrix


def init_scene() -> None:
    """Resets the scene to a clean state.

    Returns:
        None
    """
    # delete everything
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    # delete all the materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)

    # delete all the textures
    for texture in bpy.data.textures:
        bpy.data.textures.remove(texture, do_unlink=True)

    # delete all the images
    for image in bpy.data.images:
        bpy.data.images.remove(image, do_unlink=True)

def init_camera():
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.sensor_height = cam.data.sensor_width = 32
    cam_constraint = cam.constraints.new(type='TRACK_TO')
    cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    cam_constraint.up_axis = 'UP_Y'
    cam_empty = bpy.data.objects.new("Empty", None)
    cam_empty.location = (0, 0, 0)
    bpy.context.scene.collection.objects.link(cam_empty)
    cam_constraint.target = cam_empty
    return cam

def init_lighting():
    # Clear existing lights
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="LIGHT")
    bpy.ops.object.delete()
    
    # Create key light
    default_light = bpy.data.objects.new("Default_Light", bpy.data.lights.new("Default_Light", type="POINT"))
    bpy.context.collection.objects.link(default_light)
    default_light.data.energy = 1000
    default_light.location = (4, 1, 6)
    default_light.rotation_euler = (0, 0, 0)
    
    # create top light
    top_light = bpy.data.objects.new("Top_Light", bpy.data.lights.new("Top_Light", type="AREA"))
    bpy.context.collection.objects.link(top_light)
    top_light.data.energy = 10000
    top_light.location = (0, 0, 10)
    top_light.scale = (100, 100, 100)
    
    # create bottom light
    bottom_light = bpy.data.objects.new("Bottom_Light", bpy.data.lights.new("Bottom_Light", type="AREA"))
    bpy.context.collection.objects.link(bottom_light)
    bottom_light.data.energy = 1000
    bottom_light.location = (0, 0, -10)
    bottom_light.rotation_euler = (0, 0, 0)
    
    return {
        "default_light": default_light,
        "top_light": top_light,
        "bottom_light": bottom_light
    }


def load_object(object_path: str) -> None:
    """Loads a model with a supported file extension into the scene.

    Args:
        object_path (str): Path to the model file.

    Raises:
        ValueError: If the file extension is not supported.

    Returns:
        None
    """
    file_extension = object_path.split(".")[-1].lower()
    if file_extension is None:
        raise ValueError(f"Unsupported file type: {object_path}")

    if file_extension == "usdz":
        # install usdz io package
        dirname = os.path.dirname(os.path.realpath(__file__))
        usdz_package = os.path.join(dirname, "io_scene_usdz.zip")
        bpy.ops.preferences.addon_install(filepath=usdz_package)
        # enable it
        addon_name = "io_scene_usdz"
        bpy.ops.preferences.addon_enable(module=addon_name)
        # import the usdz
        from io_scene_usdz.import_usdz import import_usdz

        import_usdz(context, filepath=object_path, materials=True, animations=True)
        return None

    # load from existing import functions
    import_function = IMPORT_FUNCTIONS[file_extension]

    print(f"Loading object from {object_path}")
    if file_extension == "blend":
        import_function(directory=object_path, link=False)
    elif file_extension in {"glb", "gltf"}:
        import_function(filepath=object_path, merge_vertices=True, import_shading='NORMALS')
    else:
        import_function(filepath=object_path)
        

# --- User args ---
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--object', type=str, required=True)
parser.add_argument('--output_folder', type=str, default='/tmp')
parser.add_argument('--resolution', type=int, default=512)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

os.makedirs(args.output_folder, exist_ok=True)

# --- 1. Initialize scene and load object ---
init_scene()
load_object(args.object)
scale, offset = normalize_scene()
print(f'[INFO] Scene normalized (scale={scale}, offset={offset})')

# --- 2. Initialize camera and lighting ---
cam = init_camera()
init_lighting()
print('[INFO] Camera and lighting initialized.')

# --- 3. Define two profile views (front + side) ---
views = [
    {'name': 'front', 'location': (0, -2, 0), 'look_at': (0, 0, 0)},  # front
    {'name': 'side',  'location': (2, 0, 0), 'look_at': (0, 0, 0)}   # side
]

def look_at(obj_camera, target):
    """
    Make camera look at the target point.
    """
    direction = np.array(target) - np.array(obj_camera.location)
    rot_z = np.arctan2(direction[1], direction[0])
    rot_y = -np.arctan2(direction[2], np.sqrt(direction[0]**2 + direction[1]**2))
    obj_camera.rotation_euler = (rot_y, 0, rot_z)

# --- 4. Render the two views ---
for view in views:
    cam.location = view['location']
    look_at(cam, view['look_at'])
    bpy.context.scene.render.resolution_x = args.resolution
    bpy.context.scene.render.resolution_y = args.resolution
    bpy.context.scene.render.filepath = os.path.join(args.output_folder, f"{view['name']}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[INFO] Rendered {view['name']} view to {bpy.context.scene.render.filepath}")

# --- 5. Save camera info ---
camera_data = {
    view['name']: get_transform_matrix(cam) for view in views
}
with open(os.path.join(args.output_folder, 'camera_transforms.json'), 'w') as f:
    json.dump(camera_data, f, indent=4)


# import bpy
# import sys
# import os
# import math




# def load_object(object_path: str) -> None:
#     """Loads a model with a supported file extension into the scene.

#     Args:
#         object_path (str): Path to the model file.

#     Raises:
#         ValueError: If the file extension is not supported.

#     Returns:
#         None
#     """
#     file_extension = object_path.split(".")[-1].lower()
#     if file_extension is None:
#         raise ValueError(f"Unsupported file type: {object_path}")

#     if file_extension == "usdz":
#         # install usdz io package
#         dirname = os.path.dirname(os.path.realpath(__file__))
#         usdz_package = os.path.join(dirname, "io_scene_usdz.zip")
#         bpy.ops.preferences.addon_install(filepath=usdz_package)
#         # enable it
#         addon_name = "io_scene_usdz"
#         bpy.ops.preferences.addon_enable(module=addon_name)
#         # import the usdz
#         from io_scene_usdz.import_usdz import import_usdz

#         import_usdz(context, filepath=object_path, materials=True, animations=True)
#         return None

#     # load from existing import functions
#     import_function = IMPORT_FUNCTIONS[file_extension]

#     print(f"Loading object from {object_path}")
#     if file_extension == "blend":
#         import_function(directory=object_path, link=False)
#     elif file_extension in {"glb", "gltf"}:
#         import_function(filepath=object_path, merge_vertices=True, import_shading='NORMALS')
#     else:
#         import_function(filepath=object_path)

# # --------------------
# # Args
# # --------------------
# argv = sys.argv[sys.argv.index("--") + 1:]
# glb_path = argv[0]
# out_dir = argv[1]

# if not glb_path or not out_dir:
#     print(f'[ERROR] not {glb_path} and {out_dir}')
# else:
#     print(f'[INFO] {glb_path} and {out_dir}')

# os.makedirs(out_dir, exist_ok=True)

# # --------------------
# # Clean scene
# # --------------------
# bpy.ops.object.select_all(action='SELECT')
# bpy.ops.object.delete(use_global=False)

# # --------------------
# # Import GLB
# # --------------------
# #bpy.ops.import_scene.gltf(filepath=glb_path)
# init_scene()
# load_object(glb_path)
# obj = bpy.context.selected_objects[0]
# bpy.context.view_layer.objects.active = obj
# print('[INFO] Scene initialized.')
# # --------------------
# # Normalize scale & center (SAFE)
# # --------------------
# bpy.context.view_layer.objects.active = obj
# bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
# obj.location = (0, 0, 0)

# dims = obj.dimensions
# max_dim = max(dims)

# if max_dim <= 1e-6:
#     print(f"[WARN] Object {obj.name} has zero dimensions, skipping render")
#     bpy.data.objects.remove(obj, do_unlink=True)
#     raise RuntimeError("Invalid mesh: zero size")

# scale = 1.0 / max_dim
# obj.scale = (scale, scale, scale)

# # # --------------------
# # # Normalize scale & center
# # # --------------------
# # bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
# # obj.location = (0, 0, 0)

# # max_dim = max(obj.dimensions)
# # obj.scale = (1/max_dim, 1/max_dim, 1/max_dim)

# # --------------------
# # Camera
# # --------------------
# cam_data = bpy.data.cameras.new("Camera")
# cam = bpy.data.objects.new("Camera", cam_data)
# bpy.context.collection.objects.link(cam)
# bpy.context.scene.camera = cam

# cam.location = (0, -2.5, 0)
# cam.rotation_euler = (math.radians(90), 0, 0)

# # --------------------
# # Light
# # --------------------
# light_data = bpy.data.lights.new(name="Light", type='AREA')
# light = bpy.data.objects.new(name="Light", object_data=light_data)
# bpy.context.collection.objects.link(light)
# light.location = (0, -2, 2)

# # --------------------
# # Render settings
# # --------------------
# scene = bpy.context.scene
# scene.render.engine = 'CYCLES'
# scene.render.resolution_x = 512
# scene.render.resolution_y = 512
# scene.render.film_transparent = True

# # --------------------
# # FRONT VIEW
# # --------------------
# scene.render.filepath = os.path.join(out_dir, "front.png")
# bpy.ops.render.render(write_still=True)

# # --------------------
# # PROFILE VIEW (rotate object)
# # --------------------
# obj.rotation_euler[2] += math.radians(90)
# scene.render.filepath = os.path.join(out_dir, "side.png")
# bpy.ops.render.render(write_still=True)
