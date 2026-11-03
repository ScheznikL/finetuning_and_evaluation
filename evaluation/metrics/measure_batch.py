import argparse
import trimesh
import numpy as np
import json
import zipfile
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import tempfile
import shutil


import trimesh

import trimesh

from utils.visualise import visualize_slices_upright

def is_mesh_empty(scene, file_path = None):
    try:
        #scene = trimesh.load(file_path)
        
        # 1. If it's a Scene, check if any geometry exists within it
        if isinstance(scene, trimesh.Scene):
            if not scene.geometry:
                return True
            
            # Sum up vertices from all individual meshes in the scene
            total_vertices = sum(len(m.vertices) for m in scene.geometry.values())
            return total_vertices == 0
            
        # 2. If it loaded as a single Mesh/Geometry object
        return len(scene.vertices) == 0
        
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return True

def extract_dimensions_from_json(metadata: dict, prompt_format: str = 'auto') -> Dict[str, float]:
    """
    Extract dimensions directly from JSON metadata.
    
    Args:
        metadata: The JSON metadata object
        prompt_format: 'training_aligned', 'detailed', or 'auto' (auto-detect from JSON)
    
    Returns:
        Dictionary with dimensions in mm
    """
    dimensions = {}
    
    # Check if dimensions field exists in metadata
    if 'dimensions' not in metadata:
        print("  ⚠️  No 'dimensions' field in metadata, falling back to prompt parsing")
        if isinstance(metadata, str):
            return extract_dimensions_from_prompt_fallback(metadata)
        
        return extract_dimensions_from_prompt_fallback(metadata.get('prompt'))
    
    dims = metadata['dimensions']
    
    # Auto-detect format from JSON structure
    if prompt_format == 'auto':
        if 'format' in metadata:
            prompt_format = metadata['format']
        elif 'total_height_mm' in dims:
            prompt_format = 'training_aligned'
        elif 'top_width_mm' in dims:
            prompt_format = 'detailed'
        else:
            print("  ⚠️  Could not auto-detect format, using training_aligned")
            prompt_format = 'training_aligned'
    
    print(f"  📋 Using format: {prompt_format}")
    
    # Extract based on format
    if prompt_format == 'training_aligned':
        # Training format: total_length, total_height, total_width
        dimensions['total_length'] = dims.get('total_length_mm')
        dimensions['total_height'] = dims.get('total_height_mm')
        dimensions['total_width'] = dims.get('total_width_mm')
        
        # Also extract original dimensions if available (for reference)
        if 'original_dimensions' in dims:
            orig = dims['original_dimensions']
            dimensions['_original_top_width'] = orig.get('top_width_mm')
            dimensions['_original_bottom_width'] = orig.get('bottom_width_mm')
            dimensions['_original_channel_depth'] = orig.get('channel_depth_mm')
    
    elif prompt_format in ['detailed', 'simple_mm']:
        # Detailed format: all specific measurements
        dimensions['total_length'] = dims.get('total_length_mm')
        dimensions['top_width'] = dims.get('top_width_mm')
        dimensions['bottom_width'] = dims.get('bottom_width_mm')
        dimensions['channel_depth'] = dims.get('channel_depth_mm')
        dimensions['wall_thickness'] = dims.get('wall_thickness_mm')
        dimensions['notch_width'] = dims.get('notch_width_mm')
        dimensions['notch_depth'] = dims.get('notch_depth_mm')
    
    else:
        print(f"  ⚠️  Unknown format '{prompt_format}', using training_aligned")
        dimensions['total_length'] = dims.get('total_length_mm')
        dimensions['total_height'] = dims.get('total_height_mm')
        dimensions['total_width'] = dims.get('total_width_mm')
    
    dimensions['_format'] = prompt_format
    return dimensions


