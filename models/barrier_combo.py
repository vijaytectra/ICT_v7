"""Do the barrier lifts STACK?

Seven single conditions lift p(+2R before -1R) by more than 3pp in both periods.  The
best single lift is about +6pp; PF 2.0 needs +16.7pp.  So the only remaining route is
whether the lifts combine.

They will only stack if they are picking up different things.  If they are all proxies
for the same underlying property, the combination adds nothing and just shrinks the
sample - which is what over-filtering looks like from the inside.

So: measure the pairwise overlap first, then every combination, and require the lift to
appear in BOTH periods with a usable trade count.  A combination that only survives on
one side is the LR3 signature this project has already been burned by twice today.
"""
import itertools
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L

pd.set_option("display.width", 220)
K = 2.0
BASE = 1.0 / (1.0 + K)

C = {
    "POS": ("entry_pos <= 0.15", lambda d: d.entry_pos <= 0.15),
    "RR25": ("rr_pool >= 2.5", lambda d: d.rr_pool >= 2.5),
    "RR40": ("rr_pool >= 4.0", lambda d: d.rr_pool >= 4.0),
    "SHORT": ("shorts only", lambda d: d.side == -1),
    "RATR": ("R <= 0.6 ATR", lambda d: d.R_atr <= 0.6),
    "NOBIAS": ("bias disagrees", lambda d: d.bias_agree == 0),
}


def mask(d, keys):
    m = pd.Series(True, index=d.index)
    for k in keys:
        m &= C[k][1](d).fillna(False)
    return m


def score(d, keys, floor):
    g = d[mask(d, keys)]
    if len(g) < floor:
        return None
    p = float(g.win.mean())
    return len(g), p


if __name__ == "__main__":
    f = lambda x: f"{x:.3f}"
    dev = pd.read_csv(r"C:\personal\ICT_v7\reports\barrier_dev.csv", parse_dates=["t"])
    val = pd.read_csv(r"C:\personal\ICT_v7\reports\barrier_val.csv", parse_dates=["t"])
    print(f"DEV n={len(dev)} p={dev.win.mean()*100:.1f}%   "
          f"VAL n={len(val)} p={val.win.mean()*100:.1f}%   base {BASE*100:.1f}%   "
          f"PF2 needs 50.0%\n")

    print("=" * 96)
    print("OVERLAP — are these conditions independent, or the same thing twice?")
    print("=" * 96)
    M = pd.DataFrame({k: mask(dev, [k]).astype(int) for k in C})
    print(M.corr().to_string(float_format=f))

    print("\n" + "=" * 118)
    print("EVERY COMBINATION, both periods.  DEV floor 40 trades, VAL floor 25.")
    print("=" * 118)
    rows = []
    for r in range(1, len(C) + 1):
        for keys in itertools.combinations(C, r):
            a = score(dev, keys, 40)
            b = score(val, keys, 25)
            if not a or not b:
                continue
            rows.append(dict(combo="+".join(keys),
                             dev_n=a[0], dev_p=a[1] * 100,
                             val_n=b[0], val_p=b[1] * 100,
                             dev_lift=(a[1] - BASE) * 100,
                             val_lift=(b[1] - BASE) * 100,
                             dev_pf=(a[1] * K) / max(1 - a[1], 1e-9),
                             val_pf=(b[1] * K) / max(1 - b[1], 1e-9),
                             worst_p=min(a[1], b[1]) * 100))
    t = pd.DataFrame(rows).sort_values("worst_p", ascending=False)
    t.to_csv(r"C:\personal\ICT_v7\reports\barrier_combo.csv", index=False)
    print(t.head(25).to_string(index=False, float_format=f))

    print(f"\n  combinations reaching p >= 50% in BOTH periods: "
          f"{int(((t.dev_p >= 50) & (t.val_p >= 50)).sum())} of {len(t)}")
    print(f"  combinations reaching p >= 45% in BOTH:          "
          f"{int(((t.dev_p >= 45) & (t.val_p >= 45)).sum())}")
    print(f"  combinations reaching p >= 40% in BOTH:          "
          f"{int(((t.dev_p >= 40) & (t.val_p >= 40)).sum())}")
    best = t.iloc[0]
    print(f"\n  best by worst-period p: {best.combo}")
    print(f"    DEV {best.dev_n:.0f} trades at {best.dev_p:.1f}%  "
          f"VAL {best.val_n:.0f} at {best.val_p:.1f}%")
