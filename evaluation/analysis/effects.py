"""Main effects and interaction of two paired 2x2 designs, as mean differences with
95% BCa bootstrap CIs (10,000 resamples), computed on per-uuid contrast scores.

  A: model (INIT / CKPT8000) x prompt style (detailed / training), mm prompts
  B: model (INIT / CKPT8000) x unit (mm / cm), detailed prompts

Input is tables/per_sample.csv from raw_data/parse_raw_data.py.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from bootstrap import paired_bootstrap_bca

HERE = Path(__file__).resolve().parent
METRICS = ["CLIP", "is_watertight", "time_shape"]
DESCRIPTIVE = ["CLIP", "is_watertight", "time_shape", "time_t2i", "time_total"]

# name -> (factor column, fixed column, fixed value, level x (reference), level y)
ANALYSES = {
    "A: model x prompt style (mm)": ("prompt_style", "unit", "mm", "detailed", "training"),
    "B: model x unit (detailed)": ("unit", "prompt_style", "detailed", "mm", "cm"),
}


def load_cells(path):
    """(model, prompt_style, unit) -> metric -> {uuid: value}"""
    cells = defaultdict(lambda: defaultdict(dict))
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["model"], row["prompt_style"], row["unit"])
            for metric in DESCRIPTIVE + ["BER"]:
                if row[metric] != "":
                    cells[key][metric][row["uuid"]] = float(row[metric])
    return cells


def contrasts(ix, iy, cx, cy, x, y):
    """Per-uuid contrast scores; i/c = INIT/CKPT8000, x/y = factor levels."""
    return {
        "model (CKPT8000 - INIT)": ((cx + cy) - (ix + iy)) / 2,
        f"factor ({y} - {x})": ((iy + cy) - (ix + cx)) / 2,
        "interaction": (cy - iy) - (cx - ix),
        f"CKPT8000 - INIT within {x}": cx - ix,
        f"CKPT8000 - INIT within {y}": cy - iy,
    }


def holm(pvalues):
    order = np.argsort(pvalues)
    adjusted = np.empty(len(pvalues))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def fmt(v, digits=4):
    return "" if v is None else f"{v:.{digits}f}"


def fmt_p(p, n_resamples):
    # a bootstrap p-value cannot resolve below 1 / n_resamples
    if p is None:
        return ""
    return f"<{1 / n_resamples:.4g}" if p < 1 / n_resamples else f"{p:.4f}"


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(HERE / "tables" / "per_sample.csv"), type=str)
    parser.add_argument("--out_dir", default=str(HERE / "tables"), type=str)
    parser.add_argument("--n_resamples", default=10_000, type=int)
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--seed", default=0, type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    out_dir = Path(args.out_dir)
    cells = load_cells(args.data)
    level = int(round((1 - args.alpha) * 100))

    rows = []
    for analysis, (factor, fixed_col, fixed_val, x, y) in ANALYSES.items():
        def cell(model, lvl):
            key = {"prompt_style": None, "unit": None}
            key[factor], key[fixed_col] = lvl, fixed_val
            return cells[(model, key["prompt_style"], key["unit"])]

        names = {"ix": cell("INIT", x), "iy": cell("INIT", y), "cx": cell("CKPT8000", x), "cy": cell("CKPT8000", y)}
        for metric in METRICS:
            missing = [f"{m}/{lvl}" for (m, lvl), c in zip(
                [("INIT", x), ("INIT", y), ("CKPT8000", x), ("CKPT8000", y)], names.values())
                if not c[metric]]
            uuids = sorted(set.intersection(*(set(c[metric]) for c in names.values())))
            if missing or len(uuids) < 2:
                for name in contrasts(*[0] * 4, x, y):
                    rows.append({"analysis": analysis, "metric": metric, "effect": name,
                                 "note": f"n/a: no per-uuid {metric} for {', '.join(missing)}"})
                continue

            vecs = [np.array([c[metric][u] for u in uuids]) for c in names.values()]
            family = []
            for name, d in contrasts(*vecs, x, y).items():
                res = paired_bootstrap_bca(d, np.zeros_like(d), n_resamples=args.n_resamples,
                                           alpha=args.alpha, seed=args.seed)
                sd = d.std(ddof=1)
                row = {"analysis": analysis, "metric": metric, "effect": name,
                       "mean_diff": res["mean_diff"], "ci_low": res["ci_low"], "ci_high": res["ci_high"],
                       "d_z": res["mean_diff"] / sd if sd > 0 else None,
                       "p_boot": res["p_value"], "n": res["n"], "note": ""}
                rows.append(row)
                if "within" not in name:  # Holm over the two main effects and the interaction
                    family.append(row)
            for row, p in zip(family, holm([r["p_boot"] for r in family])):
                row["p_holm"] = p

    fields = ["analysis", "metric", "effect", "mean_diff", "ci_low", "ci_high", "d_z",
              "p_boot", "p_holm", "n", "note"]
    with open(out_dir / "effects.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # cell means (descriptive, including t2i / total time and BER)
    with open(out_dir / "cell_means.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "prompt_style", "unit", "metric", "n", "mean", "sd", "median", "n_nonzero"])
        for key in sorted(cells):
            for metric in DESCRIPTIVE + ["BER"]:
                v = np.array(list(cells[key][metric].values()))
                if v.size:
                    writer.writerow([*key, metric, v.size, fmt(v.mean()), fmt(v.std(ddof=1)),
                                     fmt(float(np.median(v))), int(np.count_nonzero(v))])

    with open(out_dir / "effects.md", "w", encoding="utf-8") as f:
        f.write(f"Paired mean differences, {level}% BCa bootstrap CI ({args.n_resamples:,} resamples, "
                f"seed {args.seed}).\nd_z = mean / sd of the per-uuid contrast. "
                f"p_holm: Holm over the two main effects and the interaction per analysis and metric.\n")
        for analysis in ANALYSES:
            for metric in METRICS:
                f.write(f"\n### {analysis}: {metric}\n\n| Effect | Δ | {level}% CI | d_z | p_boot | p_holm | n |\n"
                        "|---|---|---|---|---|---|---|\n")
                for r in rows:
                    if r["analysis"] != analysis or r["metric"] != metric:
                        continue
                    if r["note"]:
                        f.write(f"| {r['effect']} | {r['note']} | | | | | |\n")
                        continue
                    f.write(f"| {r['effect']} | {fmt(r['mean_diff'])} | [{fmt(r['ci_low'])}, {fmt(r['ci_high'])}] "
                            f"| {fmt(r['d_z'], 2)} | {fmt_p(r['p_boot'], args.n_resamples)} | {fmt_p(r.get('p_holm'), args.n_resamples)} | {r['n']} |\n")

    for r in rows:
        if r["note"]:
            print(f"{r['analysis'][:1]} {r['metric']:<14} {r['effect']:<28} {r['note']}")
        else:
            print(f"{r['analysis'][:1]} {r['metric']:<14} {r['effect']:<28} diff={r['mean_diff']:+.4f} "
                  f"[{r['ci_low']:+.4f}, {r['ci_high']:+.4f}] d_z={fmt(r['d_z'], 2):>5} p={r['p_boot']:.4f}")
    print(f"Output: {out_dir / 'effects.csv'}, effects.md, cell_means.csv")
