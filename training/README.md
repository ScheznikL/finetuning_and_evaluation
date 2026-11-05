# Training, preprocessing and generation code

This repository does not contain a copy of Hunyuan3D-2.1. It contains only the files that the fork
[ScheznikL/Hunyuan3D-2.1](https://github.com/ScheznikL/Hunyuan3D-2.1) **added or changed** relative to upstream
[Tencent-Hunyuan/Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) @ `82920d6` (`UPSTREAM_COMMIT`).
`setup_tree.sh` puts them back on top of upstream to give a runnable tree. The pipeline itself is described in
[../README.md](../README.md) §2–§6.

| Folder | Content | Fork path |
|---|---|---|
| `training/overlay/hy3dshape/` | launcher, config, SLURM jobs, `hy3dshape` package changes (data loader, MultiModalConditioner, mT5 encoder, DiT fusion, flow-matching Diffuser + LoRA, pipelines) | `hy3dshape/…` |
| `preprocessing/tools/` | rendering, watertight + sampling, prompt cleaning and checks | `hy3dshape/tools/…` |
| `preprocessing/splits/` | `make_splits.py`, which recreates the 80/20 train/val split | n/a |
| `generation/prompts/` | construction of the 100 test prompts and their variants | `experiments/…` |
| `generation/batch/`, `generation/slurm/` | 100-prompt batch generation (INIT, CKPT, ControlNet), 3D-prior experiments, cluster jobs | `experiments/…`, `batchcompute_scripts/gpu/…` |
| `training/logs/` | `extract_loss.py` and `final_losses.csv` (last logged losses of each training job) | n/a |

`manifest.txt` is the full file list (fork path → path here) and drives both scripts below. `SYNC_INFO` records which
checkout the files were copied from.

## Build a runnable tree

```bash
bash training/setup_tree.sh build --install    # clone upstream @ UPSTREAM_COMMIT, overlay the manifest, pip install
cp training/paths.env.example training/paths.env && $EDITOR training/paths.env
source training/paths.env                       # HUNYUAN_DIR=$(pwd)/build, DATA_ROOT, MODELS_DIR, ...
```

`build/` is git-ignored. The prompt files from `evaluation/prompts/` are copied into `build/experiments/`.

**Paths.** `sync_from_fork.sh` replaced the cluster paths in shell, SLURM and YAML files with the variables in
`paths.env.example`. YAML uses `${oc.env:VAR}`. Python files are copied unchanged and still contain `/dcs/...`
paths in their `__main__` blocks. Edit these before running: `generation/batch/100/*.py`,
`generation/batch/{text_demo_form_ckpt,exp_prior_init,exp_prior_init_img}.py`,
`generation/batch/utils_fantasia3d/render_normals.py`, `generation/prompts/{convert_in_prompts,analyze_token_counts}.py`,
`preprocessing/tools/render/{batch_render_blender,partially_render}.py`.

## Run

1. **Preprocess.** `preprocessing/tools/pipeline_preproc_recurs.sh`, then `render/start_render_part.sh`
   (with `SHARD_ID`/`NUM_SHARDS`), `check_preproc.sh`, `fix_prompts.sh` → `data_move_lang.sh`, and `check_prompts.sh scan`
   (README §2).
2. **Split (optional, for the record).** `python preprocessing/splits/make_splits.py $DATA_ROOT/preprocessed`.
3. **Train.** `sbatch $HUNYUAN_DIR/hy3dshape/scripts/hunyan_geko_finetune.sbatch`
   (→ `train_deepspeed_fine.sh` → `main_finetune.py --deepspeed --fast`, config `finetunung-flowmatching-with-text.yaml`).
   Checkpoints go to `$TRAIN_RESULTS_DIR/finetune_output_folder_1/dit_v2/ckpt/ckpt-step=XXXXXXXX.ckpt/`. DeepSpeed saves
   each one as a folder; the generation scripts load `<ckpt>/out/pytorch_model.bin` (the zero-to-fp32 conversion).
   Full loss curves: `python training/logs/extract_loss.py --tb $TRAIN_RESULTS_DIR/finetune_output_folder_1/dit_v2 --out training/logs/loss_dit_v2.csv`.
4. **Generation.** From `$HUNYUAN_DIR`, run
   `python experiments/100/generate_batch_from_text_initial_model.py --prompt_dir <prompts.json>`.
   The model (INIT or CKPT), the run name, the prior mesh, α and the zip of condition images are set in the script's
   `__main__` block. `evaluation/slurm/seq_slurm.sh` runs generation and then evaluation (EVAL.md §3, §6).

## Sync status and missing parts

> **Status: the files here were copied from the local fork checkout (`ead3927`), not yet from the cluster.**
> Re-run `bash training/sync_from_fork.sh /path/to/cluster/Hunyuan3D-2.1` after step F1 below, then commit.
- **3D prior meshes.** `$DATA_ROOT/raw/cover_prior/coverC_to_obj_pipe.obj` the sourse file is referenced in the paper text.