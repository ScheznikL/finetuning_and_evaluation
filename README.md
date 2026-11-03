# EFFICIENCY ANALYSIS OF GENERATIVE 3D NETWORKS WITH THE IMPLEMENTATION OF PARAMETERIZED QUERY

## Abstract
The subject matter of the article is the analysis and modification of a 3D generative neural network for the controlled synthesis of three-dimensional objects based on parameterised textual queries. The goal is to investigate the effectiveness of the 3D generative neural network, using quantitative and qualitative metrics (average generation time, Chamfer Distance, watertightness, and CLIP-Similarity), for generat-ing 3D models in strict accordance with the user’s parameterised query. The tasks to be solved are: to conduct a systematic analysis of the Hunyuan3D 2.0 model; to assess the impact of 3D prior on genera-tion accuracy; to evaluate the impact of the prior coefficient on stability and semantic correspondence using an optimized image condition; to fine-tune the model on the dataset of highly annotated 3D data; to perform a comparative analysis of the results to validate the model’s accuracy and the suitability of the generated objects for prosthetic cover design. The methods used are: machine learning methods based on the Diffusion Transformer architecture, a fine-tuning method using Low-Rank Adaptation (Lo-RA) to align the numerical parameters of the text query with the 3D geometry. The proposed approach also integrates text-to-image (T2I) models to generate specialised condition images and employs a heu-ristic method for formulating input text queries. The results show that the modified model reduces gener-ation time by 17–18%, depending on the query format. It demonstrates a potential improvement in metric accuracy, reducing the MAPE in the upper boundary region of prosthetic cover by 6.4 percentage points (from 15.60% to 9.20%), but worsens the bottom-section prosthetic-cover error. Conclusions. The scien-tific novelty lies in how the proposed modification of the model, through the integration of direct latent space matching and unification of metric information is accomplished: (1) initialising the latent space with a 3D-prior instead of random noise; (2) building ControlNet conditioning images from multi-view normal/depth renders of that same prior instead of a user-supplied image; (3) fine-tuning LoRA to align structured numerical text with 3D geometry via a shared latent space across text, image, and shape mo-dalities, using a Multimodal Fusion block that combines DINOv2-Giant image features with mT5 text embeddings before the Transformer's dual-stream blocks. Future studies will focus on resolving this trade-off and enhancing topological stability to integrate the modified architecture into mobile subsys-tems for personalised prosthetic cover design.


---

## Data Preprocessing, Prompt Sets and Fine-tuning Pipeline

Paths below are relative to the `Hunyuan3D-2.1` repository. Cluster paths (`/dcs/large/u5745134/...`) are kept as they appear in the scripts.

### 1. Dataset layout after preprocessing

Every 3D object (ABO dataset, ~7.9k objects) is stored under `dataset/preprocessed/{UUID}/`:

```
{UUID}/
├── geo_data/{UUID}_surface.npz      # random_surface, sharp_surface (N×6: xyz + normal)
├── geo_data/{UUID}_sdf.npz          # vol / random_near / sharp_near points + SDF labels
├── geo_data/{UUID}_watertight.obj
├── render_cond/00000.png … 00019.png + transforms json   # RGBA condition renders
└── prompt/{UUID}_prompt             # JSON: {"prompt": str, "item_dimensions": {length|height|width: {value, unit}}, ...}
```

### 2. Preprocessing algorithm (`hy3dshape/tools/`)

1. **Format unification.** Source models (`.glb/.gltf/.fbx/.obj`) are converted into triangle OBJ by Blender (`convert_to_obj.py`). This is Step 1.1 of `pipeline_preproc_recurs.sh`.
2. **Prompt staging.** `prepare_and_generate.py` reads the ABO metadata and writes one JSON per object to `temp_prompts_staging/{UUID}_prompt`, with the textual description in `prompt` and the physical size in `item_dimensions`.
3. **Geometry processing** (`pipeline_preproc_recurs.sh → process_obj`, run with GNU `parallel -j 12`):
   - skip the object if `_surface.npz` and `_sdf.npz` already exist;
   - copy the staged prompt into `{UUID}/prompt/`. If no prompt exists, write a placeholder JSON containing `"error": "No metadata found"`;
   - `watertight/watertight_and_sample.py`: build a watertight mesh on a 256³ grid (ε = 2/256), then sample 124,928 uniform and 124,928 sharp-edge surface points with normals, plus volume/near-surface SDF samples.
4. **Condition rendering** (`render/`, Blender 4.x, `--geo_mode`, 512 px):
   - `pipeline_render.sh`: one Blender call per object, 12 views, with a dataset-size guard (650 GB);
   - `batch_render_blender.py` / `partially_render.py` (started by `start_render_part.sh`): a single Blender session renders a whole list. The list is sharded across GPUs with `SHARD_ID/NUM_SHARDS`, and `.done/.lock` flags make reruns resumable. Rendered UUIDs are logged to `rendered_uuids_*_shard*.txt`;
   - `fix_renders.sh`: replaces the old renders with the final set of **20 views per object** (`00000.png…`, plus the camera json) from `renders19.zip`;
   - `renders_move.sh`: packs every `render_cond/*.png` into `render_conds.zip` for transfer.