def extract_dimensions_from_prompt_fallback(prompt: str) -> Dict[str, float]:
    """
    Fallback: Extract dimensions from prompt text (old method).
    Used only if JSON dimensions field is not available.
    """
    dimensions = {}
    
    # Patterns for millimeters
    patterns_mm = {
        'total_length': r'Total length:\s*([\d.]+)\s*mm',
        'top_width': r'top internal width\s*([\d.]+)\s*mm',
        'bottom_width': r'bottom internal width\s*([\d.]+)\s*mm',
        'channel_depth': r'channel depth\s*([\d.]+)\s*mm',
        'wall_thickness': r'wall thickness is\s*([\d.]+)\s*mm',
        'notch_width': r'notch:\s*([\d.]+)\s*mm wide',
        'notch_depth': r'(\d+\.\d+)\s*mm deep'
    }
    
    # Patterns for centimeters
    patterns_cm = {
        'total_length': r'length[:\s]*([\d.]+)\s*cm',
        'top_width': r'top width\s*([\d.]+)\s*cm',
        'bottom_width': r'bottom width\s*([\d.]+)\s*cm',
        'channel_depth': r'depth\s*([\d.]+)\s*cm',
        'wall_thickness': r'wall\s*([\d.]+)\s*cm',
        'notch_width': r'notch \s*([\d.]+)\s*cm wide',
        'notch_depth': r'(\d+\.\d+)\s*cm deep'
    }
    
    
    # Try mm first
    units_used = None
    for key, pattern in patterns_mm.items():
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            dimensions[key] = float(match.group(1))  # Already in mm
            units_used = 'mm'
    
    # If no mm found, try cm and convert
    if not dimensions:
        for key, pattern in patterns_cm.items():
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                dimensions[key] = float(match.group(1)) * 10  # Convert cm to mm
                units_used = 'cm'
    
    dimensions['_units_detected'] = units_used
    dimensions['_format'] = 'fallback_from_prompt'
    return dimensions



