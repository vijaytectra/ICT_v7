"""How low can the loss rate actually go, and what does each step cost?

The request was a 20-30% loss rate instead of ~70%.  The break-even route is dead
(run_ladder_honest.py: the stop kills more winners than it saves losers).  What is left
is the partial-exit family, where the remainder runs to the original stop or target and
nothing has to be assumed about intrabar order.

THE CEILING IS NOT A MATTER OF TUNING
-------------------------------------
A trade that never reaches +x R cannot be rescued by any rule that acts at +x R.  So for
any arming level x:

    minimum possible loss rate  =  P(trade never reaches +x R and loses)

and that floor is reached only by booking the WHOLE position at +x R, which caps every
winner at x.  This file prints the floor beside the profit factor at each point on the
frontier, so the cost of each reduction in the loss rate is visible rather than asserted.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F

rng = np.random.default_rng(11)


def curve(t, x, frac):
    g = np.where(t.out.values == 1, t.rr.values,
                 np.where(t.out.values == -1, -1.0, 0.0))
    reached = t.mfe_r.values >= x
    return np.where(reached, frac * x + (1 - frac) * g, g) - t.cost_r.values


def boot(v, reps=20000):
    m = rng.choice(v, size=(reps, len(v)), replace=True).mean(axis=1)
    return float((m > 0).mean())


for label, syms in (("3 INDICES", F.IDX), ("ALL 9", F.FX + F.IDX)):
    t = F.book(syms, fill_bar_stop=False).sort_values("t").reset_index(drop=True)
    dm = (t.t <= t.t.quantile(0.6)).values
    base = t.netR.values
    print("=" * 116)
    print(f"{label}   n={len(t)}   baseline loss rate "
          f"DEV {(base[dm] < 0).mean():.1%} / VAL {(base[~dm] < 0).mean():.1%}   "
          f"baseline PF {F.pf(pd.Series(base[dm])):.3f} / {F.pf(pd.Series(base[~dm])):.3f}")
    print("=" * 116)
    print("the floor: no rule acting at +x R can help a trade that never reaches +x R")
    for x in (0.25, 0.5, 0.75, 1.0, 1.5):
        floor = float(((t.mfe_r.values < x) & (t.out.values == -1)).mean())
        print(f"   arm at +{x:.2f}R  ->  loss rate can never go below {floor:5.1%}")
    print()
    print(f"{'take frac @ +x R (rest runs)':30} | {'DEVloss%':>8} {'DEVpf':>6} {'DEVR':>7} | "
          f"{'VALloss%':>8} {'VALpf':>6} {'VALR':>7} | {'P(edge>0)':>9}")
    print("-" * 116)
    for x in (0.25, 0.5, 0.75, 1.0, 1.5):
        for frac in (0.75, 0.9, 1.0):
            v = curve(t, x, frac)
            d, w = v[dm], v[~dm]
            print(f"{f'take {frac:.0%} @ +{x:.2f}R':30} | {(d < 0).mean():8.1%} "
                  f"{F.pf(pd.Series(d)):6.3f} {d.sum():+7.1f} | {(w < 0).mean():8.1%} "
                  f"{F.pf(pd.Series(w)):6.3f} {w.sum():+7.1f} | {boot(w):9.1%}")
    print()
