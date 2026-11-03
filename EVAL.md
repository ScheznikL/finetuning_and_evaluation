# Evaluation protocol

This file describes how the 100-prompt evaluation in the article was produced and how to reproduce
every reported number. It complements [README.md](README.md) (preprocessing, prompt sets, fine-tuning).

Everything referenced here is in [`evaluation/`](evaluation/). Generation code lives in the fork
[ScheznikL/Hunyuan3D-2.1](https://github.com/ScheznikL/Hunyuan3D-2.1) (commit `ead3927`); paths
starting with `Hunyuan3D-2.1/` refer to it.

```
evaluation/
├── prompts/     the 100 test prompts in every format used
├── seeds/       the seed of every generated model, per run (+ export_seeds.py)
├── metrics/     mesh measurement, CLIP-Similarity, BER/watertightness, rendering
├── analysis/    raw evaluation logs, statistics scripts, final tables
├── timing/      per-model generation times and seeds extracted from the logs
├── results/     per-run summaries (detailed_results.json, evaluation_results.json, ...)
├── slurm/       cluster job templates
└── data/        empty placeholders for meshes, condition images and run archives
```

---

## 1. Test prompt set

100 below-knee prosthetic-cover designs. Each prompt combines a design template (material, colour,
style) with a size drawn from an S/M/L size chart; the generator and templates are
`Hunyuan3D-2.1/experiments/gen_prompts.py` and `design_templates.py` (README §3). Every prompt has a
fixed `uuid`, which is the pairing key for all comparisons below.

| File in `evaluation/prompts/` | Format | Used for |
|---|---|---|
| `input_prompts.json` | detailed sentence, **cm** | generation, unit = cm cells |
| `in_prompts_MM.json` | detailed sentence, **mm** + `dimensions` (ground truth, mm) | generation, unit = mm cells; ground truth for size measurement |
| `in_prompts_TRAINING_ALIGNED.json` | training template: `Total length / height / width` in mm | generation, prompt style = training cells |
| `in_prompts_MM_AUTO_CHOPPED.json` | ≤ 77 CLIP tokens (shortening v4) | reference text for CLIP-Similarity |
| `in_prompts_MM_SHORT.json` | no numbers (shortening v3) | T2I / ControlNet condition images |

The `dimensions` field of `in_prompts_MM.json` is the ground truth for every size metric:
`total_length_mm, top_width_mm, bottom_width_mm, channel_depth_mm, wall_thickness_mm, notch_width_mm, notch_depth_mm`.

## 2. Evaluation runs

Each run generates one model per prompt (100 models). The run name is the output folder name and the
key used in every table and in `seeds/`.

| Run | Model | Prompt style | Unit | Condition | Article |
|---|---|---|---|---|---|
| `batch_generation_results` | INIT | detailed | cm | T2I image (generated in this run) | TODO(table №) |
| `batch_generation_results_with_img` | INIT | detailed | cm | image condition, seeds of `batch_generation_results` | TODO(table №) |
| `batch_generation_results_with_realimg_less_alpa` | INIT | detailed | cm | real image, lower prior α | T2I time reference only |
| `batch_INIT_mm_detailed_100_res` | INIT | detailed | mm | image of `batch_generation_results` | 2×2 analyses A, B |
| `batch_INIT_mm_trained_100_res` | INIT | training | mm | image of `batch_generation_results` | 2×2 analysis A |
| `batch_CKPT00008000_dit_v2_mm_detailed_100_res` | CKPT8000 | detailed | mm | image of `batch_generation_results` | 2×2 analyses A, B |
| `batch_CKPT00008000_dit_v2_mm_trained_100_res` | CKPT8000 | training | mm | image of `batch_generation_results` | 2×2 analysis A |
| `batch_CKPT00008000_dit_v2_cm_detailed_100_res` | CKPT8000 | detailed | cm | image of `batch_generation_results` | 2×2 analysis B |
| `gen_review_results_with_control_net_normals_al_5` | INIT | short | mm | ControlNet, normal renders of the prior, α = 0.5 | TODO(table №) |
| `gen_review_results_with_control_net_depth_al_7` | INIT | short | mm | ControlNet, depth renders of the prior, α = 0.7 | TODO(table №) |

- **INIT** = `tencent/Hunyuan3D-2mini`, subfolder `hunyuan3d-dit-v2-mini`, no fine-tuning.
- **CKPT8000** = the LoRA fine-tuned DiT after 8,000 steps (`dit_v2/ckpt/ckpt-step=00008000.ckpt`, README §5).
- In the INIT/CKPT8000 cells (the 2×2 analyses) the condition image is not regenerated: every cell loads
  the same image per `uuid` from `batch_generation_results/100_test_images/`. Model, prompt style and
  unit are therefore the only factors that differ between cells.

Earlier checkpoints (CKPT 14k, 21k, 30k) were screened during development and are not part of the
article; their outputs are not included.

## 3. Generation protocol

Scripts: `Hunyuan3D-2.1/experiments/100/generate_batch_from_text_initial_model.py` (INIT and CKPT
runs), `gen_from_prompt_100_with_ControlNet.py` (ControlNet runs); cluster wrapper
`Hunyuan3D-2.1/batchcompute_scripts/gpu/hunyan_f_gpu_100.sbatch`.

For every prompt `uuid`:

1. **Condition image.** `batch_generation_results`: generated from the prompt by
   `Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled`; other INIT/CKPT runs: loaded from that run's
   archive. ControlNet runs: an image edited from normal/depth renders of the 3D prior with the
   `in_prompts_MM_SHORT.json` prompt.
2. **Background removal.** `hy3dshape.rembg.BackgroundRemover` (`isnet-general-use` in the ControlNet runs).
3. **Shape generation.** `torch.Generator().manual_seed(seed)`, then the shape pipeline with the image,
   the text prompt and the 3D prior `coverC_to_obj_pipe.obj` (prior-initialised latent, α = 0.5 unless
   stated in §2); flow matching, Euler, **50 steps**; output `<uuid>.glb`.
4. **Metadata.** `<uuid>_meta.json` / `<uuid>.json` stores `uuid, seed, prompt, model_path` and
   `metrics.time_t2i`, `metrics.time_shape` (seconds, wall clock).

Templates for running generation + evaluation on a cluster: `evaluation/slurm/seq_slurm.sh`,
`evaluation/slurm/hunyan_eagle_eval.sbatch` (set `REPO_DIR`, `DATA_DIR`, `HUNYUAN_DIR`, `CHECKPOINT_PATH`).

## 4. Seeds

`evaluation/seeds/` lists the seed actually used for every generated model:

- `seeds_by_run.csv`: one row per run × uuid: `run, model, prompt_style, unit, condition, uuid, seed, source`
  (1,000 rows: 10 runs × 100 prompts);
- `seeds_wide.csv`: one row per uuid, one column per run;
- `export_seeds.py`: rebuilds both files from `timing/per_model_metrics.csv` (seeds read from the job
  logs and per-model JSONs) and `analysis/raw_data/controlNet/*.out`, and checks that every run has
  exactly one seed for each of the 100 prompt uuids.

**How the seeds were drawn.** Each INIT/CKPT run drew a new seed per prompt,
`random.randint(1000, 999999)`; the ControlNet runs take the seed from the input metadata when it has
one and otherwise draw `torch.seed()`. Seeds are therefore shared only where a run reused another
run's seeds:

| Runs | Same seed per uuid |
|---|---|
| `batch_generation_results` = `batch_generation_results_with_img` | 100 / 100 |
| `..._control_net_normals_al_5` = `..._control_net_depth_al_7` | 100 / 100 |
| every other pair, including INIT vs CKPT8000 | 0 / 100 |

INIT and CKPT8000 were thus generated with **different** seeds for the same prompt. All model
comparisons are paired by prompt `uuid` with the same condition image, so seed-to-seed variation is
part of the per-prompt difference and is included in the bootstrap confidence intervals (§7). To
regenerate any model exactly, pass the listed seed for that run and uuid to the generator in step 3.

## 5. Preprocessing before measurement

1. **CLIP prompt.** `metrics/rewrite_prompts_clip.py <batch_dir>` writes `<uuid>_compressed_meta.json`
   with `prompt_clip`; the article runs use the ≤ 77-token `in_prompts_MM_AUTO_CHOPPED.json`
   (`--clip_prompts_dir`).
2. **Renders for CLIP.** `metrics/render_two_views.py` (Blender 4.2.1, headless): two views of the
   mesh, `front` (camera at (0, −2, 0)) and `side` ((2, 0, 0)), both looking at the origin, 512 × 512 px.
3. **Mesh normalisation for size metrics** (`metrics/measure_batch.py --normalize`):
   load the GLB with trimesh, reorient so the longest extent is the length axis, then scale
   **uniformly** so the length equals the prompt length (`total_length_mm`). Proportions are kept, so
   width/depth errors are measured relative to a correctly sized length. Units are mm throughout
   (cm prompts are converted ×10). Without `--normalize` the raw output scale is measured instead.

## 6. Metrics

| Metric | Script | Definition |
|---|---|---|
| Dimension error (MAE, MAPE) | `metrics/measure_batch.py` | per dimension: `|prompt − model|` (mm) and `|prompt − model| / prompt × 100`; slice-based top/bottom width and channel depth |
| Chamfer Distance | `metrics/chamfer.py` | mean squared nearest-neighbour distance gt→gen plus gen→gt between point samples (scipy cKDTree) |
| BER / watertight | `metrics/bse.py` | BER = boundary edges / total edges; watertight ⇔ 0 boundary edges |
| CLIP-Similarity | `metrics/clip_sim.py` | mean cosine similarity between the CLIP prompt and the two renders, `laion/CLIP-ViT-bigG-14-laion2B-39B-b160k` |
| Generation time | per-model metadata | `time_t2i`, `time_shape`, `time_total = time_t2i + time_shape` (s) |

Commands per run (meshes in `evaluation/data/`, see §9):

```bash
cd evaluation/metrics
# CLIP + BER/watertight (writes evaluation_results.json)
BLENDER=/path/to/blender python evaluate_with_renders.py \
    --models_dir ../data/meshes/<run>/100_test_models --base_dir ../data/meshes/<run> \
    --batch_name <run> --output_metrics ../results/<run>/evaluation_results.json \
    --clip_prompts_dir ../prompts/in_prompts_MM_AUTO_CHOPPED.json --do_clip True
# size error (writes detailed_results.json, statistics_summary.json, summary_report.txt)
python measure_batch.py --zip_path ../data/run_archives/<run>.zip --batch_name <run> \
    --output_metrics_dir ../results/<run> --prompts_json_file ../prompts/in_prompts_MM.json --normalize
```

## 7. Statistics

1. `analysis/raw_data/parse_raw_data.py`: parses the raw evaluation logs (`analysis/raw_data/*.out`)
   into `analysis/tables/per_sample.csv`, one row per uuid per cell. Where `time_t2i` was not timed
   (image reused), it takes the per-uuid T2I time of `batch_generation_results_with_realimg_less_alpa`
   from `timing/per_model_metrics.csv` (descriptive only).
2. `analysis/effects.py`: two paired 2×2 designs on per-uuid contrast scores:
   - **A**: model (INIT / CKPT8000) × prompt style (detailed / training), mm prompts;
   - **B**: model (INIT / CKPT8000) × unit (mm / cm), detailed prompts.

   Main effects, interaction and simple effects as mean differences with 95 % **BCa bootstrap** CIs
   (10,000 resamples, seed 0), effect size d_z, Holm correction over the three tests per analysis and metric.
   Output: `analysis/tables/effects.csv`, `effects.md`, `cell_means.csv`.
3. `analysis/bootstrap.py`: paired BCa bootstrap of one metric between two runs (e.g.
   `analysis/clip_s_train_mm/`: CKPT8000 vs INIT, CLIP, training-style prompts).
4. `analysis/mae_check/scale_sensitivity.py`, `analysis/size_correlation.py`: does the generated size
   follow the requested size (Pearson r, slope, CV; paired test baseline vs modified).
5. `analysis/extract_timing_metrics.py`: rebuilds `timing/*.csv` (times and seeds) from the job logs
   and run archives in `evaluation/data/`.

## 8. Reproducing the reported numbers

From the committed logs and summaries (no GPU, no meshes needed; `numpy`, `scipy`):

```bash
cd evaluation/analysis
python raw_data/parse_raw_data.py      # -> tables/per_sample.csv
python effects.py                      # -> tables/effects.csv, effects.md, cell_means.csv
python bootstrap.py --a clip_s_train_mm/modified.csv --b clip_s_train_mm/baseline.csv --metric CLIP
python ../seeds/export_seeds.py        # -> ../seeds/seeds_by_run.csv, seeds_wide.csv
```

These outputs are byte-identical to the files committed in `analysis/tables/` and
`analysis/clip_s_train_mm/bootstrap_output.txt`. Per-run size and CLIP summaries are in
`evaluation/results/<path>/<run>/` (`statistics_summary.json`, `summary_report.txt`).

Full reproduction from scratch: generate the 100 models per run with the seeds of §4 (§3), then run §6
and §7.

## 9. Data placeholders

Meshes, images and archives are not stored in git. `evaluation/data/` contains empty folders, each
with a README describing the expected layout:

| Folder | Content |
|---|---|
| `data/meshes/<run>/100_test_models/` | `<uuid>.glb` + `<uuid>_meta.json` |
| `data/condition_images/` | the 100 condition images `<uuid>.png` shared by the INIT/CKPT8000 runs |
| `data/run_archives/` | `<run>.zip` (models + images), read by `measure_batch.py` and `extract_timing_metrics.py` |
| `data/by_prompt_type/` | optional unpacked run folders with job logs |

## 10. Environment

- Python packages: `evaluation/requirements.txt` (numpy 1.26.4, scipy, trimesh, torch, transformers, opencv, kiui).
- Blender 4.2.1 for rendering (`BLENDER` environment variable), `OPENCV_IO_ENABLE_OPENEXR=1`.
- Models are downloaded from Hugging Face (`HF_HOME` sets the cache).
- The article runs used one GPU per job on a SLURM cluster (CUDA 13.0.2 for evaluation); generation
  environment as in README §5.
