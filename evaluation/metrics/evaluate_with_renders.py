import argparse
import os
import json
import subprocess
import zipfile
import numpy as np
from clip_sim import cal_clip_sim_text
from bse import calculate_ber 

BLENDER = os.environ.get('BLENDER', 'blender')  # Blender 4.2.1



def get_compressed_prompt_from_file(uuid: str, file_path: str) -> str:
                       
    with open(file_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        for item in meta:
            if item['uuid'] == uuid:
                return item['prompt']
    raise KeyError(f"No prompt found in {file_path}")
    
def get_compressed_prompt_by_id(uuid: str, model_dir: str, zip_dir = None) -> str:
    meta_path = os.path.join(model_dir, f"{uuid}_compressed_meta.json")

    if zip_dir is not None:
        # json_data_list = load_json_from_zip_for_clip(zip_dir)
        # print(f"Found {len(json_data_list)} test prompts")
        
        # for idx, (json_filename, data) in enumerate(json_data_list, 1):
        #     if json_filename.endswith("_compressed_meta.json") and data.get("uuid") == uuid:
        #         pr = data.get('prompt_clip') 
        #         print(f"[INFO] Got the prompt {pr}")
        return get_prompt_by_id_fast(zip_path=zip_dir, uuid=uuid)
                # return pr
    else:                      
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        return meta["prompt_clip"]

def get_prompt_by_id_fast(zip_path, uuid):
    target_suffix = f"{uuid}_compressed_meta.json"
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for full_path in zip_ref.namelist():
            if os.path.basename(full_path) == target_suffix:
                with zip_ref.open(full_path) as f:
                    data = json.load(f)
                    return data.get('prompt_clip')
    
    return None

def load_json_from_zip_for_clip(zip_path):
    """
    Load all JSON files from zip without extracting.
    Returns list of (filename, json_data) tuples.
    """
    json_data_list = []
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get all JSON files in the zip
        json_files = [f for f in zip_ref.namelist() 
                     if f.endswith('_compressed_meta.json')] # HERE COMPRESSED
        
        for json_file in sorted(json_files):
            # Read JSON directly from zip
            with zip_ref.open(json_file) as f:
                data = json.load(f)
                json_data_list.append((json_file, data))
    
    return json_data_list

def render_views(glb_path, out_dir):
    # cmd = [
    #     BLENDER, "-b", "-P", "render_two_views.py",
    #     "--object", glb_path, out_dir
    # ]
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_two_views.py')
    cmd = [
    BLENDER,
    '-b',
    '-P', script_path,
    '--',
    '--object', glb_path,
    '--output_folder', out_dir,
    '--resolution', '512'  # optional
    ]
    subprocess.run(cmd, check=True)

def evaluate(models_dir, batch_name, 
             base_dir, out_dir = './', 
             clip_prompts_dir = None,
             clip_zip = None,
             do_clip = True,
             do_bse = True):
    
    clip_scores = []
    ber_scores = []
    times = []
    t2i_times= []
    is_watertight_count = 0

    metas = [f for f in os.listdir(models_dir) if f.endswith("_meta.json") or f.endswith(".json") and not f.endswith("_compressed_meta.json") ]
    
    print(f"[INFO] Metas: {metas}")

    for meta_file in metas:
        uuid = meta_file.replace("_meta.json", "")
        uuid = uuid.replace(".json", "")
        
        meta_path = os.path.join(models_dir, meta_file)
        glb_path = os.path.join(models_dir, f"{uuid}.glb")

        img_tmp= os.path.join(base_dir, "_renders")
        render_dir = os.path.join(img_tmp, uuid)
        os.makedirs(render_dir, exist_ok=True)

        # -------- render --------      

        imgs = [
            os.path.join(render_dir, "front.png"),
            os.path.join(render_dir, "side.png")
        ]
        # Check if all files in the list exist
        if all(os.path.exists(img) for img in imgs):
            print("Renders already exist. Skipping...")
        else:
            render_views(glb_path, render_dir)

        # -------- meta --------
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        print(meta)
        prompt = meta["prompt"]
        metrics = meta["metrics"]
        time_t2i = 0 if metrics.get("time_t2i", 0) == "0" else  metrics.get("time_t2i", 0) # optional
        
        times.append(time_t2i + metrics["time_shape"])
        t2i_times.append(time_t2i)
        
        # -------- CLIP --------
        if do_clip:
                
            if clip_prompts_dir is not None:
                prompt = get_compressed_prompt_from_file(uuid, file_path=clip_prompts_dir)
            else:
                prompt = get_compressed_prompt_by_id(uuid=uuid, model_dir=models_dir,
                                                    zip_dir=clip_zip)
            print(f"[INFO] prompt: {prompt}")
            if prompt is None:
                print('[ERROR] the prompt is NONE !!!')
                raise KeyError
            clip_score = cal_clip_sim_text(prompt, imgs)
            clip_scores.append(clip_score)
        else:
            clip_score.append(1)
            
        # -------- BER --------
        if do_bse:                
            ber = calculate_ber(glb_path)
            if ber['is_watertight']:
                is_watertight_count+=1

            if ber is not None:
                ber_scores.append(ber['BER'])
            #stats = check_watertightness_blender(glb_path, BLENDER) TODO
        else:
            ber_scores.append(1)
        
        print("[INFO] Using NO CLIP and NO BSE") if not do_clip and not do_bse else print("Calculation is complete")
        print(f"{uuid}: CLIP={clip_score:.4f}, BER={ber['BER']:.8f}, is_watertight = {ber['is_watertight']} ")
        
    result_json = {
    "total_cases": len(ber_scores),
    "avg_score_CLIP": float(np.mean(clip_scores)),
    "max_score_CLIP": float(np.max(clip_scores)),
    "min_score_CLIP": float(np.min(clip_scores)),
    "avg_score_BSE": float(np.mean(ber_scores)),
    "max_score_BSE": float(np.max(ber_scores)),
    "min_score_BSE": float(np.min(ber_scores)),
    "is_watertight_count": is_watertight_count,
    "avg_time_in_sec": float(np.mean(times)),
    "max_time_in_sec": float(np.max(times)),
    "min_time_in_sec": float(np.min(times)),
    "avr_t2i_time" : float(np.mean(t2i_times)),
    }
    
    final_json_path = out_dir
    with open(final_json_path, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=4, ensure_ascii=False)
        
    
    return result_json


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models_dir", required=True, type=str,)
    parser.add_argument("--output_metrics", required=True, type=str) 
    parser.add_argument("--base_dir", type=str) 
    parser.add_argument("--batch_name", required=True, type=str) 
    parser.add_argument("--clip_prompts_dir", type=str, default=None)
    parser.add_argument("--clip_zip", type=str, default=None,
                        help="zip with *_compressed_meta.json, used when --clip_prompts_dir is not given")
    parser.add_argument("--do_clip", type=bool, default=False)
    parser.add_argument("--do_bse", type=bool, default=True)
    return parser.parse_args()
    

if __name__ == "__main__":
    
    args = get_args()
    
    print(json.dumps(evaluate(models_dir=args.models_dir, batch_name = args.batch_name, 
                              out_dir=args.output_metrics,
                              clip_prompts_dir= args.clip_prompts_dir,
                              clip_zip = args.clip_zip,
                              base_dir = args.base_dir,
                              do_clip = args.do_clip,
                              do_bse = args.do_bse),
                     indent=4))