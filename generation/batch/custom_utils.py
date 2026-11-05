import json
import os
import re
import zipfile

def prepare_directories(*paths):
    print("-"*80)
    for path in paths:
        os.makedirs(path, exist_ok=True)
        print(f"[INFO] Directory ready: {path}")
    print("-"*80)
    
    
def prepare_output_dir(file_path, val_str = None):
    
    directory = os.path.dirname(file_path)
    
    if not os.path.isdir(file_path): 
        
        filename = os.path.basename(file_path)

        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created - {directory}")
        if val_str:
            name, ext = os.path.splitext(filename)
            new_filename = f"{val_str}_{name}{ext}"
            return os.path.join(directory, new_filename)
    else:
        if val_str:
            return os.path.join(file_path, f"{val_str}_obejct.glb")          
            
    return os.path.join(directory, "object.glb")  

def check_file_exists(file_path):
    if os.path.exists(file_path):
        print(f"File already exists: {file_path}")
        return True
    else:
        print(f"File does not exist: {file_path}")
        return False
 

def extract_dimensions_from_prompt_cm(prompt: str) -> dict:
    """
    Extract dimensions from prompt where values are in CENTIMETERS.
    Returns dict with values in cm.
    """
    dimensions = {}
    
    patterns = {
        'total_length': r'Total length:\s*([\d.]+)\s*cm',
        'top_width': r'top internal width\s*([\d.]+)\s*cm',
        'bottom_width': r'bottom internal width\s*([\d.]+)\s*cm',
        'channel_depth': r'channel depth\s*([\d.]+)\s*cm',
        'wall_thickness': r'wall thickness is\s*([\d.]+)\s*cm',
        'notch_width': r'notch:\s*([\d.]+)\s*cm wide',
        'notch_depth': r'(\d+\.\d+)\s*cm deep'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            dimensions[key] = float(match.group(1))
    
    return dimensions

def extract_dimensions_from_prompt_detailed(prompt: str) -> dict:
    """
    Extract ALL dimensions from the detailed prompt.
    Returns dict with values in cm.
    """
    dimensions = {}
    
    patterns = {
        'total_length': r'Total length:\s*([\d.]+)\s*cm',
        'top_width': r'top internal width\s*([\d.]+)\s*cm',
        'bottom_width': r'bottom internal width\s*([\d.]+)\s*cm',
        'channel_depth': r'channel depth\s*([\d.]+)\s*cm',
        'wall_thickness': r'wall thickness is\s*([\d.]+)\s*cm',
        'notch_width': r'notch:\s*([\d.]+)\s*cm wide',
        'notch_depth': r'(\d+\.\d+)\s*cm deep'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            dimensions[key] = float(match.group(1))
    
    return dimensions


def convert_prompt_cm_to_mm_simple(prompt: str) -> str:
    """
    Simple conversion: just change cm to mm in the existing prompt.
    Keeps all the detailed terminology, just converts units.
    Uses XX.XX format (2 decimal places).
    """
    # Extract dimensions in cm
    dims_cm = extract_dimensions_from_prompt_detailed(prompt)
    
    if not dims_cm:
        print(f"WARNING: No dimensions found in prompt!")
        return prompt
    
    # Replace each dimension found in the prompt with mm version
    new_prompt = prompt
    
    replacements = [
        ('total_length', r'Total length:\s*([\d.]+)\s*cm', 'Total length'),
        ('top_width', r'top internal width\s*([\d.]+)\s*cm', 'top internal width'),
        ('bottom_width', r'bottom internal width\s*([\d.]+)\s*cm', 'bottom internal width'),
        ('channel_depth', r'channel depth\s*([\d.]+)\s*cm', 'channel depth'),
        ('wall_thickness', r'wall thickness is\s*([\d.]+)\s*cm', 'wall thickness is'),
        ('notch_width', r'(\d+\.\d+)\s*cm wide', None),  # Special case
        ('notch_depth', r'(\d+\.\d+)\s*cm deep', None),  # Special case
    ]
    
    for key, pattern, prefix in replacements:
        if key in dims_cm:
            match = re.search(pattern, new_prompt, re.IGNORECASE)
            if match:
                old_value = match.group(1)
                new_value = dims_cm[key] * 10  # Convert to mm
                
                if key == 'notch_width':
                    new_prompt = new_prompt.replace(f"{old_value} cm wide", f"{new_value:.2f} mm wide")
                elif key == 'notch_depth':
                    new_prompt = new_prompt.replace(f"{old_value} cm deep", f"{new_value:.2f} mm deep")
                else:
                    new_prompt = new_prompt.replace(f"{prefix} {old_value} cm", f"{prefix} {new_value:.2f} mm")
    
    return new_prompt

def convert_prompt_cm_to_mm(prompt: str) -> str:
    """
    Convert a prompt from centimeters to millimeters.
    Finds all patterns like "X.XX cm" and converts them to "XXX.X mm"
    """
    # Extract dimensions in cm
    dims_cm = extract_dimensions_from_prompt_cm(prompt)
    
    if not dims_cm:
        print(f"WARNING: No dimensions found in prompt!")
        return prompt
    
    # Convert each dimension found in the prompt
    new_prompt = prompt
    
    # Replace "Total length: X.XX cm" with "Total length: XXX.X mm"
    if 'total_length' in dims_cm:
        old_text = f"Total length: {dims_cm['total_length']:.2f} cm"
        new_text = f"Total length: {dims_cm['total_length'] * 10:.1f} mm"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    # Replace width/depth patterns
    # "top internal width X.XX cm" -> "top internal width XXX.X mm"
    if 'top_width' in dims_cm:
        old_text = f"top internal width {dims_cm['top_width']:.2f} cm"
        new_text = f"top internal width {dims_cm['top_width'] * 10:.1f} mm"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    if 'bottom_width' in dims_cm:
        old_text = f"bottom internal width {dims_cm['bottom_width']:.2f} cm"
        new_text = f"bottom internal width {dims_cm['bottom_width'] * 10:.1f} mm"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    if 'channel_depth' in dims_cm:
        old_text = f"channel depth {dims_cm['channel_depth']:.2f} cm"
        new_text = f"channel depth {dims_cm['channel_depth'] * 10:.1f} mm"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    if 'wall_thickness' in dims_cm:
        old_text = f"wall thickness is {dims_cm['wall_thickness']:.2f} cm"
        new_text = f"wall thickness is {dims_cm['wall_thickness'] * 10:.1f} mm"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    # Notch dimensions
    if 'notch_width' in dims_cm:
        old_text = f"{dims_cm['notch_width']:.2f} cm wide"
        new_text = f"{dims_cm['notch_width'] * 10:.1f} mm wide"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    if 'notch_depth' in dims_cm:
        old_text = f"{dims_cm['notch_depth']:.2f} cm deep"
        new_text = f"{dims_cm['notch_depth'] * 10:.1f} mm deep"
        new_prompt = new_prompt.replace(old_text, new_text)
    
    return new_prompt


def regenerate_meta_files_in_zip(input_zip_path: str, output_zip_path: str):
    """
    Read a zip file, convert all _meta.json prompts from cm to mm,
    and write to a new zip file.
    """
    print(f"Processing zip: {input_zip_path}")
    print(f"Output will be saved to: {output_zip_path}")
    
    converted_count = 0
    total_count = 0
    
    with zipfile.ZipFile(input_zip_path, 'r') as zip_in:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            # Process each file in the zip
            for file_info in zip_in.filelist:
                filename = file_info.filename
                
                # Read file data
                file_data = zip_in.read(filename)
                
                # If it's a _meta.json file (but not _compressed_meta.json) #TODO write to JSON all metrics separately
                if filename.endswith('.json') and not filename.endswith('_compressed_meta.json'):
                    total_count += 1
                    
                    try:
                        # Parse JSON
                        json_data = json.loads(file_data.decode('utf-8'))
                        
                        # Get original prompt
                        original_prompt = json_data.get('prompt', '')
                        
                        if not original_prompt:
                            print(f"WARNING: No prompt in {filename}")
                            zip_out.writestr(file_info, file_data)
                            continue
                        
                        # Convert prompt from cm to mm
                        new_prompt = convert_prompt_cm_to_mm(original_prompt)
                        
                        # Update JSON
                        json_data['prompt'] = new_prompt
                        json_data['prompt_original_cm'] = original_prompt  # Keep original for reference
                        
                        # Write updated JSON to new zip
                        new_json_data = json.dumps(json_data, indent=2, ensure_ascii=False)
                        zip_out.writestr(file_info, new_json_data.encode('utf-8'))
                        
                        converted_count += 1
                        
                        if converted_count <= 3:  # Show first 3 conversions
                            print(f"\n[{converted_count}] {filename}")
                            print(f"  OLD (cm): {original_prompt[:100]}...")
                            print(f"  NEW (mm): {new_prompt[:100]}...")
                        
                    except Exception as e:
                        print(f"ERROR processing {filename}: {e}")
                        # Write original file if conversion fails
                        zip_out.writestr(file_info, file_data)
                
                else:
                    # Copy all other files unchanged
                    zip_out.writestr(file_info, file_data)
    
    print(f"\n✅ Conversion complete!")
    print(f"   Converted {converted_count}/{total_count} meta.json files")
    print(f"   Output saved to: {output_zip_path}")