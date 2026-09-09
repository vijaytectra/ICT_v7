"""Score every candidate feature the way the reachability gate was scored.

The danger with a 19-feature scan is obvious: at p<0.05 roughly one feature will look
significant by chance alone. So the bar here is deliberately brutal.

  1. Everything is selected on DEV. VAL is not looked at until a feature has already
     survived DEV.
  2. Each feature is tested in BOTH directions (high is good / low is good), because
     choosing the direction after seeing the data is itself a test. That makes 2 x 19 = 38
     tests, so the Bonferroni threshold is 0.05/38 = 0.0013.
  3. The test is a PERMUTATION on the trade list, not a t-test: does keeping the top half
     by this feature beat keeping a random half of the same size? That is the question that
     separates "this selects good trades" from "this just takes fewer trades", and it is
     the test every previously rejected filter failed at around p = 0.25.
  4. A survivor must also be MONOTONE across quartiles. A single good bucket in the middle
     is a fluke; a gradient is a mechanism.
"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

SKIP = {"t", "exit_t", "side", "res", "netR", "win", "bars", "sym", "rr", "R_pips",
        "out", "pool", "_bar", "_sweep_bar", "_fill_i", "_px", "med_stop", "planned"}


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


def perm_p(t, mask, iters=20000, seed=7):
    """P(a random subset of the same size does at least as well)."""
    v = t.netR.values; k = int(mask.sum())
    if k < 25 or k > len(v) - 25: return np.nan
    obs = v[mask.values].mean()
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(iters):
        if rng.permutation(v)[:k].mean() >= obs: hits += 1
    return hits / iters


def evaluate(D, feats=None, min_frac=0.30):
    feats = feats or [c for c in D.columns if c not in SKIP and D[c].dtype.kind in "fiu"]
    rows = []
    for f in feats:
        x = D[f]
        if x.notna().sum() < 100 or x.nunique() < 3: continue
        rho, _ = spearmanr(x, D.netR, nan_policy="omit")
        med = x.median()
        for direction, mask in (("high", x > med), ("low", x <= med)):
            mask = mask.fillna(False)
            if mask.mean() < min_frac or mask.mean() > 1 - min_frac: continue
            sub = D[mask]
            rows.append(dict(feature=f, dir=direction, n=len(sub),
                             PF=pf(sub.netR), ER=sub.netR.mean(), base=pf(D.netR),
                             rho=rho, p=perm_p(D, mask)))
    r = pd.DataFrame(rows).sort_values("p")
    r["bonferroni"] = 0.05 / max(len(r), 1)
    return r


def quartiles(D, f):
    x = D[f]
    q = pd.qcut(x.rank(method="first"), 4, labels=False)
    out = []
    for k in range(4):
        s = D[q == k]
        if len(s) < 10: continue
        out.append((k + 1, x[q == k].min(), x[q == k].max(), len(s), pf(s.netR), s.netR.sum()))
    return out
