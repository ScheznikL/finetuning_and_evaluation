"""
Scale-sensitivity analysis for unnormalised Hunyuan3D outputs.

Answers: does the generated size depend on the size requested in the prompt?
  - Pearson r and regression slope (generated length vs requested length)
  - Coefficient of variation of requested vs generated length
  - Paired test: is the baseline vs modified error difference significant?

Usage
  1) Inspect the JSON structure first:
       python scale_sensitivity.py --inspect detailed_results.json
  2) Edit the three getter functions below to match your field names.
  3) Run for one model:
       python scale_sensitivity.py --modified modified/detailed_results.json
     or for both (adds the paired test):
       python scale_sensitivity.py --baseline base/detailed_results.json \
                                   --modified modified/detailed_results.json

Requires: numpy, scipy (matplotlib optional, for the scatter plot)
"""
import argparse
import json
import sys

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# EDIT THESE THREE FUNCTIONS to match your detailed_results.json fields.
# ---------------------------------------------------------------------------
def get_id(rec):
    """Unique key used to pair baseline and modified results (prompt id / index)."""
    return rec.get("id", rec.get("prompt_id", rec.get("name")))


def get_requested_length(rec):
    """Requested total length in mm, from the prompt."""
    return float(rec["prompt"]["total_length"])


def get_generated_length(rec):
    """Generated longest side, as reported by measure_batch.py (units*1000).
    Uses the largest bounding-box extent; change if you store 'length' directly."""
    return float(max(rec["extents"]))
# ---------------------------------------------------------------------------


def load_records(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # common wrappers: {"results": [...]} or {id: record, ...}
        for key in ("results", "records", "items", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return [dict(v, id=k) if isinstance(v, dict) else v for k, v in data.items()]
    return data


def inspect(path):
    recs = load_records(path)
    print(f"{len(recs)} records. First record:\n")
    print(json.dumps(recs[0], indent=2, ensure_ascii=False)[:3000])
    normalized = {r.get("normalized") for r in recs if isinstance(r, dict)}
    print(f"\n'normalized' values found: {normalized}")


def analyse(path, label):
    recs = load_records(path)
    ids, req, gen = [], [], []
    for r in recs:
        try:
            ids.append(get_id(r))
            req.append(get_requested_length(r))
            gen.append(get_generated_length(r))
        except (KeyError, TypeError, ValueError) as e:
            print(f"[{label}] skipped a record: {e!r}", file=sys.stderr)
    req, gen = np.array(req), np.array(gen)
    n = len(req)

    pr = stats.pearsonr(req, gen)
    r_ci = pr.confidence_interval(0.95)
    lr = stats.linregress(req, gen)
    t_crit = stats.t.ppf(0.975, n - 2)
    slope_ci = (lr.slope - t_crit * lr.stderr, lr.slope + t_crit * lr.stderr)
    sp = stats.spearmanr(req, gen)

    cv_req = req.std(ddof=1) / req.mean() * 100
    cv_gen = gen.std(ddof=1) / gen.mean() * 100
    abs_err = np.abs(gen - req)

    print(f"\n=== {label}  (n = {n}) ===")
    print(f"Requested length  : min {req.min():.1f}  median {np.median(req):.1f}  "
          f"max {req.max():.1f} mm   CV {cv_req:.2f}%")
    print(f"Generated length  : min {gen.min():.1f}  median {np.median(gen):.1f}  "
          f"max {gen.max():.1f} (reported mm)   CV {cv_gen:.2f}%")
    print(f"Pearson r         : {pr.statistic:.3f}  95% CI [{r_ci.low:.3f}, {r_ci.high:.3f}]  "
          f"p = {pr.pvalue:.3g}")
    print(f"Spearman rho      : {sp.statistic:.3f}  p = {sp.pvalue:.3g}")
    print(f"Slope             : {lr.slope:.4f}  95% CI [{slope_ci[0]:.4f}, {slope_ci[1]:.4f}]"
          f"   (1 = follows prompt, 0 = ignores it)")
    print(f"Intercept         : {lr.intercept:.1f}   R^2 = {lr.rvalue**2:.4f}")
    print(f"Length abs. error : mean {abs_err.mean():.1f}  std {abs_err.std(ddof=1):.1f} mm")

    return dict(zip(ids, abs_err)), req, gen


def paired_test(err_a, err_b):
    common = sorted(set(err_a) & set(err_b), key=str)
    a = np.array([err_a[k] for k in common])
    b = np.array([err_b[k] for k in common])
    d = a - b
    t = stats.ttest_rel(a, b)
    w = stats.wilcoxon(a, b) if np.any(d != 0) else None
    print(f"\n=== Paired comparison (baseline - modified), n = {len(common)} pairs ===")
    print(f"Mean difference   : {d.mean():.2f} mm  (std {d.std(ddof=1):.2f})")
    print(f"Paired t-test     : t = {t.statistic:.3f}  p = {t.pvalue:.3g}")
    if w is not None:
        print(f"Wilcoxon          : W = {w.statistic:.1f}  p = {w.pvalue:.3g}")


def plot(results, out="scale_sensitivity.png"):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 5))
    lo = min(r[1].min() for r in results.values())
    hi = max(r[2].max() for r in results.values())
    for label, (_, req, gen) in results.items():
        ax.scatter(req, gen, s=14, alpha=0.7, label=label)
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="ideal (generated = requested)")
    ax.set_xlabel("Requested total length, mm")
    ax.set_ylabel("Generated longest side (unnormalised, reported mm)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"\nScatter plot saved to {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inspect")
    p.add_argument("--baseline")
    p.add_argument("--modified")
    args = p.parse_args()

    if args.inspect:
        inspect(args.inspect)
        return

    results = {}
    if args.baseline:
        results["Hunyuan3D 2.0"] = analyse(args.baseline, "Hunyuan3D 2.0")
    if args.modified:
        results["Modified model"] = analyse(args.modified, "Modified model")
    if not results:
        p.error("give --inspect, --baseline and/or --modified")
    if len(results) == 2:
        paired_test(results["Hunyuan3D 2.0"][0], results["Modified model"][0])
    plot(results)


if __name__ == "__main__":
    main()
