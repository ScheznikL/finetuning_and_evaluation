import os
import sys
import json
import re

# usage: python rewrite_prompts_clip.py <batch_dir>   (reads <batch_dir>/100_test_models/*_meta.json)
BASE_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
MODEL_DIR = os.path.join(BASE_DIR, "100_test_models")

# -------------------------
# Regex helpers
# -------------------------

def find_float(text, key):
    m = re.search(rf"{key}[^0-9]*([\d.]+)", text, re.IGNORECASE)
    return m.group(1) if m else None

def find_pair(text, key):
    m = re.search(rf"{key}[^0-9]*([\d.]+)[^\d]+([\d.]+)", text, re.IGNORECASE)
    return (m.group(1), m.group(2)) if m else (None, None)

# -------------------------
# Prompt compression
# -------------------------

def compress_prompt(original: str) -> str:
    p = original.lower()

    # ---- material / finish ----
    material = "plastic"
    if "chrome" in p:
        material = "chrome finish"
    elif "matte white" in p:
        material = "matte white"
    elif "pla" in p:
        material = "PLA"

    # ---- geometry ----
    L  = find_float(p, "total length")
    WT = find_float(p, "top internal width")
    WB = find_float(p, "bottom internal width")
    D  = find_float(p, "channel depth")
    T  = find_float(p, "wall thickness")

    NW, ND = find_pair(p, "notch")

    parts = [
        "below-knee prosthetic cover",
        "U-shaped shell",
        material
    ]

    if L:
        parts.append(f"length {L}cm")
    if WT and WB:
        parts.append(f"top width {WT}cm")
        parts.append(f"bottom width {WB}cm")
    if D:
        parts.append(f"depth {D}cm")
    if T:
        parts.append(f"wall {T}cm")
    if NW and ND:
        parts.append(f"rect notch {NW}x{ND}cm")

    return ", ".join(parts)

# -------------------------
# Batch rewrite (SEPARATE FILE)
# -------------------------

def rewrite_all():
    metas = [f for f in os.listdir(MODEL_DIR) if f.endswith("_meta.json")]

    for meta_file in metas:
        uuid = meta_file.replace("_meta.json", "")

        src_path = os.path.join(MODEL_DIR, meta_file)
        dst_path = os.path.join(MODEL_DIR, f"{uuid}_compressed_meta.json")

        if os.path.exists(dst_path):
            continue  # already created

        with open(src_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        compressed_prompt = compress_prompt(meta["prompt"])

        compressed_meta = {
            "uuid": uuid,
            "prompt_clip": compressed_prompt
        }

        with open(dst_path, "w", encoding="utf-8") as f:
            json.dump(compressed_meta, f, indent=4)

        print(f"[OK] {uuid}")

    print("DONE.")

# -------------------------
# Entry
# -------------------------

if __name__ == "__main__":
    rewrite_all()
