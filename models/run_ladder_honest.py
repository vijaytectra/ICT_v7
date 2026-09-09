"""The partial-exit study, re-run with the break-even stop actually simulated.

WHY THIS FILE EXISTS
--------------------
run_ladder.py answered "can the loss rate reach 20-30%" with a ladder that had a hole in
it: a break-even stop was applied to LOSERS (turning -1R into 0) but never to WINNERS.
In reality a stop moved to entry fires on any trade that comes back to entry, including
trades that would later have reached the target.  Rescuing every loser while keeping
every winner is not an exit rule, it is an accounting error, and it is the same class of
error as the four already found in ict_bt.py.

fx_lab.run_fixed now records, for each arming level x, whether price returned to the
entry after first printing +x R (`be_{x}`).  Same-bar ambiguity resolves against the
trade.  This file re-asks the question using that field.

POLICIES
--------
  partial only   book `frac` at +x R, the remainder runs to the original stop/target.
                 No ambiguity: the remainder's outcome is the one already simulated.
  partial + BE   book `frac` at +x R and move the stop to entry.  The remainder exits at
                 0 whenever `be_{x}` is true - whether the trade was going to win or lose.

Every number is reported DEV / VAL on the same 60/40 chronological split as the rest of
the project, with a bootstrap P(mean > 0) on VAL.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F

rng = np.random.default_rng(7)


def gross(t):
    """Outcome of the untouched position in R, before costs."""
    return np.where(t.out.values == 1, t.rr.values,
                    np.where(t.out.values == -1, -1.0, 0.0))


def ladder(t, x, frac, breakeven):
    """Net R per trade under 'book `frac` at +x R', with or without the BE stop."""
    g = gross(t)
    reached = (t.mfe_r.values >= x)
    if breakeven:
        col = f"be_{x}"
        if col not in t.columns:
            raise KeyError(f"{col} not recorded - add {x} to fx_lab.BE_LEVELS")
        stopped = t[col].values
        rest = np.where(stopped, 0.0, g)
    else:
        rest = g
    out = np.where(reached, frac * x + (1 - frac) * rest, g)
    return out - t.cost_r.values


def boot(v, reps=20000):
    m = rng.choice(v, size=(reps, len(v)), replace=True).mean(axis=1)
    return float((m > 0).mean())


def row(name, v, dm):
    d, w = v[dm], v[~dm]
    return (f"{name:30} | {(d < 0).mean():8.1%} {F.pf(pd.Series(d)):6.3f} {d.sum():+7.1f} | "
            f"{(w < 0).mean():8.1%} {F.pf(pd.Series(w)):6.3f} {w.sum():+7.1f} | {boot(w):9.1%}")


for label, syms in (("3 INDICES", F.IDX), ("ALL 9", F.FX + F.IDX)):
    t = F.book(syms, fill_bar_stop=False).sort_values("t").reset_index(drop=True)
    dm = (t.t <= t.t.quantile(0.6)).values

    # ---- consistency check: a loser that reached +x MUST have returned to entry -------
    bad = 0
    for x in F.BE_LEVELS:
        m = (t.out == -1) & (t.mfe_r >= x) & (~t[f"be_{x}"])
        bad += int(m.sum())
    print("=" * 118)
    print(f"{label}   n={len(t)}   DEV={int(dm.sum())} VAL={int((~dm).sum())}   "
          f"impossible rows (loser reached +xR without revisiting entry): {bad}")
    print("=" * 118)

    # ---- how often the break-even stop actually fires ---------------------------------
    print("break-even stop firing rate, by arming level:")
    for x in F.BE_LEVELS:
        reached = t.mfe_r >= x
        if reached.sum() == 0:
            continue
        fired = t.loc[reached, f"be_{x}"]
        wins_killed = t.loc[reached & t[f"be_{x}"] & (t.out == 1)]
        print(f"   arm at +{x:.2f}R : {reached.mean():5.1%} of trades reach it, "
              f"{fired.mean():5.1%} of those come back to entry, "
              f"{len(wins_killed):3} WINNERS killed by the stop")
    print()

    print(f"{'policy':30} | {'DEVloss%':>8} {'DEVpf':>6} {'DEVR':>7} | "
          f"{'VALloss%':>8} {'VALpf':>6} {'VALR':>7} | {'P(edge>0)':>9}")
    print("-" * 118)
    base = t.netR.values
    print(row("locked exit (no partial)", base, dm))
    for x, frac in ((0.5, 0.5), (0.75, 0.5), (1.0, 0.5), (1.0, 0.75), (1.5, 0.5)):
        print(row(f"take {frac:.0%} @+{x:.2f}R, rest runs", ladder(t, x, frac, False), dm))
    for x, frac in ((0.5, 0.5), (0.75, 0.5), (1.0, 0.5), (1.0, 0.75), (1.5, 0.5)):
        print(row(f"take {frac:.0%} @+{x:.2f}R + BE", ladder(t, x, frac, True), dm))
    print()
