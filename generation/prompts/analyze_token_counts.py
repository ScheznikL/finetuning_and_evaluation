import json
import re
from transformers import CLIPTokenizer


def count_tokens(text: str, tokenizer) -> int:
    """Count tokens in text using CLIP tokenizer."""
    tokens = tokenizer(text, truncation=False, add_special_tokens=True)
    return len(tokens['input_ids'])


def shorten_prompt_v1(prompt: str) -> str:
    """
    Version 1: Remove redundant words like "Create only one" and "Total"
    Keep all numerical specifications.
    """
    new_prompt = prompt
    
    # Remove "Create only one "
    new_prompt = re.sub(r'^Create only one\s+', '', new_prompt, flags=re.IGNORECASE)
    
    # Remove "Total" before measurements
    new_prompt = re.sub(r'\bTotal\s+', '', new_prompt, flags=re.IGNORECASE)
    
    return new_prompt.strip()


def shorten_prompt_v2(prompt: str) -> str:
    """
    Version 2: Remove redundant words AND simplify descriptions.
    Keep all numerical specifications.
    """
    new_prompt = prompt
    
    # Remove "Create only one "
    new_prompt = re.sub(r'^Create only one\s+', '', new_prompt, flags=re.IGNORECASE)
    
    # Remove verbose phrases
    new_prompt = new_prompt.replace('in a form of shell the style restores natural limb silhouette. ', '')
    new_prompt = new_prompt.replace('the style restores natural limb silhouette. ', '')
    
    # Remove "Total" before measurements
    new_prompt = re.sub(r'\bTotal\s+', '', new_prompt, flags=re.IGNORECASE)
    
    # Simplify "Tapering U-channel:" to just the measurements
    new_prompt = new_prompt.replace('Tapering U-channel: ', '')
    
    # Simplify "Centered rectangular top notch:" to just "Top notch:"
    new_prompt = new_prompt.replace('Centered rectangular top notch:', 'Top notch:')
    
    return new_prompt.strip()


def shorten_prompt_v3(prompt: str) -> str:
    """
    Version 3: Remove numerical details if CLIP doesn't understand them anyway.
    Keep only material, shape type, and structural descriptions.
    """
    new_prompt = prompt
    
    # Remove "Create only one "
    new_prompt = re.sub(r'^Create only one\s+', '', new_prompt, flags=re.IGNORECASE)
    
    # Extract just the material and basic description
    # Example: "Matte White PLA below-knee prosthetic cover"
    match = re.search(r'^([^.]+?below-knee prosthetic cover)', new_prompt, re.IGNORECASE)
    if match:
        base = match.group(1)
        
        # Add shape description if present
        shape_match = re.search(r'(Ergonomic semi-cylindrical U-shaped open channel)', new_prompt, re.IGNORECASE)
        if shape_match:
            new_prompt = f"{base}. {shape_match.group(1)}."
        else:
            new_prompt = f"{base}."
    
    return new_prompt.strip()


