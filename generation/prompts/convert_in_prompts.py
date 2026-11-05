import json
import re
from pathlib import Path


def extract_dimensions_from_prompt(prompt: str) -> dict:
    """Extract all dimensions from prompt (in cm)."""
    dimensions = {}
    
    patterns = {
        'total_length': r'Total length:\s*([\d.]+)\s*cm',
        'top_width': r'top internal width\s*([\d.]+)\s*cm',
        'bottom_width': r'bottom internal width\s*([\d.]+)\s*cm',
        'channel_depth': r'channel depth\s*([\d.]+)\s*cm',
        'wall_thickness': r'wall thickness is\s*([\d.]+)\s*cm',
        'notch_width': r'(\d+\.\d+)\s*cm wide',
        'notch_depth': r'(\d+\.\d+)\s*cm deep'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            dimensions[key] = float(match.group(1))
    
    return dimensions


def extract_texture_and_shape(prompt: str) -> tuple:
    """Extract texture, material, and shape description."""
    # Extract texture/material (e.g., "Matte White PLA")
    texture_match = re.search(r'Create only one ([^b]+?)\s+below-knee', prompt, re.IGNORECASE)
    texture = texture_match.group(1).strip() if texture_match else "Matte White PLA"
    
    # Extract style description
    style_match = re.search(r'the style ([^.]+?)\.', prompt, re.IGNORECASE)
    style = style_match.group(1).strip() if style_match else "restores natural limb silhouette"
    
    # Extract shape details
    shape_match = re.search(r'silhouette\.\s*([^.]+?)\.', prompt, re.IGNORECASE)
    shape_details = shape_match.group(1).strip() if shape_match else "Ergonomic semi-cylindrical U-shaped open channel"
    
    return texture, style, shape_details


def convert_prompt_to_mm(prompt: str) -> str:
    """
    Version 1: Simple conversion - just change cm to mm.
    Keeps all original detail, uses XX.XX format.
    Converts ALL numbers followed by 'cm' to mm.
    """
    def replace_cm_with_mm(match):
        """Helper function to convert matched cm values to mm"""
        value = float(match.group(1))
        return f"{value * 10:.2f} mm"
    
    # Replace all patterns of "number cm" with "number*10 mm"
    # This regex matches any number (including decimals) followed by " cm"
    new_prompt = re.sub(r'([\d.]+)\s*cm\b', replace_cm_with_mm, prompt)
    
    return new_prompt


def convert_prompt_to_training_format(prompt: str) -> str:
    """
    Version 2: Training-aligned format.
    Uses "Total length/height/width" terminology to match training data.
    Format: "{texture} texture below-knee prosthetic cover. Total length: XX.XX mm. Total height: XX.XX mm. Total width: XX.XX mm."
    """
    dims_cm = extract_dimensions_from_prompt(prompt)
    
    if not dims_cm:
        print(f"WARNING: No dimensions found in prompt!")
        return prompt
    
    texture, style, shape_details = extract_texture_and_shape(prompt)
    
    # Map to training dimensions:
    # - total_length → Total length
    # - channel_depth → Total height
    # - average of top/bottom width → Total width
    
    total_length_mm = dims_cm.get('total_length', 383.1) * 10
    total_height_mm = dims_cm.get('channel_depth', 52.2) * 10
    
    if 'top_width' in dims_cm and 'bottom_width' in dims_cm:
        total_width_mm = ((dims_cm['top_width'] + dims_cm['bottom_width']) / 2) * 10
    elif 'top_width' in dims_cm:
        total_width_mm = dims_cm['top_width'] * 10
    else:
        total_width_mm = 104.4
    
    # Create training-aligned prompt
    aligned_prompt = (
        f"{texture} texture below-knee prosthetic cover. "
        f"Total length: {total_length_mm:.2f} mm. "
        f"Total height: {total_height_mm:.2f} mm. "
        f"Total width: {total_width_mm:.2f} mm."
    )
    
    return aligned_prompt


def process_prompts_file(input_file: str, output_mm: str, output_training: str):
    """
    Process the in_prompts.json file and create two output versions.
    """
    print(f"Reading: {input_file}")
    
    # Load input file
    with open(input_file, 'r', encoding='utf-8') as f:
        prompts = json.load(f)
    
    print(f"Found {len(prompts)} prompts")
    
    # Process each prompt
    prompts_mm = []
    prompts_training = []
    
    cm_count_original = 0
    cm_count_mm_version = 0
    cm_count_training_version = 0
    
    for idx, item in enumerate(prompts, 1):
        uuid = item['uuid']
        original_prompt = item['prompt']
        
        # Count 'cm' in original
        cm_count_original += original_prompt.count(' cm')
        
        # Extract dimensions from original prompt (in cm)
        dims_cm = extract_dimensions_from_prompt(original_prompt)
        
        # Version 1: Simple mm conversion
        prompt_mm = convert_prompt_to_mm(original_prompt)
        cm_count_mm_version += prompt_mm.count(' cm')
        
        # For MM version: keep detailed dimensions in mm
        dimensions_mm = {
            'total_length_mm': dims_cm.get('total_length', 0) * 10,
            'top_width_mm': dims_cm.get('top_width', 0) * 10,
            'bottom_width_mm': dims_cm.get('bottom_width', 0) * 10,
            'channel_depth_mm': dims_cm.get('channel_depth', 0) * 10,
            'wall_thickness_mm': dims_cm.get('wall_thickness', 0) * 10,
            'notch_width_mm': dims_cm.get('notch_width', 0) * 10,
            'notch_depth_mm': dims_cm.get('notch_depth', 0) * 10,
        }
        
        prompts_mm.append({
            'uuid': uuid,
            'prompt': prompt_mm,
            'dimensions': dimensions_mm,
            'prompt_original': original_prompt,
            'format': 'simple_mm'
        })
        
        # Version 2: Training-aligned
        prompt_training = convert_prompt_to_training_format(original_prompt)
        cm_count_training_version += prompt_training.count(' cm')
        
        # For Training version: map to training-style dimensions
        # Calculate the same way as in the prompt
        total_length_mm = dims_cm.get('total_length', 383.1) * 10
        total_height_mm = dims_cm.get('channel_depth', 52.2) * 10
        
        if 'top_width' in dims_cm and 'bottom_width' in dims_cm:
            total_width_mm = ((dims_cm['top_width'] + dims_cm['bottom_width']) / 2) * 10
        elif 'top_width' in dims_cm:
            total_width_mm = dims_cm['top_width'] * 10
        else:
            total_width_mm = 104.4
        
        dimensions_training = {
            'total_length_mm': round(total_length_mm, 2),
            'total_height_mm': round(total_height_mm, 2),
            'total_width_mm': round(total_width_mm, 2),
            # Also include original detailed dimensions for reference
            'original_dimensions': {
                'total_length_mm': dims_cm.get('total_length', 0) * 10,
                'top_width_mm': dims_cm.get('top_width', 0) * 10,
                'bottom_width_mm': dims_cm.get('bottom_width', 0) * 10,
                'channel_depth_mm': dims_cm.get('channel_depth', 0) * 10,
            }
        }
        
        prompts_training.append({
            'uuid': uuid,
            'prompt': prompt_training,
            'dimensions': dimensions_training,
            'prompt_original': original_prompt,
            'format': 'training_aligned'
        })
        
        # Show first 3 examples
        if idx <= 3:
            print(f"\n[{idx}] UUID: {uuid}")
            print(f"  ORIGINAL: {original_prompt[:100]}...")
            print(f"  MM:       {prompt_mm[:100]}...")
            print(f"  MM DIMS:  {dimensions_mm}")
            print(f"  TRAINING: {prompt_training[:100]}...")
            print(f"  TRAIN DIMS: {dimensions_training}")
    
    # Verify conversion
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    print(f"Original prompts: {cm_count_original} occurrences of ' cm'")
    print(f"MM version:       {cm_count_mm_version} occurrences of ' cm'")
    print(f"Training version: {cm_count_training_version} occurrences of ' cm'")
    
    if cm_count_mm_version > 0:
        print(f"\n  WARNING: MM version still has {cm_count_mm_version} 'cm' - should be 0!")
        print("Checking which prompts have issues...")
        for item in prompts_mm:
            if ' cm' in item['prompt']:
                print(f"  - UUID {item['uuid']}: {item['prompt'].count(' cm')} 'cm' found")
    else:
        print(f"✅ MM version: All 'cm' converted to 'mm'!")
    
    if cm_count_training_version > 0:
        print(f"\n  WARNING: Training version still has {cm_count_training_version} 'cm' - should be 0!")
    else:
        print(f"✅ Training version: All 'cm' converted to 'mm'!")
    
    # Save Version 1: Simple MM
    with open(output_mm, 'w', encoding='utf-8') as f:
        json.dump(prompts_mm, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved MM version to: {output_mm}")
    
    # Save Version 2: Training-aligned
    with open(output_training, 'w', encoding='utf-8') as f:
        json.dump(prompts_training, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved training-aligned version to: {output_training}")
    
    # Print statistics
    print("\n" + "=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Processed: {len(prompts)} prompts")
    print(f"\nVersion 1 (SIMPLE_MM):")
    print(f"  - Keeps all original detail")
    print(f"  - Just converts cm → mm (XX.XX format)")
    print(f"  - Includes: total_length, top_width, bottom_width, channel_depth, etc.")
    print(f"  - Example: 'top internal width 112.50 mm'")
    print(f"\nVersion 2 (TRAINING_ALIGNED):")
    print(f"  - Matches training data format")
    print(f"  - Uses 'Total length/height/width'")
    print(f"  - Includes: total_length, total_height, total_width + original dimensions")
    print(f"  - Example: 'Total length: 432.20 mm. Total height: 56.20 mm. Total width: 91.50 mm.'")
    print("=" * 80)


if __name__ == "__main__":
    # File paths
    INPUT_FILE = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/input_prompts.json"
    OUTPUT_MM = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/in_prompts_MM_fix.json"
    OUTPUT_TRAINING = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/in_prompts_TRAINING_ALIGNED.json"
    
    
    print("=" * 80)
    print("CONVERTING in_prompts.json TO MM FORMAT")
    print("=" * 80)
    print()
    print("Creating 2 versions:")
    print("  1. in_prompts_MM.json - Simple mm conversion (detailed)")
    print("  2. in_prompts_TRAINING_ALIGNED.json - Training format (Total length/height/width)")
    print()
    print("Both versions use XX.XX format (2 decimal places)")
    print()
    
    # Process the file
    process_prompts_file(INPUT_FILE, OUTPUT_MM, OUTPUT_TRAINING)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print(f"1. Use '{OUTPUT_TRAINING}' for batch generation (RECOMMENDED)")
    print(f"2. Or try '{OUTPUT_MM}' if you want to test detailed prompts")
    print(f"3. Update your batch generation script to use the new prompt file")
    print("=" * 80)
