"""Collect the shape-generation seed of every model in every evaluation run.

Sources (all inside evaluation/):
  timing/per_model_metrics.csv          main runs (from extract_timing_metrics.py)
  analysis/raw_data/controlNet/*.out    ControlNet runs (seed is printed per model)

Seeds were drawn independently per run, so a uuid has a different seed in
different runs unless the run reused the seeds of an earlier one. The matrix
printed at the end shows how many of the 100 seeds two runs share.

Output: seeds_by_run.csv (one row per run x uuid), seeds_wide.csv (uuid x run).
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent

# run -> (model, prompt_style, unit, condition)
RUNS = {
    "batch_generation_results": ("INIT", "detailed", "cm", "T2I image"),
    "batch_generation_results_with_img": ("INIT", "detailed", "cm", "image condition (with_img), seeds of batch_generation_results"),
    "batch_generation_results_with_realimg_less_alpa": ("INIT", "detailed", "cm", "real image (realimg), lower prior alpha"),
    "batch_INIT_mm_detailed_100_res": ("INIT", "detailed", "mm", "image of batch_generation_results"),
    "batch_INIT_mm_trained_100_res": ("INIT", "training", "mm", "image of batch_generation_results"),
    "batch_CKPT00008000_dit_v2_mm_detailed_100_res": ("CKPT8000", "detailed", "mm", "image of batch_generation_results"),
    "batch_CKPT00008000_dit_v2_cm_detailed_100_res": ("CKPT8000", "detailed", "cm", "image of batch_generation_results"),
    "batch_CKPT00008000_dit_v2_mm_trained_100_res": ("CKPT8000", "training", "mm", "image of batch_generation_results"),
    "gen_review_results_with_control_net_normals_al_5": ("INIT", "short", "mm", "ControlNet normals, alpha 0.5"),
    "gen_review_results_with_control_net_depth_al_7": ("INIT", "short", "mm", "ControlNet depth, alpha 0.7"),
}
CONTROLNET_LOGS = {
    "output_norm_al_5.out": "gen_review_results_with_control_net_normals_al_5",
    "review_out_depth_al_7.out": "gen_review_results_with_control_net_depth_al_7",
}
LOG_SEED_RE = re.compile(r"\{'uuid': '([0-9a-f-]{36})', 'seed': (\d+)")


def read_main(path):
    seeds = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["batch"] in RUNS:
                seeds[row["batch"]][row["uuid"]] = (int(row["seed"]), row["source"])
    return seeds


def read_controlnet(log_dir):
    seeds = defaultdict(dict)
    for name, run in CONTROLNET_LOGS.items():
        text = (log_dir / name).read_text(encoding="utf-8", errors="ignore")
        for uuid, seed in LOG_SEED_RE.findall(text):
            seeds[run][uuid] = (int(seed), f"log:{name}")
    return seeds


def get_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--metrics_csv", default=str(EVAL / "timing" / "per_model_metrics.csv"), type=str)
    parser.add_argument("--controlnet_dir", default=str(EVAL / "analysis" / "raw_data" / "controlNet"), type=str)
    parser.add_argument("--prompts", default=str(EVAL / "prompts" / "in_prompts_MM.json"), type=str)
    parser.add_argument("--out_dir", default=str(HERE), type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    seeds = read_main(args.metrics_csv)
    seeds.update(read_controlnet(Path(args.controlnet_dir)))

    with open(args.prompts, encoding="utf-8") as f:
        prompt_uuids = [p["uuid"] for p in json.load(f)]

    for run in RUNS:
        got = seeds.get(run, {})
        assert set(got) == set(prompt_uuids), f"{run}: {len(got)} seeds, uuids differ from the prompt set"

    out_dir = Path(args.out_dir)
    with open(out_dir / "seeds_by_run.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run", "model", "prompt_style", "unit", "condition", "uuid", "seed", "source"])
        for run, cond in RUNS.items():
            for uuid in prompt_uuids:
                seed, source = seeds[run][uuid]
                w.writerow([run, *cond, uuid, seed, source])

    with open(out_dir / "seeds_wide.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["uuid", *RUNS])
        for uuid in prompt_uuids:
            w.writerow([uuid, *(seeds[run][uuid][0] for run in RUNS)])

    print(f"{len(RUNS)} runs x {len(prompt_uuids)} prompts written to {out_dir}")
    print("\nShared seeds (same uuid, same seed):")
    runs = list(RUNS)
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            same = sum(seeds[a][u][0] == seeds[b][u][0] for u in prompt_uuids)
            if same:
                print(f"  {same:3d}/{len(prompt_uuids)}  {a}  =  {b}")
    print("  every other pair: 0/100")
