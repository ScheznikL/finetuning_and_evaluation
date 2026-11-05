import sys
import os
from peft import PeftModel
import torch
import yaml
from PIL import Image

sys.path.insert(0, './hy3dshape')
sys.path.insert(0, './hy3dpaint')

from hy3dshape.rembg import BackgroundRemover
from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipelineInAlighnedSpace, export_to_trimesh
from hy3dshape.utils import instantiate_from_config
from custom_utils import check_file_exists, prepare_output_dir


 #ckpt-step=00024000.ckpt ckpt-step=00044000.ckpt
# Використовуємо конфіг, який відповідає вашій mini-моделі
CONFIG_PATH = '/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/hy3dshape/configs/finetunung-flowmatching-with-text.yaml'

CAPTION = "Create a lower limb prosthesis cover with a height of 400 mm and width of 50 mm"
SEED = 1111


def setup_pipeline_with_custom_weights(ckpt_path):
    
    # shape
    default_subfolder='hunyuan3d-dit-v2-mini'
    model_path = 'tencent/Hunyuan3D-2mini' #'tencent/Hunyuan3D-2.1'
    
    pipeline = Hunyuan3DDiTFlowMatchingPipelineInAlighnedSpace.from_pretrained(
        model_path,
        subfolder = default_subfolder,
        )
    
    return pipeline # FIXME Test
    # base_model = pipeline.model WAS tot try PerfMerge
    
    # # 2. Накладаєте адаптер з чекпоїнта
    # model = PeftModel.from_pretrained(base_model, ckpt_path)

    # # 3. Зливаєте ваги фізично (W_new = W_base + A*B)
    # model = model.merge_and_unload() 

    # # 4. Повертаєте злиту модель у пайплайн
    # pipeline.model = model
    
    # ----------------
    config = yaml.safe_load(open(CONFIG_PATH, 'r'))
    # Використовуємо вашу логіку: instantiate_from_config(config['model']['params']['denoiser_cfg'])
    custom_model = instantiate_from_config(config['model']['params']['denoiser_cfg'])

    sd = torch.load(ckpt_path, weights_only = False, map_location='cpu')# 
    if 'state_dict' in sd:
        sd = sd['state_dict']
    
    # Очищуємо ключі від префіксів Lightning
    sd = {k.replace('model.', '').replace('_forward_module.', ''): v for k, v in sd.items()}
    
    # Завантажуємо ваги в модель
    msg = custom_model.load_state_dict(sd, strict=False)
    custom_model = custom_model.to('cuda').half()
    print(f"Model Load Status: {msg}")

    # 4. Переводимо в потрібний формат і замінюємо модель у пайплайні
    custom_model = custom_model.cuda().half()
    
    # Якщо custom_model використовує Peft всередині:
    if hasattr(custom_model, "merge_and_unload"):
        custom_model = custom_model.merge_and_unload()
        print("LoRA weights merged into base model.")  
        
    pipeline.model = custom_model

    
    return pipeline

def gen_from_text_plus_im(prompt, image_path, prior_path, pipeline, export_dir, seed=1002, num_inference_steps = 100, version_num = None):
    generator = torch.Generator(device='cuda').manual_seed(seed)
    alpha = None
       
    if isinstance(image_path, str) and os.path.exists(image_path):
        image = Image.open(image_path).convert("RGBA")
    elif image_path:
        image = image_path
    else:
        # Тут може бути логіка t2i, якщо зображення немає
        print("Image not found, check your t2i logic.")
        return
    if prior_path:
        # Генерація
        # alpha_values = [0.1, 0.4, 0.7, 1.0]
        alpha_values = [1.0]
        for alpha in alpha_values:
            outputs = pipeline(
                prompt=prompt,
                image=image,
                prior=prior_path,
                alpha=alpha,
                generator=generator,
                output_type='mesh',
                num_inference_steps=num_inference_steps,
                # octree_resolution=380,
            )
    else:
        outputs = pipeline(
        prompt=prompt,
        image=image,
        generator=generator,
        output_type='mesh',
        num_inference_steps=num_inference_steps,
        # octree_resolution=380,
    )  
        
    mesh = export_to_trimesh(outputs)[0]
    val_str = f"{alpha:.1f}".replace(".", "_") if alpha else ""
    with_prior = f'with_prior_Hunyuan_inf_impr_part_{num_inference_steps}'
    final_export_path = prepare_output_dir(export_dir, f'{val_str}{with_prior}_ckpt{version_num}')
    mesh.export(final_export_path)
    print(f"Exported: {final_export_path}")

if __name__ == '__main__':

    version_num = "014" #prior tests: 096 144 154
    ckpt_path = f"/dcs/large/u5745134/traPin_results/finetune_output_folder_1/dit/ckpt/ckpt-step=00{version_num}000.ckpt"
    ckpt_path_init = "/dcs/large/u5745134/hy3dgen_models/tencent/Hunyuan3D-2mini/hunyuan3d-dit-v2-mini/model.fp16.ckpt"
    # IF Deep Speed
    #/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/assets/prior_imgs/image_prior.png
    ckpt_path = "/dcs/large/u5745134/train_results/finetune_output_folder_1/dit/ckpt/ckpt-step=00014000.ckpt/out/pytorch_model.bin"
    image_path = '/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/assets/rembg_ankle1.png' #blue one
    image_prior = '/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/assets//image_prior_part.png'
    image_normal_path = '/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/tmp_results/normals/corner_normal.png'
    output_base = f"/dcs/pg24/u5745134/Desktop/dev/Hunyuan3D-2.1/experiments/objects"
    prior = "/dcs/large/u5745134/dataset/raw/cover_prior/coverC_to_obj_pipe.obj"
    num_inference_steps = 50
    #"CAPTION"  
    
    image_normal = Image.open(image_normal_path).convert("RGB")
    if image_normal.mode == 'RGB':
        rembg = BackgroundRemover()
        image_normal = rembg(image_normal)
    
    pipeline = setup_pipeline_with_custom_weights(ckpt_path)
    gen_from_text_plus_im(CAPTION, image_prior, prior, pipeline, output_base, seed=SEED, num_inference_steps = num_inference_steps, version_num=version_num)