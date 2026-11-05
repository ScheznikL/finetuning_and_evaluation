#TRY_INX = "_alpha_0_9"
TRY_INX = ""
SEED = 1111
CAPTION_demo = "Create a lower limb prosthesis cover with a height of 0.5m"
#CAPTION = ""
PRIOR_PATH = "/dcs/large/u5745134/dataset/raw/3dmodels/coverC_to_obj_pipe.obj"

import sys
import time
from venv import logger

import diffusers
import torch
sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')

from PIL import Image
from hy3dshape.rembg import BackgroundRemover
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline, Hunyuan3DDiTFlowMatchingPipelineWithPriorInitialization
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
from cover_caption import CAPTION, CAPTION_ankle

def gen_from_text_with_prior(prompt, prior_path, pipeline, export_path = "demo_path_of_model.glb", seed = 1002):
    from hy3dshape.pipelines import export_to_trimesh

    time_meta = {}

    if prompt: print('prompt is', prompt)
    else: 
        print(f"prompt empty") 
        return    

    image_path = './rembg_CAPTION_ankle.png'
    if not check_file_exists(image_path):
        t2i_worker = HunyuanDiTPipeline('Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled')
        start_time = time.time()
        try:
            image = t2i_worker(prompt, seed=SEED)
        except Exception as e:
            print(e)
            return    
        time_meta['text2image'] = time.time() - start_time

        #image.save(f'{image_path}')
    else:
        image = Image.open(image_path).convert("RGB")

    if image.mode == "RGB":
        start_time = time.time()
        rembg = BackgroundRemover()
        image = rembg(image)
        #image = BackgroundRemover(image = image.convert('RGB'))
        time_meta['remove background'] = time.time() - start_time

    image.save(image_path)

    # remove disk io to make responding faster, uncomment at your will.
    # image.save(os.path.join(save_folder, 'rembg.png'))

    # image to white model
    start_time = time.time()

    generator = torch.Generator() # for rand nums
    generator = generator.manual_seed(int(seed))
    alpha = [0.1, 0.4, 0.7, 1]
    for i in alpha:
        outputs = pipeline(
            image=image,
            prior = prior_path,
            alpha = i,
            #num_inference_steps=steps,
            #guidance_scale=guidance_scale,
            generator=generator,
            #octree_resolution=octree_resolution,
            #num_chunks=num_chunks,
            output_type='mesh',
            debug_img_dir = "./out/debugimg"
        )
        time_meta['shape generation'] = time.time() - start_time
        logger.info("---Shape generation takes %s seconds ---" % (time.time() - start_time))
        print("[PRINT INFO]---Shape generation takes %s seconds ---" % (time.time() - start_time))

        tmp_start = time.time()
        mesh = export_to_trimesh(outputs)[0]
        time_meta['export to trimesh'] = time.time() - tmp_start

        val_str = f"{i:.1f}".replace(".", "_")

        export_path = prepare_output_dir(export_path, val_str)
        mesh.export(export_path)

def prepare_output_dir(file_path, val_str = None):
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"Created - {directory}")
    if val_str:
        name, ext = os.path.splitext(filename)
        new_filename = f"{val_str}_{name}{ext}"
        return os.path.join(directory, new_filename)
    return file_path

def check_file_exists(file_path):
    if os.path.exists(file_path):
        print(f"File already exists: {file_path}")
        return True
    else:
        print(f"File does not exist: {file_path}")
        return False
    
###
# ----------------- CLASS
import os
import random

import numpy as np
import torch
from diffusers import AutoPipelineForText2Image
#from diffusers import DiffusionPipeline
def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    os.environ["PL_GLOBAL_SEED"] = str(seed)
    return str(seed)