def shorten_prompt_aggressive(prompt: str, tokenizer=None, max_tokens: int = 77) -> str:
    """
    Version 4: Iteratively remove sentences from the end until under token limit.
    Keeps "Create only one" if tokens allow, removes less important sentences first.
    Priority: Keep material/type description > shape > measurements (chop from end).
    """
    if tokenizer is None:
        # If no tokenizer provided, just do basic shortening
        match = re.search(r'^Create only one ([^.]+?below-knee prosthetic cover)', prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip() + "."
        return prompt
    
    # First try with everything (including "Create only one")
    current_prompt = prompt
    token_count = count_tokens(current_prompt, tokenizer)
    
    if token_count <= max_tokens:
        return current_prompt
    
    # Split into sentences (split on '. ')
    sentences = [s.strip() for s in prompt.split('. ') if s.strip()]
    
    # Iteratively remove sentences from the end
    while len(sentences) > 1:
        sentences = sentences[:-1]  # Remove last sentence
        current_prompt = '. '.join(sentences)
        # Add period at the end if not already there
        if not current_prompt.endswith('.'):
            current_prompt += '.'
        
        token_count = count_tokens(current_prompt, tokenizer)
        
        if token_count <= max_tokens:
            return current_prompt
    
    # If we're down to one sentence and it's still too long, try removing "Create only one"
    if sentences:
        first_sentence = sentences[0]
        # Try without "Create only one"
        without_create = re.sub(r'^Create only one\s+', '', first_sentence, flags=re.IGNORECASE)
        if not without_create.endswith('.'):
            without_create += '.'
        
        token_count = count_tokens(without_create, tokenizer)
        if token_count <= max_tokens:
            return without_create
        
        # Still too long? Return it anyway, it's the best we can do
        return without_create
    
    # Fallback (shouldn't reach here)
    return current_prompt


def analyze_prompts(input_file: str, model_name: str = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"):
    """
    Analyze token counts for all prompts and their shortened versions.
    """
    print(f"Loading CLIP tokenizer from: {model_name}")
    tokenizer = CLIPTokenizer.from_pretrained(model_name)
    print(f"✅ Loaded tokenizer")
    print(f"Max tokens: 77 (CLIP limit)\n")
    
    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} prompts\n")
    
    # Analyze all prompts
    stats = {
        'original': [],
        'v1_remove_redundant': [],
        'v2_simplify_desc': [],
        'v3_remove_numbers': [],
        'v4_ultra_short': []
    }
    
    over_limit_count = {
        'original': 0,
        'v1_remove_redundant': 0,
        'v2_simplify_desc': 0,
        'v3_remove_numbers': 0,
        'v4_ultra_short': 0
    }
    
    print("=" * 100)
    print("ANALYZING FIRST 3 PROMPTS")
    print("=" * 100)
    
    for idx, item in enumerate(data, 1):
        prompt = item['prompt']
        
        # Count tokens for all versions
        tokens_original = count_tokens(prompt, tokenizer)
        tokens_v1 = count_tokens(shorten_prompt_v1(prompt), tokenizer)
        tokens_v2 = count_tokens(shorten_prompt_v2(prompt), tokenizer)
        tokens_v3 = count_tokens(shorten_prompt_v3(prompt), tokenizer)
        tokens_v4 = count_tokens(shorten_prompt_aggressive(prompt, tokenizer), tokenizer)
        
        # Store stats
        stats['original'].append(tokens_original)
        stats['v1_remove_redundant'].append(tokens_v1)
        stats['v2_simplify_desc'].append(tokens_v2)
        stats['v3_remove_numbers'].append(tokens_v3)
        stats['v4_ultra_short'].append(tokens_v4)
        
        # Count over-limit
        if tokens_original > 77: over_limit_count['original'] += 1
        if tokens_v1 > 77: over_limit_count['v1_remove_redundant'] += 1
        if tokens_v2 > 77: over_limit_count['v2_simplify_desc'] += 1
        if tokens_v3 > 77: over_limit_count['v3_remove_numbers'] += 1
        if tokens_v4 > 77: over_limit_count['v4_ultra_short'] += 1
        
        # Show first 3 examples
        if idx <= 3:
            print(f"\n[{idx}] UUID: {item['uuid']}")
            print(f"\nORIGINAL ({tokens_original} tokens):")
            print(f"  {prompt[:150]}...")
            
            v1 = shorten_prompt_v1(prompt)
            print(f"\nV1: Remove redundant ({tokens_v1} tokens, saved {tokens_original - tokens_v1}):")
            print(f"  {v1[:150]}...")
            
            v2 = shorten_prompt_v2(prompt)
            print(f"\nV2: Simplify descriptions ({tokens_v2} tokens, saved {tokens_original - tokens_v2}):")
            print(f"  {v2[:150]}...")
            
            v3 = shorten_prompt_v3(prompt)
            print(f"\nV3: Remove numbers ({tokens_v3} tokens, saved {tokens_original - tokens_v3}):")
            print(f"  {v3[:150]}...")
            
            v4 = shorten_prompt_aggressive(prompt, tokenizer)
            print(f"\nV4: Chop sentences ({tokens_v4} tokens, saved {tokens_original - tokens_v4}):")
            print(f"  {v4[:150]}...")
            print("\n" + "-" * 100)
    
    # Print overall statistics
    print("\n" + "=" * 100)
    print("OVERALL STATISTICS")
    print("=" * 100)
    
    for version, tokens_list in stats.items():
        avg = sum(tokens_list) / len(tokens_list)
        max_tokens = max(tokens_list)
        min_tokens = min(tokens_list)
        over_limit = over_limit_count[version]
        
        print(f"\n{version.upper().replace('_', ' ')}:")
        print(f"  Average tokens: {avg:.1f}")
        print(f"  Range: {min_tokens} - {max_tokens}")
        print(f"  Over limit (>77): {over_limit}/{len(tokens_list)} prompts")
        
        if over_limit == 0:
            print(f"  ✅ ALL prompts fit within 77 token limit!")
        else:
            print(f"  ❌ {over_limit} prompts exceed limit")
    
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)
    
    # Find the shortest version that fits all prompts
    if over_limit_count['v1_remove_redundant'] == 0:
        print("✅ Use V1 (Remove redundant words)")
        print("   - Removes 'Create only one' and 'Total'")
        print("   - Keeps all numerical specifications")
        print("   - Minimal changes, all prompts fit")
    elif over_limit_count['v2_simplify_desc'] == 0:
        print("✅ Use V2 (Simplify descriptions)")
        print("   - Removes verbose phrases")
        print("   - Keeps all numerical specifications")
        print("   - More aggressive trimming")
    elif over_limit_count['v3_remove_numbers'] == 0:
        print("✅ Use V3 (Remove numbers)")
        print("   - Keeps only material and shape type")
        print("   - Removes all measurements")
        print("   - Test if CLIP even uses numbers")
    elif over_limit_count['v4_ultra_short'] == 0:
        print("✅ Use V4 (Chop sentences)")
        print("   - Automatically removes sentences from end until it fits")
        print("   - Keeps as much detail as possible within 77 tokens")
        print("   - Guaranteed to fit!")
    else:
        print("⚠️  All versions have some prompts over limit!")
        print("   This should not happen with V4 - check your prompts")
    
    return stats, over_limit_count


