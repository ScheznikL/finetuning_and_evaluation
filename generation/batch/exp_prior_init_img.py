#TRY_INX = "_alpha_0_9"
TRY_INX = "test-0"
SEED = 1111
CAPTION_demo = "Create a lower limb prosthesis cover with a height of 0.5m"
#CAPTION = ""
PRIOR_PATH = "/dcs/large/u5745134/dataset/raw/cover_prior/coverC_to_obj_pipe.obj"
TEMP_RESULTS = "/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/tmp_results"

import os
from pathlib import Path
import sys
import time
from venv import logger

import diffusers
import numpy as np
import torch
sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')

from PIL import Image
from hy3dshape.rembg import BackgroundRemover
from hy3dshape.pipelines import HunyuanDiTPipeline, Hunyuan3DDiTFlowMatchingPipelineWithPriorInitialization
from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
from cover_caption import CAPTION, CAPTION_ankle
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler, StableDiffusionInstructPix2PixPipeline
from diffusers.utils import load_image

from utils_fantasia3d.render_normals import render_normals_blender
from utils_fantasia3d.process_canny import process_canny
from transformers import DPTFeatureExtractor, DPTForDepthEstimation

from functools import lru_cache

_depth_model = None
_depth_extractor = None


def get_depth_model():
    global _depth_model, _depth_extractor

    if _depth_model is None:
        _depth_extractor = DPTFeatureExtractor.from_pretrained(
            "Intel/dpt-hybrid-midas"
        )
        _depth_model = DPTForDepthEstimation.from_pretrained(
            "Intel/dpt-hybrid-midas"
        ).to("cuda").eval()

    return _depth_extractor, _depth_model


def rgb_to_depth(pil_image: Image.Image) -> Image.Image:
    extractor, model = get_depth_model()

    inputs = extractor(images=pil_image, return_tensors="pt").to("cuda")

    with torch.no_grad():
        depth = model(**inputs).predicted_depth

    depth = torch.nn.functional.interpolate(
        depth.unsqueeze(1),
        size=pil_image.size[::-1],
        mode="bicubic",
        align_corners=False,
    ).squeeze()

    depth = depth.cpu().numpy()
    depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
    depth = (depth * 255).astype(np.uint8)

    return Image.fromarray(depth)

@lru_cache(maxsize=1)
def get_base_models(model_name):
    controlnet = ControlNetModel.from_pretrained(
        model_name,
        torch_dtype=torch.float16
    )

    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=controlnet,
        torch_dtype=torch.float16
    ).to("cuda")

    return pipe, controlnet

from pathlib import Path

from functools import lru_cache
import torch

@lru_cache(maxsize=1)
def get_edit_pipe():
    pipe = StableDiffusionInstructPix2PixPipeline.from_pretrained(
        "timbrooks/instruct-pix2pix",
        torch_dtype=torch.float16
    ).to("cuda")

    pipe.enable_model_cpu_offload()
    return pipe


def apadt_prompt(prompt, prefix = "Turn given image of prosthetic cover into"):
    prompt=f"{prefix} {prompt}"
    return prompt
    
def edit_image_pix2pix(
    prompt,
    normal_map_dir = None,
    #controlnet_conditioning_scale=[0.8, 1.0],  # unused but kept
    usereal=True,
    im_path=None,
    prompt_prefix = None
):
    filename = "edited_prior_image.png"
    #negative_prompt = "monochrome, lowres, worst quality, low quality"

    pipe = get_edit_pipe()
    generator = torch.Generator(device="cuda").manual_seed(2)

    images = []
    if prompt_prefix is not None:
        prompt = apadt_prompt(prompt=prompt, prefix = prompt_prefix)
    
    if usereal and im_path is not None:
        print("[INFO] EditInfinity: using real image")
        images.append(load_image(im_path))
    else:
        print(f"[INFO] loading images from {normal_map_dir}")
        for file in sorted(os.listdir(normal_map_dir)):
            images.append(load_image(os.path.join(normal_map_dir, file)))

    # Edit pipelines take single image
    input_image = images[0]

    edited = pipe(
        prompt=prompt,
        image=input_image,
        num_inference_steps=50,
        image_guidance_scale=1.5,   # Edit strength
        guidance_scale=7.5,
        generator=generator,
    ).images[0]

    save_path = Path.cwd() / filename
    print(f"[INFO] Save path is {save_path}")
    return edited, filename

def edit_image_nm(normal_map_dir, prompt):
    """
    Функція для редагування зображення за допомогою декількох карт нормалей (Multi-ControlNet).
    Забезпечує жорстку відповідність геометрії при генерації текстур.
    """
    
    # Ініціалізація декількох моделей ControlNet для обробки різних ракурсів
    controlnet = [
        ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-normal", torch_dtype=torch.float16),
        ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-normal", torch_dtype=torch.float16),
        ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-normal", torch_dtype=torch.float16),
    ]

    # Завантаження основного пайплайну Stable Diffusion v1.5
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=controlnet,
        torch_dtype=torch.float16
    )

    # Використання швидкого та стабільного планувальника UniPC
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload()

    # Налаштування генератора для відтворюваності результатів
    generator = torch.Generator().manual_seed(2)

    # Негативний запит для запобігання артефактам
    negative_prompt = "monochrome, lowres, bad anatomy, worst quality, low quality"

    images = []
    print(f"[INFO] start collecting normals from {normal_map_dir}")
      
    if normal_map_dir:
        # Зчитування та сортування карт нормалей
        for file in sorted(os.listdir(normal_map_dir)):
            img = load_image(os.path.join(normal_map_dir, file))
            images.append(img)
    else:
        raise KeyError("No normal map directory passed!")

    # ВАЖЛИВО: кількість ваг у списку має відповідати кількості завантажених зображень/моделей.
    # Тут ми встановлюємо високий пріоритет (1.0) для останньої карти для максимальної точності.
    conditioning_scales = [0.8, 0.8, 1.0] 

    image = pipe(
        prompt,
        images,
        generator=generator,
        negative_prompt=negative_prompt,
        controlnet_conditioning_scale=conditioning_scales,
    ).images[0]

    return image
    
