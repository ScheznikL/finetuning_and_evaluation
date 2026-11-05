"""Extract fine-tuning loss values to CSV.

Two sources:
  --tb DIR      TensorBoard event files written by main.py (TensorBoardLogger, <output_dir>/**/tensorboard/).
                Gives the full per-step curves of train/simple, val/simple, train/lr_abs.
                Needs `pip install tensorboard`.
  --slurm FILE  SLURM .out logs of the training jobs. The Rich progress bar only keeps its last state,
                so this gives one row per job: the final epoch/batch and the last logged losses.

Examples:
  python extract_loss.py --tb $TRAIN_RESULTS_DIR/finetune_output_folder_1/dit_v2 --out loss_dit_v2.csv
  python extract_loss.py --slurm finetune-hun_gecko*.out --out final_losses.csv
"""
import argparse
import csv
import glob
import os
import re

TAGS = ("train/simple", "val/simple", "train/lr_abs")


def from_tensorboard(log_dir):
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    rows = {}
    for event_file in sorted(glob.glob(os.path.join(log_dir, "**", "events.out.tfevents.*"), recursive=True)):
        acc = EventAccumulator(event_file, size_guidance={"scalars": 0})
        acc.Reload()
        for tag in TAGS:
            if tag not in acc.Tags()["scalars"]:
                continue
            for ev in acc.Scalars(tag):
                rows.setdefault(ev.step, {"step": ev.step})[tag] = ev.value
    return [rows[s] for s in sorted(rows)], ["step", *TAGS]


def from_slurm(paths):
    num = r"([0-9]+\.[0-9]+)"
    rows = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read().replace("\r", "\n")
        # The progress bar wraps over several lines; collapse whitespace before matching.
        flat = re.sub(r"\s+", " ", text)
        row = {"job": os.path.basename(path)}
        m = re.search(r"output_dir: (\S+)", text)
        row["output_dir"] = re.sub(r"^.*/train_results", "${TRAIN_RESULTS_DIR}", m.group(1)) if m else ""
        m = re.search(r"Dataset Split \(80/20\): Total=(\d+), Train=(\d+), Val=(\d+)", text)
        row["n_total"], row["n_train"], row["n_val"] = m.groups() if m else ("", "", "")
        epochs = re.findall(r"Epoch (\d+)/(\d+) \S+ (\d+)/", flat)
        row["epoch"], row["max_epoch"], row["batch_in_epoch"] = epochs[-1] if epochs else ("", "", "")
        for tag in ("train/simple", "val/simple"):
            vals = re.findall(re.escape(tag) + r": " + num, flat)
            row[tag] = vals[-1] if vals else ""
        fail = re.findall(r"Current failure rate of data loading: (\d+)/(\d+)=", flat)
        row["load_failures"] = "/".join(fail[-1]) if fail else ""
        rows.append(row)
    fields = ["job", "output_dir", "n_total", "n_train", "n_val", "epoch", "max_epoch",
              "batch_in_epoch", "train/simple", "val/simple", "load_failures"]
    return rows, fields


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tb", help="directory with TensorBoard event files")
    src.add_argument("--slurm", nargs="+", help="SLURM .out files")
    ap.add_argument("--out", required=True, help="output CSV")
    args = ap.parse_args()

    rows, fields = from_tensorboard(args.tb) if args.tb else from_slurm(args.slurm)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