def create_shortened_prompts(input_file: str, output_file: str, version: str = 'v1', 
                             model_name: str = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"):
    """
    Create a new JSON file with shortened prompts.
    
    Args:
        input_file: Input JSON file path
        output_file: Output JSON file path
        version: 'v1', 'v2', 'v3', or 'v4'
        model_name: CLIP model name for tokenizer
    """
    print(f"\nCreating shortened prompts (version: {version})...")
    
    tokenizer = CLIPTokenizer.from_pretrained(model_name)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    shortened_data = []
    
    for item in data:
        original_prompt = item['prompt']
        
        # Apply shortening based on version
        if version == 'v1':
            new_prompt = shorten_prompt_v1(original_prompt)
        elif version == 'v2':
            new_prompt = shorten_prompt_v2(original_prompt)
        elif version == 'v3':
            new_prompt = shorten_prompt_v3(original_prompt)
        elif version == 'v4':
            new_prompt = shorten_prompt_aggressive(original_prompt, tokenizer)
        else:
            raise ValueError(f"Unknown version: {version}")
        
        token_count = count_tokens(new_prompt, tokenizer)
        
        # Copy all existing fields and update prompt
        new_item = item.copy()
        new_item['prompt'] = new_prompt
        new_item['prompt_original'] = original_prompt
        new_item['token_count'] = token_count
        new_item['shortening_version'] = version
        
        shortened_data.append(new_item)
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(shortened_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved to: {output_file}")
    print(f"   Processed {len(shortened_data)} prompts")


if __name__ == "__main__":
    
    
    prompts_path = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/in_prompts_MM.json"
        
    INPUT_FILE = prompts_path
    MODEL_NAME = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"  
    

    print(f"Input file: {INPUT_FILE}")
    print(f"CLIP model: {MODEL_NAME}")
    print()
    
    # Analyze
    stats, over_limit = analyze_prompts(INPUT_FILE, model_name=MODEL_NAME)
    
    # Create shortened versions if needed
    print("\n" + "=" * 100)
    print("CREATING SHORTENED FILES")
    print("=" * 100)
    
    # Always create V1 (safest option that keeps numbers)
    if over_limit['v1_remove_redundant'] == 0:
        create_shortened_prompts(INPUT_FILE, "in_prompts_MM_SHORT.json", version='v1', model_name=MODEL_NAME)
        print("\n✅ RECOMMENDED: Use in_prompts_MM_SHORT.json (V1 shortening)")
    elif over_limit['v2_simplify_desc'] == 0:
        create_shortened_prompts(INPUT_FILE, "in_prompts_MM_SHORT.json", version='v2', model_name=MODEL_NAME)
        print("\n✅ RECOMMENDED: Use in_prompts_MM_SHORT.json (V2 shortening)")
    elif over_limit['v3_remove_numbers'] == 0:
        create_shortened_prompts(INPUT_FILE, "in_prompts_MM_SHORT.json", version='v3', model_name=MODEL_NAME)
        print("\n Using V3 (no numbers) - test if this works for your model")
    else:
        # V4 should always work as it chops sentences until it fits
        create_shortened_prompts(INPUT_FILE, "in_prompts_MM_SHORT.json", version='v4', model_name=MODEL_NAME)
        print("\n✅ Using V4 (chop sentences) - guaranteed to fit!")
    
    # Also create V3 for comparison (to test if numbers matter)
    create_shortened_prompts(INPUT_FILE, "in_prompts_MM_NO_NUMBERS.json", version='v3', model_name=MODEL_NAME)
    
    # And create V4 for maximum compatibility
    create_shortened_prompts(INPUT_FILE, "in_prompts_MM_AUTO_CHOPPED.json", version='v4', model_name=MODEL_NAME)
    
    print("\n💡 EXPERIMENT: Compare results from:")
    print("   1. in_prompts_MM_SHORT.json (recommended version)")
    print("   2. in_prompts_MM_NO_NUMBERS.json (no measurements - test if CLIP uses them)")
    print("   3. in_prompts_MM_AUTO_CHOPPED.json (auto-truncated - guaranteed to fit)")
    print("   to see if CLIP even uses the numerical specifications!")