def measure_model_dimensions_mm_with_vis(mesh, mesh_path: str, visualize: bool = False, 
                           output_dir: str = "./", uuid: str = None, normalize: bool = False,
                           prompt_dims: Dict[str, float] = None,
                           view_elev: float = 20, view_azim: float = 45) -> Dict[str, float]:
    """
    Measure actual dimensions from the 3D model.
    Returns measurements in MILLIMETERS (assuming 1 unit = 1 meter).
    
    Args:
        mesh_path: Path to mesh file
        visualize: If True, save visualization images of slices
        output_dir: Directory to save visualizations
        uuid: UUID for naming visualization files
        normalize: If True, reorient and scale ONLY length axis to match prompt
        prompt_dims: Dictionary of prompt dimensions for length scaling
        view_elev: Elevation angle for 3D visualization (default: 20)
        view_azim: Azimuth angle for 3D visualization (default: 45)
    """
    try:
        if isinstance(mesh, (trimesh.Geometry, trimesh.Scene)):
            loaded = mesh
        else:               
            loaded = trimesh.load(mesh_path)
        
        # Handle Scene objects
        if isinstance(loaded, trimesh.Scene):
            if len(loaded.geometry) == 0:
                return {}
            mesh = loaded.to_geometry()
        else:
            mesh = loaded
        
        # Store original extents and scale for reference
        original_extents = mesh.extents.copy()
        original_scale = mesh.scale
        
        # Normalize mesh if requested
        if normalize:
            # Center the mesh at origin
            mesh.vertices -= mesh.centroid
            
            # SMART NORMALIZATION: Reorient so longest axis becomes Y (length)
            # This ensures consistent measurement regardless of original orientation
            extents = mesh.extents
            axes_order = np.argsort(extents)[::-1]  # Indices sorted by size, largest first
            
            # Create rotation matrix to align longest axis with Y
            longest_axis_idx = axes_order[0]  # Index of longest axis (0=X, 1=Y, 2=Z)
            
            print(f"  🔄 Original extents: X={extents[0]*1000:.2f}mm, Y={extents[1]*1000:.2f}mm, Z={extents[2]*1000:.2f}mm")
            print(f"  🔄 Longest axis is: {['X', 'Y', 'Z'][longest_axis_idx]}")
            
            # Reorient mesh so longest axis aligns with Y-axis
            if longest_axis_idx == 0:  # Longest is X, rotate X->Y
                # Rotate 90° around Z to move X to Y
                angle = np.pi / 2
                rotation_matrix = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                mesh.apply_transform(rotation_matrix)
                print(f"  🔄 Rotated X-axis to Y-axis (90° around Z)")
            elif longest_axis_idx == 2:  # Longest is Z, rotate Z->Y
                # Rotate 90° around X to move Z to Y
                angle = np.pi / 2
                rotation_matrix = trimesh.transformations.rotation_matrix(angle, [1, 0, 0])
                mesh.apply_transform(rotation_matrix)
                print(f"  🔄 Rotated Z-axis to Y-axis (90° around X)")
            else:  # longest_axis_idx == 1, already aligned with Y
                print(f"  🔄 Already aligned with Y-axis, no rotation needed")
            
            # Now scale uniformly based on prompt length (keeping proportions)
            # This is like Blender's uniform scaling: S, [scale_factor]
            if prompt_dims and 'total_length' in prompt_dims:
                # Get the target length from prompt (in mm)
                target_length_mm = prompt_dims['total_length']
                
                # Current length along Y-axis (in meters, so convert to mm)
                current_length_mm = mesh.extents[1] * 1000
                
                # Calculate scale factor based on length
                # This factor will be applied to ALL axes (uniform scaling)
                scale_factor = target_length_mm / current_length_mm
                
                print(f"  📏 Scaling uniformly (keeping proportions) based on length:")
                print(f"     Current length: {current_length_mm:.2f}mm")
                print(f"     Target length: {target_length_mm:.2f}mm")
                print(f"     Scale factor: {scale_factor:.4f}")
                print(f"     All axes (X, Y, Z) will scale by {scale_factor:.4f}")
                
                # Apply UNIFORM scaling to all vertices
                # This is like Blender: S, [scale_factor] (or S, Shift+Z for uniform XY)
                mesh.vertices *= scale_factor
                
                print(f"     This preserves proportions - if width/depth don't match prompt,")
                print(f"     it means the AI generated wrong proportions!")
            else:
                print(f"  ⚠️  No prompt dimensions provided, skipping scaling")
            
            # Verify final orientation
            final_extents = mesh.extents * 1000
            print(f"  ✅ Final extents: X={final_extents[0]:.2f}mm, Y={final_extents[1]:.2f}mm, Z={final_extents[2]:.2f}mm")
            
            # Compare with prompt if available
            if prompt_dims:
                if 'total_length' in prompt_dims:
                    print(f"     Length: {final_extents[1]:.2f}mm (target: {prompt_dims['total_length']:.2f}mm)")
                if 'total_width' in prompt_dims:
                    avg_width = final_extents[0]  # X is width
                    print(f"     Width:  {avg_width:.2f}mm (target: {prompt_dims['total_width']:.2f}mm)")
                if 'total_height' in prompt_dims:
                    print(f"     Depth:  {final_extents[2]:.2f}mm (target: {prompt_dims['total_height']:.2f}mm)")
        
        # Basic extents (convert to mm: meters * 1000)
        extents = mesh.extents * 1000  # X, Y, Z in mm
        
        # Get bounds
        min_y = mesh.bounds[0][1]
        max_y = mesh.bounds[1][1]
        height = (max_y - min_y) * 1000  # Total height in mm
        
        measurements = {
            'total_length': height,  # Y axis as height/length
            'width_x': extents[0],
            'depth_z': extents[2],
            'normalized': normalize,
            'original_scale': original_scale if normalize else None,
            'original_extents_mm': (original_extents * 1000).tolist() if normalize else None
        }
        
        # Store slice objects for visualization
        slices = {}
        
        # Define slice positions
        slice_positions = {
            'top_2pct': 0.02,
            'top_5pct': 0.05,
            'middle': 0.50,
            'bottom_5pct': 0.05,
            'bottom_2pct': 0.02
        }
        
        # Measure top width (top 2% slice)
        try:
            top_slice_2pct = mesh.section(
                plane_origin=[0, max_y - ((max_y - min_y) * 0.02), 0],
                plane_normal=[0, 1, 0]
            )
            if top_slice_2pct:
                measurements['top_width_2pct'] = top_slice_2pct.extents[0] * 1000  # mm
                slices['top_2pct'] = top_slice_2pct
                # Keep backward compatibility
                measurements['top_width'] = measurements['top_width_2pct']
        except:
            measurements['top_width_2pct'] = None
            measurements['top_width'] = None
        
        # Measure top width (top 5% slice)
        try:
            top_slice_5pct = mesh.section(
                plane_origin=[0, max_y - ((max_y - min_y) * 0.05), 0],
                plane_normal=[0, 1, 0]
            )
            if top_slice_5pct:
                measurements['top_width_5pct'] = top_slice_5pct.extents[0] * 1000  # mm
                slices['top_5pct'] = top_slice_5pct
        except:
            measurements['top_width_5pct'] = None
        
        # Measure bottom width (bottom 2% slice)
        try:
            bottom_slice_2pct = mesh.section(
                plane_origin=[0, min_y + ((max_y - min_y) * 0.02), 0],
                plane_normal=[0, 1, 0]
            )
            if bottom_slice_2pct:
                measurements['bottom_width_2pct'] = bottom_slice_2pct.extents[0] * 1000  # mm
                slices['bottom_2pct'] = bottom_slice_2pct
                # Keep backward compatibility
                measurements['bottom_width'] = measurements['bottom_width_2pct']
        except:
            measurements['bottom_width_2pct'] = None
            measurements['bottom_width'] = None
        
        # Measure bottom width (bottom 5% slice)
        try:
            bottom_slice_5pct = mesh.section(
                plane_origin=[0, min_y + ((max_y - min_y) * 0.05), 0],
                plane_normal=[0, 1, 0]
            )
            if bottom_slice_5pct:
                measurements['bottom_width_5pct'] = bottom_slice_5pct.extents[0] * 1000  # mm
                slices['bottom_5pct'] = bottom_slice_5pct
        except:
            measurements['bottom_width_5pct'] = None
        
        # Measure middle width (50% slice)
        try:
            middle_y = (max_y + min_y) / 2
            middle_slice = mesh.section(
                plane_origin=[0, middle_y, 0],
                plane_normal=[0, 1, 0]
            )
            if middle_slice:
                measurements['middle_width'] = middle_slice.extents[0] * 1000  # mm
                slices['middle'] = middle_slice
        except:
            measurements['middle_width'] = None
        
        # Measure channel depth (approximate as Z extent)
        measurements['channel_depth'] = extents[2]
        
        # Visualize if requested
        if visualize and output_dir and uuid:
            visualize_slices_upright(mesh, slices, measurements, output_dir, uuid, 
                           min_y, max_y, height, view_elev=view_elev, view_azim=view_azim)
        
        return measurements
        
    except Exception as e:
        print(f"Error measuring model {mesh_path}: {e}")
        return {}


