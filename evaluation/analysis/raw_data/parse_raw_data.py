"""Parse the raw evaluation logs into one long table: one row per uuid per cell.

Cells are model (INIT / CKPT8000) x prompt style (detailed / training) x unit (mm / cm),
identified by the batch folder in each record's model_path.
t2i is recorded as 0 where the image was not timed; those cells take the per-uuid
t2i time from T2I_FALLBACK_BATCH (descriptive only, not used in the bootstrap).
"""
import argparse
import ast
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# batch folder -> (model, prompt_style, unit)
BATCH_CONDITIONS = {
    "batch_INIT_mm_detailed_100_res": ("INIT", "detailed", "mm"),
    "batch_generation_results": ("INIT", "detailed", "cm"),
    "batch_INIT_mm_trained_100_res": ("INIT", "training", "mm"),
    "batch_CKPT00008000_dit_v2_mm_detailed_100_res": ("CKPT8000", "detailed", "mm"),
    "batch_CKPT00008000_dit_v2_cm_detailed_100_res": ("CKPT8000", "detailed", "cm"),
    "batch_CKPT00008000_dit_v2_mm_trained_100_res": ("CKPT8000", "training", "mm"),
}
T2I_FALLBACK_BATCH = "batch_generation_results_with_realimg_less_alpa"

EVAL_LINE_RE = re.compile(
    r"^(?P<uuid>[0-9a-f-]{36}): CLIP=(?P<clip>[-\d.eE]+), BER=(?P<ber>[-\d.eE]+)"
    r"(?:, is_watertight = (?P<wt>True|False))?"
)
FIELDS = ["uuid", "seed", "model", "prompt_style", "unit", "batch", "source_file",
          "CLIP", "BER", "is_watertight", "time_shape", "time_t2i", "t2i_source", "time_total"]


def load_t2i_fallback(path, batch):
    with open(path, newline="", encoding="utf-8") as f:
        return {row["uuid"]: float(row["time_t2i"]) for row in csv.DictReader(f)
                if row["batch"] == batch and row["t2i_status"] == "nonzero"}


def parse_log(path):
    """Yield one row per evaluated model; each CLIP line follows its own dict line."""
    current = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line.startswith("{'uuid'"):
                current = ast.literal_eval(line)
                continue
            m = EVAL_LINE_RE.match(line)
            if not m:
                continue
            if current is None or current["uuid"] != m["uuid"]:
                raise ValueError(f"{path.name}:{n}: CLIP line for {m['uuid']} does not follow its record")
            batch = current["model_path"].replace("\\", "/").split("/")[-3]
            if batch not in BATCH_CONDITIONS:
                raise ValueError(f"{path.name}:{n}: unknown batch {batch}, add it to BATCH_CONDITIONS")
            metrics = current.get("metrics") or {}
            yield {
                "uuid": m["uuid"],
                "seed": current["seed"],
                "batch": batch,
                "source_file": path.name,
                "CLIP": float(m["clip"]),
                "BER": float(m["ber"]),
                # older logs do not print watertightness
                "is_watertight": "" if m["wt"] is None else int(m["wt"] == "True"),
                "time_shape": float(metrics["time_shape"]),
                "time_t2i": float(metrics.get("time_t2i") or 0),
            }
            current = None


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw_dir", default=str(HERE), type=str)
    parser.add_argument("--t2i_csv", type=str,
                        default=str(HERE.parents[1] / "timing" / "per_model_metrics.csv"),
                        help="output of extract_timing_metrics.py")
    parser.add_argument("--out", default=str(HERE.parent / "tables" / "per_sample.csv"), type=str)

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    fallback = load_t2i_fallback(args.t2i_csv, T2I_FALLBACK_BATCH)

    rows = []
    for path in sorted(Path(args.raw_dir).glob("*.out")):  # controlNet/ is a subfolder, not searched
        for row in parse_log(path):
            row["model"], row["prompt_style"], row["unit"] = BATCH_CONDITIONS[row["batch"]]
            if row["time_t2i"] > 0:
                row["t2i_source"] = "measured"
            else:
                row["time_t2i"] = fallback[row["uuid"]]
                row["t2i_source"] = T2I_FALLBACK_BATCH
            row["time_total"] = round(row["time_t2i"] + row["time_shape"], 4)
            rows.append(row)

    seen = {}
    for row in rows:
        key = (row["batch"], row["uuid"])
        if key in seen:
            raise ValueError(f"duplicate {key} in {seen[key]} and {row['source_file']}")
        seen[key] = row["source_file"]

    rows.sort(key=lambda r: (r["model"], r["prompt_style"], r["unit"], r["uuid"]))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} rows -> {args.out}")
    for batch, cond in BATCH_CONDITIONS.items():
        cell = [r for r in rows if r["batch"] == batch]
        wt = [r["is_watertight"] for r in cell if r["is_watertight"] != ""]
        print(f"  {'/'.join(cond):24} n={len(cell):<4} watertight known={len(wt):<4} "
              f"t2i={cell[0]['t2i_source'] if cell else '-'}")