class HunyuanDiTPipeline:
    def __init__(
        self,
        model_path="Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled",
        device='cuda'
    ):
        self.device = device
        self.pipe = AutoPipelineForText2Image.from_pretrained(
           model_path,
           torch_dtype=torch.float16,
           enable_pag=True,
           pag_applied_layers=["blocks.(16|17|18|19)"]
        ).to(device)
        self.seed_toprint = "0"
        #self.pipe = DiffusionPipeline.from_pretrained(model_path, dtype=torch.bfloat16, device_map="cuda", enable_pag=True)

        self.pos_txt = ",白色背景,3D风格,最佳质量"
        self.neg_txt = "文本,特写,裁剪,出框,最差质量,低质量,JPEG伪影,PGLY,重复,病态," \
                       "残缺,多余的手指,变异的手,画得不好的手,画得不好的脸,变异,畸形,模糊,脱水,糟糕的解剖学," \
                       "糟糕的比例,多余的肢体,克隆的脸,毁容,恶心的比例,畸形的肢体,缺失的手臂,缺失的腿," \
                       "额外的手臂,额外的腿,融合的手指,手指太多,长脖子"

    def compile(self):
        # accelarate hunyuan-dit transformer,first inference will cost long time
        torch.set_float32_matmul_precision('high')
        self.pipe.transformer = torch.compile(self.pipe.transformer, fullgraph=True)
        # self.pipe.vae.decode = torch.compile(self.pipe.vae.decode, fullgraph=True)
        generator = torch.Generator(device=self.pipe.device)  # infer once for hot-start
        out_img = self.pipe(
            prompt='美少女战士',
            negative_prompt='模糊',
            num_inference_steps=25,
            pag_scale=1.3,
            width=1024,
            height=1024,
            generator=generator,
            return_dict=False
        )[0][0]

    @torch.no_grad()
    def __call__(self, prompt, seed=0):
        self.seed_toprint = seed_everything(seed)
        generator = torch.Generator(device=self.pipe.device)
        generator = generator.manual_seed(int(seed))
        out_img = self.pipe(
            prompt=prompt[:60] + self.pos_txt,
            negative_prompt=self.neg_txt,
            num_inference_steps=25,
            pag_scale=1.3,
            width=1024,
            height=1024,
            generator=generator,
            return_dict=False
        )[0][0]
        return out_img
### -------------------------------END------------------------------------------------------------   
  
if __name__ == '__main__':    
    try:
        from torchvision_fix import apply_fix
        apply_fix()
    except ImportError:
        print("Warning: torchvision_fix module not found, proceeding without compatibility fix")                                      
    except Exception as e:
        print(f"Warning: Failed to apply torchvision fix: {e}")

    # shape
    default_subfolder='hunyuan3d-dit-v2-mini'
    model_path = 'tencent/Hunyuan3D-2mini' #'tencent/Hunyuan3D-2.1'

    pipeline_shapegen = Hunyuan3DDiTFlowMatchingPipelineWithPriorInitialization.from_pretrained(
        model_path,
        subfolder = default_subfolder,
        )

    #demo_prompt = "A cylindrical wooden cup with an outer height of 0.12 meters and an outer diameter of 0.08 meters."
    
    #prepare file_name
    CAPTION = CAPTION_ankle
    obj_descr_begin, obj_descr_end = CAPTION[:len(CAPTION)//2], CAPTION[len(CAPTION)//2:]
    obj_descr_begin = obj_descr_begin.replace(" ", "_").replace(".","_")
    gen_from_text_with_prior(CAPTION_ankle, prior_path = PRIOR_PATH, pipeline = pipeline_shapegen, seed=SEED, export_path=f"./out/objects/{TRY_INX}{obj_descr_begin}.glb")

### A rectangular wooden table with a tabletop measuring 1.2 meters in length, 
# 0.8 meters in width, and 0.04 meters in thickness. The table stands 0.75 meters tall /
# and is supported by four straight cylindrical legs, each with a diameter of 0.06 meters, /
# positioned exactly at the four corners of the tabletop./
#  The legs extend vertically and connect directly to the underside of the tabletop without additional braces. The surface is flat, smooth, and untextured.
##