def measure_model_dimensions_cm(mesh: str | trimesh.Geometry | trimesh.Scene, path = None) -> Dict[str, float]:
    """
    Measure actual dimensions from the 3D model.
    Returns measurements in cm.
    """
    try:
        if isinstance(mesh, str):
            loaded = trimesh.load(mesh)
        elif isinstance(mesh, (trimesh.Geometry, trimesh.Scene)):
            loaded = mesh
        else: 
            raise ValueError("no mesh found")
        
        # Handle Scene objects
        if isinstance(loaded, trimesh.Scene):
            if len(loaded.geometry) == 0:
                return {}
            mesh = loaded.dump(concatenate=True)
        else:
            mesh = loaded
       
        # Basic extents (convert to cm, assuming 1 unit = 1 meter)
        extents = mesh.extents * 100  # X, Y, Z in cm
        
        # Get bounds
        min_y = mesh.bounds[0][1]
        max_y = mesh.bounds[1][1]
        height = (max_y - min_y) * 100  # Total height in cm
        
        measurements = {
            'total_length': height,  # Y axis as height/length
            'width_x': extents[0],
            'depth_z': extents[2]
        }
        
        # Measure top width (top 2% slice)
        try:
            top_slice = mesh.section(
                plane_origin=[0, max_y - ((max_y - min_y) * 0.02), 0],
                plane_normal=[0, 1, 0]
            )
            if top_slice:
                measurements['top_width'] = top_slice.extents[0] * 100
        except:
            measurements['top_width'] = None
        
        # Measure bottom width (bottom 2% slice)
        try:
            bottom_slice = mesh.section(
                plane_origin=[0, min_y + ((max_y - min_y) * 0.02), 0],
                plane_normal=[0, 1, 0]
            )
            if bottom_slice:
                measurements['bottom_width'] = bottom_slice.extents[0] * 100
        except:
            measurements['bottom_width'] = None
        
        # Measure channel depth (approximate as Z extent)
        measurements['channel_depth'] = extents[2]
        
        return measurements
        
    except Exception as e:
        print(f"Error measuring model {mesh}: {e}")
        return {}


