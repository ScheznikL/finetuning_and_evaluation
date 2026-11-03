"""
Collect per-model timing (time_t2i / time_shape) and evaluation metrics from
.out logs, per-model JSONs in by_prompt_type/, and per-model JSONs inside the
ZIP archives of the tests. Records are deduplicated by (batch, uuid), where
batch is the folder before 100_test_models/ in the record's own model_path.

Output goes to evaluation/timing/ (see write_outputs for the file list).

Usage:
    python extract_timing_metrics.py [--zip-dir PATH] [--out-dir PATH]
"""
import argparse
import ast
import csv
import json
import re
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # evaluation/
SEARCH_DIR = ROOT / "data" / "by_prompt_type"
DEFAULT_ZIP_DIR = ROOT / "data" / "run_archives"
DEFAULT_OUT_DIR = ROOT / "timing"

# Old data, excluded from every source (checked against batch name and zip name)
EXCLUDED_BATCHES = {
    "batch_CKPT00014000_100_res",
    "batch_CKPT00021000_dit_v2_mm_trained_100_res",
    "batch_CKPT00030000_100_res",
    "batch_CKPT00030000_mm_100_res",
}

# Per-model JSONs: <uuid>.json or <uuid>_meta.json (not _compressed_meta.json)
MODEL_JSON_RE = re.compile(r"[0-9a-f-]{36}(_meta)?\.json$")
EVAL_LINE_RE = re.compile(
    r"^(?P<uuid>[0-9a-f-]{36}): CLIP=(?P<clip>[-\d.eE]+), BER=(?P<ber>[-\d.eE]+)"
    r"(?:, is_watertight = (?P<wt>True|False))?"
)
SOURCE_ORDER = ["out", "json", "zip"]
SOURCE_LABELS = {"out": "out", "json": "json", "zip": "json+zip"}


def batch_of(record, fallback):
    """Batch name from model_path (.../<batch>/100_test_models/<file>)."""
    parts = record.get("model_path", "").replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[-2] == "100_test_models":
        return parts[-3]
    return fallback


def to_float(value):
    if value is None or value == "":
        return None
    return float(value)


class Collector:
    def __init__(self):
        self.models = {}                 # (batch, uuid) -> record dict
        self.evals = []                  # per-evaluation rows from .out files
        self.conflicts = []

    def add(self, record, source, location, fallback_batch):
        batch = batch_of(record, fallback_batch)
        if batch in EXCLUDED_BATCHES:
            return None
        metrics = record.get("metrics") or {}
        t2i = to_float(metrics.get("time_t2i"))
        shape = to_float(metrics.get("time_shape"))
        key = (batch, record["uuid"])

        existing = self.models.get(key)
        if existing is None:
            self.models[key] = {
                "batch": batch,
                "uuid": record["uuid"],
                "seed": int(record["seed"]),
                "time_t2i": t2i,
                "time_shape": shape,
                "sources": {source},
                "locations": [location],
            }
            return key

        same = (existing["seed"] == int(record["seed"])
                and existing["time_t2i"] == t2i
                and existing["time_shape"] == shape)
        if same:
            existing["sources"].add(source)
            existing["locations"].append(location)
        else:
            self.conflicts.append(
                f"{batch} {record['uuid']}: kept seed={existing['seed']} "
                f"t2i={existing['time_t2i']} shape={existing['time_shape']} "
                f"from {existing['locations'][0]} | skipped seed={record['seed']} "
                f"t2i={t2i} shape={shape} from {location}"
            )
        return key

    def read_out(self, path):
        rel = str(path.relative_to(ROOT))
        uuid_to_key = {}
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("{'uuid'"):
                    record = ast.literal_eval(line)
                    key = self.add(record, "out", rel, path.parent.name)
                    uuid_to_key[record["uuid"]] = key
                    continue
                m = EVAL_LINE_RE.match(line)
                if m and uuid_to_key.get(m["uuid"]):
                    batch, uuid = uuid_to_key[m["uuid"]]
                    self.evals.append({
                        "batch": batch,
                        "uuid": uuid,
                        "eval_file": rel,
                        "CLIP": float(m["clip"]),
                        "BER": float(m["ber"]),
                        "is_watertight": m["wt"] or "",
                    })

    def read_local_json(self, path):
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        # Folder holding the file, skipping 100_test_models / train_alighned etc.
        fallback = path.parent.name
        if fallback == "100_test_models":
            fallback = path.parent.parent.name
        self.add(record, "json", str(path.relative_to(ROOT)), fallback)

    def read_zip(self, path):
        if path.stem in EXCLUDED_BATCHES:
            print(f"Skipping {path.name} (excluded)")
            return
        print(f"Reading {path.name} ...")
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if MODEL_JSON_RE.search(name):
                    record = json.loads(zf.read(name))
                    self.add(record, "zip", f"{path.name}::{name}", path.stem)


