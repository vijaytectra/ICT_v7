"""Does the partial + break-even exit survive a DEV/VAL split, or is it in-sample fitting?

The locked project rejected all nineteen management rules (LOSS_FORENSICS.md), but that
was measured on the engine where shorts never paid the spread and the stop was skipped on
the fill bar.  With those corrected the ladder has to be re-asked, and re-asked HONESTLY:
a rule that only improves the pooled number is worth nothing.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F
from models.run_ladder import apply_ladder

rng = np.random.default_rng(1)


def boot_mean(v, reps=20000):
    m = rng.choice(v, size=(reps, len(v)), replace=True).mean(axis=1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5), float((m > 0).mean())


POLICIES = [("locked (no partial)", None, None, False),
            ("50% at +1.5R + BE", 1.5, 0.5, True),
            ("50% at +1.0R + BE", 1.0, 0.5, True),
            ("50% at +0.5R + BE", 0.5, 0.5, True),
            ("75% at +1.0R + BE", 1.0, 0.75, True),
            ("50% at +1.0R  no BE", 1.0, 0.5, False)]

for label, syms in (("3 INDICES", F.IDX), ("ALL 9", F.FX + F.IDX)):
    t = F.book(syms, fill_bar_stop=False).sort_values("t").reset_index(drop=True)
    d_idx = t.t <= t.t.quantile(0.6)
    print("=" * 112)
    print(f"{label}     DEV n={int(d_idx.sum())}   VAL n={int((~d_idx).sum())}")
    print("=" * 112)
    print(f"{'policy':24} | {'DEV loss%':>9} {'DEV PF':>7} {'DEV R':>7} | "
          f"{'VAL loss%':>9} {'VAL PF':>7} {'VAL R':>7} | {'VAL P(edge>0)':>13}")
    print("-" * 112)
    for name, take, frac, be in POLICIES:
        v = t.netR.values if take is None else apply_ladder(t, take, frac, breakeven=be)
        dv, vv = v[d_idx.values], v[~d_idx.values]
        _, _, p = boot_mean(vv)
        print(f"{name:24} | {(dv < 0).mean():9.1%} {F.pf(pd.Series(dv)):7.3f} {dv.sum():+7.1f} | "
              f"{(vv < 0).mean():9.1%} {F.pf(pd.Series(vv)):7.3f} {vv.sum():+7.1f} | {p:13.1%}")
    print()