def calculate_differences(prompt_dims: Dict[str, float], 
                         model_dims: Dict[str, float]) -> Dict[str, Dict]:
    """
    Calculate differences between prompt specifications and model measurements.
    Handles both training_aligned and detailed formats.
    Both values should be in mm.
    Returns absolute difference, percentage difference, and both values.
    """
    differences = {}
    
    print(f"[DEBUG] in calculate_differences model_dims are: {model_dims} \n\r prompt_dims are {prompt_dims}")
    
    # Determine format
    format_type = prompt_dims.get('_format', 'detailed')
    
    if format_type == 'training_aligned':
        # Training format: map total_length/height/width to model measurements
        dimension_mapping = {
            'total_length': 'total_length',  # Y axis
            'total_height': 'channel_depth',  # Z axis (depth becomes height in training)
            'total_width': ('top_width', 'bottom_width'),  # Average of top/bottom
        }
        
        for prompt_key, model_key in dimension_mapping.items():
            if prompt_key in prompt_dims:
                prompt_val = prompt_dims[prompt_key]
                
                # Handle width which needs averaging
                if isinstance(model_key, tuple):
                    # Average top and bottom width
                    top = model_dims.get(model_key[0])
                    bottom = model_dims.get(model_key[1])
                    if top is not None and bottom is not None:
                        model_val = (top + bottom) / 2
                    elif top is not None:
                        model_val = top
                    elif bottom is not None:
                        model_val = bottom
                    else:
                        print("[INFO] There was NO TOP & BOTTOM")
                        continue
                else:
                    model_val = model_dims.get(model_key)
                
                if model_val is not None and prompt_val > 0:
                    abs_diff = abs(prompt_val - model_val)
                    pct_diff = (abs_diff / prompt_val) * 100
                    
                    differences[prompt_key] = {
                        'prompt_value': prompt_val,
                        'model_value': model_val,
                        'absolute_diff': abs_diff,
                        'percentage_diff': pct_diff
                    }
    
    else:  # detailed or simple_mm format
        # Detailed format: direct mapping
        dimension_mapping = {
            'total_length': 'total_length',
            'top_width': 'top_width',
            'bottom_width': 'bottom_width',
            'channel_depth': 'channel_depth',
        }
        
        for prompt_key, model_key in dimension_mapping.items():
            if prompt_key in prompt_dims and model_key in model_dims:
                if model_dims[model_key] is not None:
                    prompt_val = prompt_dims[prompt_key]
                    model_val = model_dims[model_key]
                    
                    if prompt_val > 0:
                        abs_diff = abs(prompt_val - model_val)
                        pct_diff = (abs_diff / prompt_val) * 100
                        
                        differences[prompt_key] = {
                            'prompt_value': prompt_val,
                            'model_value': model_val,
                            'absolute_diff': abs_diff,
                            'percentage_diff': pct_diff
                        }
    
    return differences



