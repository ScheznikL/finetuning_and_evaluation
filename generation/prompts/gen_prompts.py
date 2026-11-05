import math
import os
import sys
import time
import uuid
import json
import random
import logging
import torch
import numpy as np
from PIL import Image
from diffusers import AutoPipelineForText2Image
from design_templates import size_chart, design_templates


def generate_random_measurements(size_key):
    """
    Generates realistic measurements based on the provided size chart.
    Calculates Width (Diameter) from Circumference (Circ / Pi).
    """
    data = size_chart[size_key]
    
    # Randomize core dimensions based on chart
    length = random.uniform(data['length'][0], data['length'][1])
    ankle_c = random.uniform(data['ankle_circ'][0], data['ankle_circ'][1])
    calf_c = random.uniform(data['calf_circ'][0], data['calf_circ'][1])
    
    # Calculate widths (Diameter = Circumference / Pi)
    # We add a small buffer or round appropriately
    top_width = calf_c / math.pi
    bottom_width = ankle_c / math.pi
    
    # Channel depth is roughly half the width (radius) for a U-shape
    channel_depth = top_width / 2.0
    
    # Constants/Small variance items
    wall_thickness = random.uniform(0.3, 0.5) # Standard 3D print wall
    top_notch_width = random.uniform(4.0, 6.0) # Standard knee notch width
    top_notch_depth = random.uniform(2.0, 3.5) # Standard knee notch depth

    return {
        "TOTAL_LENGTH": round(length, 2),
        "TOP_WIDTH": round(top_width, 2),
        "BOTTOM_WIDTH": round(bottom_width, 2),
        "CHANNEL_DEPTH": round(channel_depth, 2),
        "WALL_THICKNESS": round(wall_thickness, 2),
        "TOP_NOTCH_WIDTH": round(top_notch_width, 2),
        "TOP_NOTCH_DEPTH": round(top_notch_depth, 2)
    }

def gen_and_save_prompts():
    prompt_data = []

    # Ensure we don't exceed the list length if it's less than 100
    limit = min(100, len(design_templates))
    
    for i in range(limit):
        # 1. Generate a unique ID for this specific prompt
        unique_id = str(uuid.uuid4())

        # 2. Pick a random size
        size_selection = random.choice(['S', 'M', 'L'])
        
        # 3. Get measurements
        dims = generate_random_measurements(size_selection)
        
        # 4. Construct the prompt string
        # Using design_templates[i] ensures every prompt is unique
        prompt_text = (
            f'CAPTION = f"{design_templates[i]} Ergonomic semi-cylindrical U-shaped open channel.'
            f'    Total length: {dims["TOTAL_LENGTH"]} cm. Tapering U-channel: top internal width {dims["TOP_WIDTH"]} cm, '
            f'bottom internal width {dims["BOTTOM_WIDTH"]} cm,'
            f'    channel depth {dims["CHANNEL_DEPTH"]} cm, wall thickness is {dims["WALL_THICKNESS"]} cm. '
            f'Centered rectangular top notch: {dims["TOP_NOTCH_WIDTH"]} cm wide, {dims["TOP_NOTCH_DEPTH"]} cm deep."'
        )
        
        # 5. Append to list as a dictionary
        prompt_data.append({
            "uuid": unique_id,
            "prompt": prompt_text
        })

    # 6. Save to JSON file
    output_file = 'input_prompts.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(prompt_data, f, indent=4)
    
    print(f"Successfully generated {len(prompt_data)} prompts and saved to '{output_file}'")

if __name__ == "__main__":
    gen_and_save_prompts()

# def gen_prompt():
#     prompts = []

#     for i in range(100):
#         # 1. Pick a random size (S, M, or L) to keep proportions realistic
#         size_selection = random.choice(['S', 'M', 'L'])
#         # 2. Get the specific measurements for this instance
#         dims = generate_random_measurements(size_selection)
#         # 3. Pick a random design description (Material/Style)
#         design_intro = random.choice(design_templates)
#         # 4. Construct the prompt string
#         # Note: We ensure the "sentence before first \" changes, and the measurements follow your exact template.
#         prompt = (
#             f'CAPTION = f"{design_templates[i]} Ergonomic semi-cylindrical U-shaped open channel.\\ \n'
#             f'    Total length: {dims["TOTAL_LENGTH"]} cm. Tapering U-channel: top internal width {dims["TOP_WIDTH"]} cm, '
#             f'bottom internal width {dims["BOTTOM_WIDTH"]} cm,\\ \n'
#             f'    channel depth {dims["CHANNEL_DEPTH"]} cm, wall thickness is {dims["WALL_THICKNESS"]} cm. '
#             f'Centered rectangular top notch: {dims["TOP_NOTCH_WIDTH"]} cm wide, {dims["TOP_NOTCH_DEPTH"]} cm deep."'
#         )
        
#         prompts.append(prompt)