def edit_image_controlnet(
    prompt,
    normal_map_dir =None,
    controlnet_conditioning_scale=[0.7, 1.0],
    usereal=True,
    im_path=None,
    is_normal_mode = None
):
    
    if is_normal_mode:
        model_name = "lllyasviel/sd-controlnet-normal"
    else:
        model_name = "lllyasviel/sd-controlnet-depth"
        
    filename = "edited_prior_image.png"
    negative_prompt = "monochrome, lowres, worst quality, low quality"

    pipe, base_controlnet = get_base_models(model_name)

    images = []

    if usereal and im_path is not None:
        print(f"[INFO] use real image is {usereal}")
        rgb = load_image(im_path)
        depth = rgb_to_depth(rgb)
        images.append(depth)
        #images.append(load_image(im_path))
    else:
        print(f"[INFO] start collecting normals from {normal_map_dir}")
        for file in sorted(os.listdir(normal_map_dir)):
            images.append(load_image(os.path.join(normal_map_dir, file)))

    # ✅ replicate controlnet references (no reload)
    controlnets = [base_controlnet] * len(images)

    generator = torch.Generator(device="cuda").manual_seed(2)

    if not usereal:
        image = pipe(
            prompt,
            images,
            controlnet=controlnets,
            #num_inference_steps=20,
            generator=generator,
            negative_prompt=negative_prompt,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
        ).images[0]

        save_path = Path(im_path).parent / filename

    else:
        image = pipe(
            prompt,
            images[0],
            num_inference_steps=50,
            controlnet = controlnets,
            generator=generator,
            negative_prompt=negative_prompt,
            controlnet_conditioning_scale = controlnet_conditioning_scale[0]
        ).images[0]

        save_path = Path.cwd() / filename

    #print(f"[INFO] Save path is {save_path}")
    return image, filename



def textgen_with_mv_prior(prompt, prior_path, pipeline, export_dir = "./tmp", seed = SEED, im_path = None):
    from hy3dshape.pipelines import export_to_trimesh

    time_meta = {}
    
    norm_out_dir = os.path.join(TEMP_RESULTS,"normals_from_exp")
    
    image_path = './rembg_CAPTION_ankle.png'
    
    render_normals_blender(prior_path, norm_out_dir)

    if not im_path:
        image, path = edit_image_controlnet(normal_map_dir=norm_out_dir, prompt=prompt)
    else:
        image, _= edit_image_controlnet(im_path=im_path, prompt=prompt) 
    
    if prompt: print('prompt is', prompt)
    else: 
        print(f"prompt empty") 
        return    
    
    
    if not check_file_exists(path):
        raise KeyError
        # t2i_worker = HunyuanDiTPipeline('Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled') 
        # start_time = time.time()
        # try:
        #     image = t2i_worker(prompt, seed=SEED)
        # except Exception as e:
        #     print(e)
        #     return    
        # time_meta['text2image'] = time.time() - start_time

        #image.save(f'{image_path}')
    # else:
    #     image = Image.open(image_path).convert("RGB")

    if image.mode == "RGB":
        start_time = time.time()
        rembg = BackgroundRemover()
        image = rembg(image)
        #image = BackgroundRemover(image = image.convert('RGB'))
        time_meta['remove background'] = time.time() - start_time

    #image.save(image_path)

    # remove disk io to make responding faster, uncomment at your will.
    # image.save(os.path.join(save_folder, 'rembg.png'))

    # image to white model
    start_time = time.time()

    generator = torch.Generator() # for rand nums
    generator = generator.manual_seed(int(seed))
    alpha = [0.1, 0.4, 0.7, 1]
    alpha = [0.7]

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
        export_dir = prepare_output_dir(export_dir, val_str)
        exp_file = os.path.join(export_dir, f'{val_str}.glb')
        
        print(f"[INFO] Saving shape to {exp_file}")
        mesh.export(exp_file)

def prepare_output_dir(file_path, val_str = None):
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    os.makedirs(directory, exist_ok=True)
    
    # if directory and not os.path.exists(directory):
      
    #     print(f"Created - {directory}")
    # if val_str:
    #     os.makedirs(directory, exist_ok=True)
    #     name, ext = os.path.splitext(filename)
    #     new_filename = f"{val_str}_{name}{ext}"
    #     return os.path.join(directory, new_filename)
    return directory

def check_file_exists(file_path):
    if os.path.exists(file_path):
        print(f"File already exists: {file_path}")
        return True
    else:
        print(f"File does not exist: {file_path}")
        return False

if __name__ == '__main__':    
    try:
        from torchvision_fix import apply_fix
        apply_fix()
    except ImportError:
        print("Warning: torchvision_fix module not found, proceeding without compatibility fix")                                      
    except Exception as e:
        print(f"Warning: Failed to apply torchvision fix: {e}")

    # shape pipe
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
    #prior_path
    prior_path = PRIOR_PATH
    im_real_cover_path = './rembg_CAPTION_ankle.png'
    #generate
    textgen_with_mv_prior(CAPTION_ankle, prior_path = prior_path, pipeline = pipeline_shapegen, seed=SEED, 
                          export_dir=f"./out/objects/{TRY_INX}",
                          im_path = im_real_cover_path)