def process_all_models(zip_path: str, prompts_json_file, check_format, out_vis_dir, 
                      normalize: bool = False, view_elev: float = 20, 
                      view_azim: float = 45) -> Tuple[List[Dict], Dict[str, List[float]]]:
    """
    Process all models in the zip file.
    Returns list of individual results and aggregated statistics.
    
    Args:
        zip_path: Path to zip file containing models
        prompts_json_file: Path to prompts JSON file
        check_format: Format to check ('training_aligned' or 'detailed')
        out_vis_dir: Output directory for visualizations
        normalize: If True, normalize meshes before measurement
        view_elev: Elevation angle for 3D visualizations
        view_azim: Azimuth angle for 3D visualizations
    """
    all_results = []
    all_differences = None
    format_detected = None
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Extracting zip file to temporary directory...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # The zip directly contains 100_test_models directory
        models_dir = Path(temp_dir) / '100_test_models'
        
        if not models_dir.exists():
            print(f"Models directory not found: {models_dir}")
            print(f"Searched in: {temp_dir}")
            print(f"Available directories:")
            for root, dirs, files in os.walk(temp_dir):
                for d in dirs:
                    print(f"  - {os.path.join(root, d)}")
            return [], {}
        
        print(f"Processing models from: {models_dir}")
        
        # Get all unique UUIDs
        glb_files = list(models_dir.glob('*.glb'))
        print(f"Found {len(glb_files)} GLB files")
        
        for idx, glb_file in enumerate(glb_files, 1):
            uuid = glb_file.stem
            print(f"\n[{idx}/{len(glb_files)}] Processing {uuid}...")
            
            #Check the file and mesh
            try:
                mesh = trimesh.load(glb_file)
            except IndexError as in_e:
                print(f"[Error] At {uuid} the file is empty!\n\rError message: {in_e}")
                print("Skiping ...")
                continue
            
            if is_mesh_empty(mesh, glb_file):
                print(f"[Error] At {uuid} the mesh is empty!")
                print("Skiping ...")
                continue
            
            meta_file = models_dir / f"{uuid}_meta.json"   
            prompt_id = 'prompt'
            
            if check_format == 'detailed':
                meta_file = models_dir / f"{uuid}_compressed_meta.json"
                prompt_id = 'prompt_clip'   
            # Load metadata
            if not meta_file.exists():
                print(f"  ⚠️  Metadata file not found: {meta_file}")
                print(f"Searching ...")
                meta_file = models_dir / f"{uuid}.json"
                prompt_id = 'prompt'
                if not meta_file.exists():
                    print(f"  ⚠️  Metadata file not found: {meta_file}")
                    continue        
            
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    prompt = metadata.get(prompt_id)
                
                if prompts_json_file is not None:
                    with open(prompts_json_file, 'r', encoding='utf-8') as f:
                        prompts_detailed = json.load(f)
                        obj_details = next((obj for obj in prompts_detailed if obj['uuid'] == uuid), None)
                else:
                    obj_details = prompt
                    
                if not prompt:
                    print(f"  ⚠️  No prompt found in metadata")
                    continue
                
                # Extract dimensions from prompt
                prompt_dims = extract_dimensions_from_json(obj_details, check_format)
                format_type = prompt_dims.get('_format', 'unknown')
                
                #adjust differences
                if not all_differences:
                    if format_type == 'training_aligned':
                        all_differences = {
                            'total_length': [],
                            'total_height': [],
                            'total_width': []
                        }
                    else:  # detailed format
                        all_differences = {
                            'total_length': [],
                            'top_width': [],
                            'bottom_width': [],
                            'channel_depth': []
                        }

                # Remove internal fields before storing
                units_detected = prompt_dims.get('_units_detected', None)
                print(f"  Prompt dimensions in {units_detected}: {len([k for k in prompt_dims.keys() if not k.startswith('_')])} found ({format_type}) ")
                
                # Measure model (original)
                indx_vis = 1
                should_visualize = (idx - 1) == indx_vis
                
                if check_format == "training_aligned":
                    model_dims_original = measure_model_dimensions_mm_with_vis(
                        mesh,
                        output_dir=out_vis_dir,
                        visualize=should_visualize,
                        mesh_path=str(glb_file), 
                        uuid=f"{glb_files[indx_vis].stem}_original" if normalize else glb_files[indx_vis].stem,
                        normalize=False,
                        prompt_dims=None,  # No prompt dims needed for original
                        view_elev=view_elev,
                        view_azim=view_azim
                    )
                else:
                    model_dims_original = measure_model_dimensions_cm(mesh, str(glb_file))
                
                # Measure model (normalized) if requested
                if normalize:
                    # Reload mesh for normalized measurement
                    mesh_norm = trimesh.load(glb_file)
                    if isinstance(mesh_norm, trimesh.Scene):
                        mesh_norm = mesh_norm.to_geometry()
                    
                    if check_format == "training_aligned":
                        model_dims_normalized = measure_model_dimensions_mm_with_vis(
                            mesh_norm,
                            output_dir=out_vis_dir,
                            visualize=should_visualize,
                            mesh_path=str(glb_file), 
                            uuid=f"{glb_files[indx_vis].stem}_normalized",
                            normalize=True,
                            prompt_dims=prompt_dims,  # Pass prompt dims for smart scaling
                            view_elev=view_elev,
                            view_azim=view_azim
                        )
                    else:
                        model_dims_normalized = measure_model_dimensions_cm(mesh_norm, str(glb_file))
                else:
                    model_dims_normalized = None
                    
                if should_visualize:
                    print(f"  🎨 VISUALIZED this model!")
                    
                print(f"  Model measurements (original): {len(model_dims_original)} taken")
                if normalize:
                    print(f"  Model measurements (normalized): {len(model_dims_normalized)} taken")
                
                # Calculate differences for original
                differences_original = calculate_differences(prompt_dims, model_dims_original)
                
                # Calculate differences for normalized if available
                if normalize and model_dims_normalized:
                    differences_normalized = calculate_differences(prompt_dims, model_dims_normalized)
                else:
                    differences_normalized = None
                
                # Store results
                result = {
                    'uuid': uuid,
                    'prompt': prompt,
                    'prompt_dimensions': prompt_dims,
                    'model_dimensions_original': model_dims_original,
                    'differences_original': differences_original,
                    'units': 'mm'
                }
                
                if normalize:
                    result['model_dimensions_normalized'] = model_dims_normalized
                    result['differences_normalized'] = differences_normalized
                
                all_results.append(result)
                
                # Aggregate differences (using original measurements)
                for dim_name, diff_data in differences_original.items():
                    if dim_name in all_differences:
                        all_differences[dim_name].append(diff_data['absolute_diff'])
                
               # Print summary for this model
                if differences_original:
                    print(f"  Differences calculated (original, in mm):")
                    for dim_name, diff_data in differences_original.items():
                        print(f"    {dim_name}: {diff_data['absolute_diff']:.2f} mm "
                              f"({diff_data['percentage_diff']:.2f}%) - "
                              f"Prompt: {diff_data['prompt_value']:.2f} mm, "
                              f"Model: {diff_data['model_value']:.2f} mm")
                
                if normalize and differences_normalized:
                    print(f"  Differences calculated (normalized, in mm):")
                    for dim_name, diff_data in differences_normalized.items():
                        print(f"    {dim_name}: {diff_data['absolute_diff']:.2f} mm "
                              f"({diff_data['percentage_diff']:.2f}%) - "
                              f"Prompt: {diff_data['prompt_value']:.2f} mm, "
                              f"Model: {diff_data['model_value']:.2f} mm")
                else:
                    if not differences_original:
                        print(f"  ⚠️  No matching dimensions found")
                
            except Exception as e:
                print(f"  ❌ Error processing {uuid}: {e}")
                continue
    
    return all_results, all_differences