5. **Integrity check.** `check_preproc.sh` flags every `{UUID}` folder that is missing either `.npz` file (the delete step is commented out, so the script only reports).
6. **Prompt language cleaning:**
   - `fix_prompts.sh` re-copies the English prompts from staging and logs every UUID without an English prompt to `non_eng_log.log`;
   - `data_move_lang.sh` reads that log and moves those folders to `dataset/non_eng_lang/`, which removes them from training;
   - `check_prompts.sh` is the prompt checker:
     - `scan` runs `check_and_fix_prompts.py --dataset … --create-plan translation_plan.json`;
     - `translate` would call `auto_translate_prompts.py` with the Claude API (this script is not in the repository);
     - `apply` writes the hand-filled `translated_prompt` fields back into the prompt JSONs.
   - Detection rules in `check_and_fix_prompts.py`: a prompt counts as non-English if
     1. it contains a non-Latin script (Indic, CJK, Arabic, Cyrillic, Greek, Thai, …), or
     2. more than 20 % of its alphabetic characters are non-ASCII, or
     3. it has more than 10 non-ASCII characters, or
     4. it contains literal `\u` escapes.

     A few special characters (em-dash, smart quotes, accents) are allowed.
   - Result after cleaning (`logg_after_clean.log`): **7,953 prompts, 7,945 English (99.9 %), 8 flagged.**
7. **Train/validation split.** `AlignedShapeTextLatentModule.setup()` lists every `{UUID}` folder, shuffles the list with seed 42 and splits it **80/20** (~6,362 train / ~1,591 validation).
8. **On-the-fly sample construction** (`hy3dshape/data/dit_astl.py`):
   - *Image:* pick 1 of the 20 renders at random. Composite it onto a white background using alpha, crop to the mask bounding box (+5 px), pad to a square (ratio 1.15), resize to 518 px and normalise with mean/std 0.5.
   - *Shape:* draw 81,920 points from `random_surface` (with normals; sharp-edge points disabled, label 0). The frozen ShapeVAE encodes them into latents.
   - *Text* (`final_clean_text`): NFKC normalisation, non-breaking spaces → spaces, `&` → `and`, every character outside `[a-zA-Z0-9\s.,:;\-_/()"']` dropped, whitespace collapsed, then lowercase + capitalise.
   - *Units:* `length/height/width` are converted to mm (factors: mm 1, cm 10, m 1000, in 25.4). A sample with a missing dimension or an unsupported unit raises an error and is skipped.

### 3. Prompts: training vs testing

**Training prompt** (built at load time by `load_textprompt`):

```
"{clean ABO description}. Total length: {L} mm. Total height: {H} mm. Total width: {W} mm."
```

An alternative "detailed / aligned" builder (`load_detailed_textprompt`) writes each value as `"{mm} mm (norm: {mm/scale})"`, where `scale = 1.01·max(L,H,W)`. It also returns `extents_norm` and `scale`, which `ProstheticDiffuser` uses for a global measurement token.

**Test prompt sets** (`experiments/`, 100 prosthetic-cover designs):

| File | How it was produced | Example / format | Used in testing for |
|---|---|---|---|
| `input_prompts.json` | `gen_prompts.py`: 100 `design_templates` × random S/M/L size from `size_chart`. Width = circumference/π, depth = top width/2, wall 0.3–0.5 cm, notch 4–6 × 2–3.5 cm | Full sentence, **cm**: "Create only one … Total length: 43.22 cm. Tapering U-channel: top internal width …" | Original baseline prompts |
| `in_prompts_MM.json` | `convert_in_prompts.py`: cm → mm (XX.XX) | `format: simple_mm`, detailed | Shape generation (DiT text) and size check (`test_sizes.py --check_format simple_mm`) |
| `in_prompts_TRAINING_ALIGNED.json` | `convert_in_prompts.py`: rewritten in the training template. length → *Total length*, channel depth → *Total height*, mean(top, bottom width) → *Total width* | "Matte White PLA texture below-knee prosthetic cover. Total length: 432.20 mm. Total height: 56.20 mm. Total width: 91.50 mm." | Generation and size check in the training format |
| `in_prompts_MM_SHORT.json` / `in_prompts_MM_NO_NUMBERS.json` | `analyze_token_counts.py`, shortening **v3** (all numbers removed). The two files have identical prompts | "Matte White PLA below-knee prosthetic cover. Ergonomic semi-cylindrical U-shaped open channel." | T2I condition images (`generete_image_set.sbatch`, `hunyan_generate_one_example.sbatch`) and CLIP prompts |
| `in_prompts_MM_AUTO_CHOPPED.json` | `analyze_token_counts.py`, shortening **v4**: sentences dropped from the end until ≤ 77 CLIP tokens (`CLIP-ViT-bigG-14`) | "Create only one … open channel. Total length: 432.20 mm." | Reference text for **CLIP-Similarity** (`evaluate_with_renders.py --clip_prompts_dir`) |
| `in_prompt_final_text.json` | 6 hand-picked styles with a separate `prompt_t2i` for image editing | `prompt_t2i`: "Edit the shape of cover to match Steampunk …"; `prompt`: detailed mm | Final single-model qualitative run (`hunyan_fg_gpu_one_model.sbatch`) |

