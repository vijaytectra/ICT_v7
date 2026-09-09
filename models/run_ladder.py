"""Can the loss rate go from ~70% to 20-30%?  Measured, using each trade's real MFE.

A partial at +X R fills only on a trade that ACTUALLY reached +X R.  mfe_r is recorded on
the exit quote, before the barrier test, so it is the best price a resting limit could
have been filled at.  Entries, stops and targets are untouched; only the exit changes.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F


def apply_ladder(t, take_at, frac, breakeven=False):
    """Book `frac` of the position at +take_at R if the trade reached it.

    CORRECTED.  The first version of this function applied the break-even stop only to
    losing trades, so every loser was rescued to 0 while every winner still ran to its
    target.  That is not a break-even stop, it is a wish, and it invented the entire
    result it was asked to test.  A stop at entry fires on ANY trade that returns to the
    entry, winners included; `fx_lab.run_fixed` now records that per arming level in
    `be_{x}`, and this function uses it.  See run_ladder_honest.py for the re-run.
    """
    g = np.where(t.out.values == 1, t.rr.values,
                 np.where(t.out.values == -1, -1.0, 0.0))
    reached = t.mfe_r.values >= take_at
    if breakeven:
        col = f"be_{take_at}"
        if col not in t.columns:
            raise KeyError(f"{col} not recorded - add {take_at} to fx_lab.BE_LEVELS")
        rest = np.where(t[col].values, 0.0, g)
    else:
        rest = g
    return np.where(reached, frac * take_at + (1 - frac) * rest, g) - t.cost_r.values


for label, syms in (("ALL 9", F.FX + F.IDX), ("3 INDICES only", F.IDX)):
    t = F.book(syms, fill_bar_stop=False)
    base = t.netR.values
    print("=" * 104)
    print(f"{label}   n={len(t)}   MFE distribution of the LOSING trades:")
    ls = t[t.out == -1].mfe_r
    for x in (0.25, 0.5, 1.0, 1.5, 2.0):
        print(f"    losers that still reached +{x:.2f}R : {(ls >= x).mean():5.1%}  ({int((ls >= x).sum())} of {len(ls)})")
    print()
    print(f"{'exit policy':44} {'win%':>6} {'loss%':>7} {'PF':>7} {'totR':>8}")
    print("-" * 104)
    print(f"{'locked exit (no partial)':44} {(base > 0).mean():6.1%} {(base < 0).mean():7.1%} "
          f"{F.pf(pd.Series(base)):7.3f} {base.sum():+8.1f}")
    for be in (False, True):
        for take_at, frac in ((1.5, 0.5), (1.0, 0.5), (1.0, 0.75), (0.5, 0.5),
                              (0.5, 0.75), (0.25, 0.75)):
            v = apply_ladder(t, take_at, frac, breakeven=be)
            tag = f"take {frac:.0%} at +{take_at:.2f}R" + (" + BE on rest" if be else "")
            print(f"{tag:44} {(v > 0).mean():6.1%} {(v < 0).mean():7.1%} "
                  f"{F.pf(pd.Series(v)):7.3f} {v.sum():+8.1f}")
    print()