def calculate_statistics(all_differences: Dict[str, List[float]]) -> Dict:
    """
    Calculate average, median, std dev, min, max for each dimension.
    """
    stats = {}
    
    for dim_name, diff_list in all_differences.items():
        if diff_list:
            stats[dim_name] = {
                'count': len(diff_list),
                'mean': np.mean(diff_list),
                'median': np.median(diff_list),
                'std': np.std(diff_list),
                'min': np.min(diff_list),
                'max': np.max(diff_list)
            }
        else:
            stats[dim_name] = {
                'count': 0,
                'mean': 0,
                'median': 0,
                'std': 0,
                'min': 0,
                'max': 0
            }
    
    return stats


def save_results(all_results: List[Dict], stats: Dict, output_dir: str):
    """
    Save detailed results and summary statistics to JSON files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save detailed results
    detailed_file = os.path.join(output_dir, 'detailed_results.json')
    with open(detailed_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Detailed results saved to: {detailed_file}")
    
    # Save statistics
    stats_file = os.path.join(output_dir, 'statistics_summary.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    print(f"✅ Statistics summary saved to: {stats_file}")
    
    # Create human-readable summary
    summary_file = os.path.join(output_dir, 'summary_report.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BATCH MODEL ANALYSIS - SUMMARY REPORT (MILLIMETERS)\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total models analyzed: {len(all_results)}\n\n")
        
        f.write("AVERAGE DIFFERENCES BETWEEN PROMPT AND GENERATED MODELS\n")
        f.write("-" * 80 + "\n\n")
        
        for dim_name, stat_data in stats.items():
            f.write(f"{dim_name.upper().replace('_', ' ')}:\n")
            f.write(f"  Number of measurements: {stat_data['count']}\n")
            f.write(f"  Average difference: {stat_data['mean']:.3f} mm ({stat_data['mean']/10:.3f} cm)\n")
            f.write(f"  Median difference: {stat_data['median']:.3f} mm ({stat_data['median']/10:.3f} cm)\n")
            f.write(f"  Standard deviation: {stat_data['std']:.3f} mm ({stat_data['std']/10:.3f} cm)\n")
            f.write(f"  Min difference: {stat_data['min']:.3f} mm ({stat_data['min']/10:.3f} cm)\n")
            f.write(f"  Max difference: {stat_data['max']:.3f} mm ({stat_data['max']/10:.3f} cm)\n")
            f.write("\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("OVERALL AVERAGE ACROSS ALL DIMENSIONS\n")
        f.write("=" * 80 + "\n\n")
        
        all_means = [stat_data['mean'] for stat_data in stats.values() if stat_data['count'] > 0]
        if all_means:
            overall_mean = np.mean(all_means)
            f.write(f"Overall average difference: {overall_mean:.3f} mm ({overall_mean/10:.3f} cm)\n")
    
    print(f"✅ Summary report saved to: {summary_file}")


def main(zip_path, output_dir, check_format, prompts_json_file=None, batch_name=None,
         normalize=False, view_elev=20, view_azim=45):
    """
    Main function to process batch models.
    
    Args:
        zip_path: Path to zip file
        output_dir: Output directory for results
        check_format: Format to check
        prompts_json_file: Optional prompts JSON file
        batch_name: Name of the batch
        normalize: Whether to normalize meshes
        view_elev: Elevation angle for 3D visualization
        view_azim: Azimuth angle for 3D visualization
    """
    print("=" * 80)
    print("BATCH MODEL ANALYSIS - Starting Processing")
    print("=" * 80)
    print(f"Zip file: {zip_path}")
    print(f"Output directory: {output_dir}")
    print(f"Normalize meshes: {normalize}")
    print(f"View angles: elev={view_elev}°, azim={view_azim}°")
    print()
    
    # Process all models
    all_results, all_differences = process_all_models(
        zip_path, prompts_json_file, check_format, output_dir,
        normalize=normalize, view_elev=view_elev, view_azim=view_azim
    )
    
    # Calculate statistics
    print("\n" + "=" * 80)
    print("CALCULATING STATISTICS")
    print("=" * 80)
    stats = calculate_statistics(all_differences)
    
    # Print statistics to console
    print("\nSTATISTICS SUMMARY (MILLIMETERS):")
    print("-" * 80)
    for dim_name, stat_data in stats.items():
        print(f"\n{dim_name.upper().replace('_', ' ')}:")
        print(f"  Count: {stat_data['count']}")
        print(f"  Average difference: {stat_data['mean']:.3f} mm ({stat_data['mean']/10:.2f} cm)")
        print(f"  Median difference: {stat_data['median']:.3f} mm ({stat_data['median']/10:.2f} cm)")
        print(f"  Std deviation: {stat_data['std']:.3f} mm ({stat_data['std']/10:.2f} cm)")
        print(f"  Range: {stat_data['min']:.3f} - {stat_data['max']:.3f} mm")
    
    # Calculate overall average
    all_means = [stat_data['mean'] for stat_data in stats.values() if stat_data['count'] > 0]
    if all_means:
        overall_mean = np.mean(all_means)
        print(f"\n{'=' * 80}")
        print(f"OVERALL AVERAGE DIFFERENCE: {overall_mean:.3f} mm ({overall_mean/10:.2f} cm)")
        print(f"{'=' * 80}")
    
    # Save results
    save_results(all_results, stats, output_dir)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip_path", required=True, type=str,)
    parser.add_argument("--output_metrics_dir", required=True, type=str) 
    parser.add_argument("--batch_name", required=True, type=str) 
    parser.add_argument("--check_format", type=str, default=None) 
    parser.add_argument("--prompts_json_file", type=str, default=None)
    parser.add_argument("--normalize", action='store_true', 
                       help="Normalize meshes before measurement")
    parser.add_argument("--view_elev", type=float, default=20,
                       help="Elevation angle for 3D visualization (default: 20)")
    parser.add_argument("--view_azim", type=float, default=45,
                       help="Azimuth angle for 3D visualization (default: 45)")
    
    return parser.parse_args()
    

if __name__ == "__main__":
    
    args = get_args()
    
    main(args.zip_path, args.output_metrics_dir, batch_name = args.batch_name,
         prompts_json_file = args.prompts_json_file, 
         check_format = args.check_format,
         normalize = args.normalize,
         view_elev = args.view_elev,
         view_azim = args.view_azim)