Shortening levels in `analyze_token_counts.py`:
- **v1**: removes "Create only one" and "Total";
- **v2**: v1 plus removing the style phrases and the "Tapering U-channel:" label;
- **v3**: keeps only material, object type and shape;
- **v4**: drops sentences from the end until the prompt fits the token limit.

The test loop (`batchcompute_scripts/gpu/hunyan_f_gpu_100.sbatch`) runs three stages:
1. generate 100 models from a checkpoint;
2. evaluate CD, watertightness and CLIP-Similarity against the AUTO_CHOPPED prompts;
3. check measured sizes against the dimensions in `in_prompts_MM.json`.

### 4. Text fine-tuning setup: MultiModalConditioner

Config: `hy3dshape/configs/finetunung-flowmatching-with-text.yaml`.

- **Conditioner:** `hy3dshape.models.conditioner.MultiModalConditioner` returns `{'main': image tokens, 'text': {'emb', 'mask'}}`.
  - Image branch: `DinoImageEncoder`, **DINOv2-Giant** (hidden 1536, 40 layers, patch 14, 518 px, CLS token kept).
  - Text branch: `MT5TextEncoder`, **google/mt5-large**, encoder frozen, tokens padded/truncated to `max_length = 128`. A `TextCondAdapter` (Linear d_model → 1536 + LayerNorm) projects the text into the image-token dimension, which puts both modalities in one 1536-d space.
  - `drop_ratio = 0.1` (classifier-free-guidance dropout) and `unconditional_embedding()` supplies image zeros and text zeros with an all-false mask.
- **Fusion in the DiT** (`Hunyuan3DDiT.forward`):
  1. `cond = concat([image_tokens, text_tokens], dim=1)`;
  2. optional `part_tokens` and `global_token` are appended;
  3. `cond_in` (Linear 1536 → hidden) projects the sequence;
  4. the dual-stream blocks attend jointly over `(cond, latent)`.
- **Modes:** `multimodal: true` is Case A (text + 3D + image guide); `false` is Case B (text + 3D). At inference, text is the primary condition and the image is optional.

### 5. Training pipeline

1. **Launch.** `hy3dshape/scripts/hunyan_geko_finetune.sbatch` (SLURM `gecko`, 2 GPUs, 16 CPU, 24 h, CUDA 12.6, env `hunyuan3D_torch28`) → `scripts/train_deepspeed_fine.sh` (NCCL setup, copies the config into `output_dir`) → `python3 main_finetune.py --deepspeed --fast` (DeepSpeed stage 1 when more than one GPU). Single-GPU variant: `train_finetune.sh`.
2. **Model** (`hy3dshape.models.diffusion.flow_matching_stit.Diffuser`):
   - Frozen **ShapeVAE** (`Hunyuan3D-2mini / hunyuan3d-vae-v2-mini-withencoder`): surface points → latents × `z_scale_factor = 1.00395`.
   - Denoiser **Hunyuan3D-DiT v2-mini**, wrapped with **LoRA** (PEFT, r = α = 16, targets `qkv`, `mlp`, `proj`). Only the DiT parameters go to the optimiser.
   - **EMA** (`LitEma`, decay 0.999) updated after every batch.
3. **Objective:** linear-path optimal-transport **flow matching** with velocity prediction (`create_transport(path_type=Linear, prediction=velocity)`). The loss is computed on the VAE latents with `contexts` from the conditioner. Conditioning runs in bf16; the VAE encode runs in fp16 under `no_grad`.
4. **Optimisation:**
   - AdamW (β = 0.9/0.99, ε = 1e-6, weight decay 0.01), base LR **1e-5** with no LR scaling;
   - `LambdaWarmUpCosineFactorScheduler`: 500 warm-up steps, f_start 1e-6, f_min 1e-3;
   - bf16 AMP, gradient clipping (norm 1.0), gradient accumulation 4, batch 2 per GPU, 5 epochs;
   - a checkpoint every 1,000 steps, validation every 100 steps on 16 batches.
5. **Checkpoints** are written to `train_results/finetune_output_folder_1/dit_v2/ckpt/ckpt-step=XXXXXXXX.ckpt`, for example `CKPT00008000_dit_v2_mm_detailed`, which is evaluated in section 3.
6. **Inference:** `Hunyuan3DDiTFlowMatchingPipelineInAlighnedSpace`, Euler ODE, 50 steps. Optional 3D prior: `experiments/text_demo_form_ckpt.py`, `exp_prior_init*.py`.
