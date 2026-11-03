"""Paired bootstrap of the mean difference with BCa confidence intervals.

Makes no normality assumption, so it suits skewed per-sample metrics such as MAE.
Samples are paired by id (e.g. the same prompt uuid evaluated by two models).
"""
import argparse
import csv
from statistics import NormalDist

import numpy as np

_NORM = NormalDist()


def paired_bootstrap_bca(a, b, n_resamples=10_000, alpha=0.05, seed=0):
    """BCa bootstrap CI for mean(a - b), where a[i] and b[i] are paired."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("a and b must be 1-D arrays of equal length")
    d = a - b
    n = d.size
    if n < 2:
        raise ValueError("need at least 2 pairs")

    theta_hat = d.mean()

    # resample pairs (i.e. differences) with replacement
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    boot = d[idx].mean(axis=1)

    if np.ptp(d) == 0:
        # all differences identical: the interval collapses to a point
        return {"mean_diff": theta_hat, "ci_low": theta_hat, "ci_high": theta_hat,
                "p_value": 0.0 if theta_hat != 0 else 1.0, "n": n,
                "n_resamples": n_resamples, "z0": 0.0, "acceleration": 0.0,
                "boot": boot}

    # bias correction z0 (ties counted as half)
    prop = (np.sum(boot < theta_hat) + 0.5 * np.sum(boot == theta_hat)) / n_resamples
    prop = np.clip(prop, 1 / (n_resamples + 1), n_resamples / (n_resamples + 1))
    z0 = _NORM.inv_cdf(prop)

    # acceleration from the jackknife of the mean
    jack = (d.sum() - d) / (n - 1)
    dev = jack.mean() - jack
    denom = 6.0 * np.sum(dev ** 2) ** 1.5
    acc = np.sum(dev ** 3) / denom if denom > 0 else 0.0

    def adjusted_quantile(q):
        z = _NORM.inv_cdf(q)
        return _NORM.cdf(z0 + (z0 + z) / (1 - acc * (z0 + z)))

    q_low = adjusted_quantile(alpha / 2)
    q_high = adjusted_quantile(1 - alpha / 2)
    ci_low, ci_high = np.quantile(boot, [q_low, q_high])

    # two-sided bootstrap p-value for H0: mean difference == 0
    p_value = min(1.0, 2 * min(np.mean(boot <= 0), np.mean(boot >= 0)))

    return {"mean_diff": theta_hat, "ci_low": ci_low, "ci_high": ci_high,
            "p_value": p_value, "n": n, "n_resamples": n_resamples,
            "z0": z0, "acceleration": acc, "boot": boot}


def load_metric(path, metric, id_col="uuid"):
    with open(path, newline="") as f:
        return {row[id_col]: float(row[metric]) for row in csv.DictReader(f)
                if row.get(metric) not in (None, "", "nan")}


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, type=str, help="CSV for model A")
    parser.add_argument("--b", required=True, type=str, help="CSV for model B")
    parser.add_argument("--metric", required=True, type=str, help="column to compare, e.g. MAE")
    parser.add_argument("--id_col", default="uuid", type=str)
    parser.add_argument("--n_resamples", default=10_000, type=int)
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--seed", default=0, type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    a_vals = load_metric(args.a, args.metric, args.id_col)
    b_vals = load_metric(args.b, args.metric, args.id_col)
    common = sorted(a_vals.keys() & b_vals.keys())
    dropped = len(a_vals.keys() ^ b_vals.keys())

    res = paired_bootstrap_bca([a_vals[k] for k in common], [b_vals[k] for k in common],
                               n_resamples=args.n_resamples, alpha=args.alpha, seed=args.seed)

    level = int(round((1 - args.alpha) * 100))
    print(f"Metric: {args.metric}  (A - B, paired on {args.id_col})")
    print(f"Pairs: {res['n']}  (unpaired ids dropped: {dropped})")
    print(f"Mean difference: {res['mean_diff']:.6f}")
    print(f"{level}% BCa CI: [{res['ci_low']:.6f}, {res['ci_high']:.6f}]  "
          f"({res['n_resamples']} resamples)")
    print(f"Bootstrap p-value (H0: diff = 0): {res['p_value']:.4f}")
    print(f"z0 = {res['z0']:.4f}, acceleration = {res['acceleration']:.4f}")