def source_label(sources):
    # e.g. "out", "json+zip", "out;json;json+zip" (a ZIP record is a JSON inside a ZIP)
    return ";".join(SOURCE_LABELS[s] for s in SOURCE_ORDER if s in sources)


def t2i_status(t2i):
    if t2i is None:
        return "missing"
    return "nonzero" if t2i > 0 else "zero"


def describe(values):
    if not values:
        return {"mean": "", "median": "", "std": "", "min": "", "max": ""}
    return {
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(col, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    models = sorted(col.models.values(), key=lambda r: (r["batch"], r["uuid"]))

    # uuid+seed pairs used in more than one batch
    pair_batches = defaultdict(list)
    for r in models:
        pair_batches[(r["uuid"], r["seed"])].append(r)
    shared = {k: v for k, v in pair_batches.items() if len(v) > 1}

    # per_model_metrics.csv
    rows = []
    for r in models:
        status = t2i_status(r["time_t2i"])
        others = [o["batch"] for o in pair_batches[(r["uuid"], r["seed"])] if o is not r]
        total = ""
        if status == "nonzero" and r["time_shape"] is not None:
            total = round(r["time_t2i"] + r["time_shape"], 4)
        rows.append({
            "batch": r["batch"],
            "uuid": r["uuid"],
            "seed": r["seed"],
            "source": source_label(r["sources"]),
            "t2i_status": status,
            "time_t2i": "" if r["time_t2i"] is None else r["time_t2i"],
            "time_shape": "" if r["time_shape"] is None else r["time_shape"],
            "time_total": total,
            "seed_shared_with": ";".join(others),
        })
    write_csv(out_dir / "per_model_metrics.csv", rows, list(rows[0].keys()) if rows else ["batch"])

    # per_eval_metrics.csv
    write_csv(out_dir / "per_eval_metrics.csv", col.evals,
              ["batch", "uuid", "eval_file", "CLIP", "BER", "is_watertight"])

    # seed_reuse.csv: one row per reused pair, timings of each batch side by side
    reuse_rows = []
    for (uuid, seed), recs in sorted(shared.items()):
        recs = sorted(recs, key=lambda r: r["batch"])
        reuse_rows.append({
            "uuid": uuid,
            "seed": seed,
            "n_batches": len(recs),
            "batches": ";".join(r["batch"] for r in recs),
            "time_t2i": ";".join("" if r["time_t2i"] is None else str(r["time_t2i"]) for r in recs),
            "time_shape": ";".join("" if r["time_shape"] is None else str(r["time_shape"]) for r in recs),
        })
    write_csv(out_dir / "seed_reuse.csv", reuse_rows,
              ["uuid", "seed", "n_batches", "batches", "time_t2i", "time_shape"])

    # run_summary.csv: time_shape and time_t2i (non-zero only) aggregated separately
    by_batch = defaultdict(list)
    for r in models:
        by_batch[r["batch"]].append(r)
    summary = []
    for batch, recs in sorted(by_batch.items()):
        shape = [r["time_shape"] for r in recs if r["time_shape"] is not None]
        t2i = [r["time_t2i"] for r in recs if t2i_status(r["time_t2i"]) == "nonzero"]
        shared_recs = [r for r in recs if (r["uuid"], r["seed"]) in shared]
        shared_with = sorted({o["batch"] for r in shared_recs
                              for o in shared[(r["uuid"], r["seed"])] if o["batch"] != batch})
        row = {
            "batch": batch,
            "n": len(recs),
            "n_t2i_nonzero": len(t2i),
            "n_t2i_zero": sum(t2i_status(r["time_t2i"]) == "zero" for r in recs),
            "n_t2i_missing": sum(r["time_t2i"] is None for r in recs),
        }
        row.update({f"time_shape_{k}": v for k, v in describe(shape).items()})
        row.update({f"time_t2i_{k}": v for k, v in describe(t2i).items()})
        row["n_seed_shared"] = len(shared_recs)
        row["seed_shared_with"] = ";".join(shared_with)
        row["sources"] = " | ".join(sorted({source_label(r["sources"]) for r in recs}))
        summary.append(row)
    write_csv(out_dir / "run_summary.csv", summary, list(summary[0].keys()) if summary else ["batch"])

    # t2i_time_non_zero.log / t2i_time_zero.log: source files grouped by batch
    for status, fname in (("nonzero", "t2i_time_non_zero.log"), ("zero", "t2i_time_zero.log")):
        files = defaultdict(lambda: defaultdict(int))
        for r in models:
            if t2i_status(r["time_t2i"]) != status:
                continue
            for loc in r["locations"]:
                # Collapse per-model JSONs to their folder / archive
                if loc.endswith(".json"):
                    loc = loc.rsplit("/", 1)[0] if "::" in loc else str(Path(loc).parent) + "\\*.json"
                files[r["batch"]][loc] += 1
        with open(out_dir / fname, "w", encoding="utf-8") as f:
            for batch in sorted(files):
                f.write(f"[{batch}]\n")
                for loc, n in sorted(files[batch].items()):
                    f.write(f"  {loc}  ({n} records)\n")

    missing = [r for r in models if r["time_t2i"] is None]
    if missing:
        with open(out_dir / "t2i_time_missing.log", "w", encoding="utf-8") as f:
            for r in missing:
                f.write(f"{r['batch']} {r['uuid']}  {r['locations'][0]}\n")

    conflicts_path = out_dir / "conflicts.log"
    if col.conflicts:
        conflicts_path.write_text("\n".join(col.conflicts) + "\n", encoding="utf-8")
    elif conflicts_path.exists():
        conflicts_path.unlink()

    return summary, len(shared)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip-dir", type=Path, default=DEFAULT_ZIP_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    col = Collector()
    # Order matters: .out first, then local JSON, then ZIP
    for path in sorted(SEARCH_DIR.rglob("*.out")):
        col.read_out(path)
    for path in sorted(SEARCH_DIR.rglob("*.json")):
        if MODEL_JSON_RE.search(path.name):
            col.read_local_json(path)
    if args.zip_dir.is_dir():
        for path in sorted(args.zip_dir.glob("*.zip")):
            col.read_zip(path)
    else:
        print(f"ZIP dir not found, skipped: {args.zip_dir}")

    summary, n_shared = write_outputs(col, args.out_dir)

    print(f"\n{len(col.models)} models, {len(col.evals)} evaluation rows, "
          f"{n_shared} uuid+seed pairs shared between batches, {len(col.conflicts)} conflicts")
    for row in summary:
        print(f"  {row['batch']:<55} n={row['n']:<4} t2i>0={row['n_t2i_nonzero']:<4} "
              f"shape_mean={row['time_shape_mean']:<8} t2i_mean={row['time_t2i_mean']:<8} "
              f"sources={row['sources']}")
    print(f"Output: {args.out_dir}")


if __name__ == "__main__":
    main()
