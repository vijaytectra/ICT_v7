"""Dynamic draw-on-liquidity target vs a flat R multiple — the clean comparison.

The mutation in the lock verification (`target="fixed"`, PF 0.944) is NOT a fair test:
switching to a fixed R also bypasses the min_rr/max_rr gate, so it trades a different
population (1546 setups instead of 471).  It answers "what if we removed the gate too",
not "what if we exited at 3R".

Here the SETUP POPULATION IS HELD FIXED — the same 471 trades the locked model takes,
selected by the same DOL gate — and only the exit is moved:

  A  dynamic   take the pool  (the locked model)
  B  flat kR   ignore the pool, exit at k x risk
  C  capped    take the pool but never plan beyond kR

Nothing here changes the locked config: `exit_rr` and `cap_rr` default to None.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L

f = lambda x: f"{x:.3f}"


def row(t, label):
    if t is None or len(t) == 0:
        return None
    v = t.netR.values
    eq = t.netR.cumsum()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0
        mx = max(mx, s)
    p, ci = L.bootstrap(v)
    i, o = t[t.t < L.IS_END], t[t.t >= L.IS_END]
    return dict(exit=label, n=len(t), WR=float((t.out == 1).mean()),
                ER=float(v.mean()), PF=L.pf(v), totR=float(v.sum()),
                maxDD=float((eq - eq.cummax()).min()),
                RdD=float(v.sum() / abs((eq - eq.cummax()).min())),
                streak=mx, avg_rr=float(t.rr.mean()),
                med_hold=int(t.bars.median()),
                is_PF=L.pf(i.netR.values), oos_PF=L.pf(o.netR.values), P_edge=p)


if __name__ == "__main__":
    base = L.portfolio()
    print("=" * 108)
    print("SAME 471 SETUPS, ONLY THE EXIT MOVES   (arm A, both sides, cost charged)")
    print("=" * 108)
    rows = [row(base, "DYNAMIC pool  (LOCKED)")]
    for k in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        rows.append(row(L.portfolio(exit_rr=k), f"flat {k}R"))
    for k in (3.0, 4.0, 5.0):
        rows.append(row(L.portfolio(cap_rr=k), f"pool capped at {k}R"))
    r = pd.DataFrame([x for x in rows if x])
    print(r.to_string(index=False, float_format=f))

    print("\n" + "=" * 108)
    print("ARM B, SHORTS ONLY — same question")
    print("=" * 108)
    rows = [row(L.portfolio(shorts_only=True), "DYNAMIC pool  (LOCKED)")]
    for k in (2.0, 3.0, 4.0):
        rows.append(row(L.portfolio(shorts_only=True, exit_rr=k), f"flat {k}R"))
    for k in (3.0, 4.0):
        rows.append(row(L.portfolio(shorts_only=True, cap_rr=k), f"pool capped at {k}R"))
    print(pd.DataFrame([x for x in rows if x]).to_string(index=False, float_format=f))

    print("\n" + "=" * 108)
    print("WHERE THE DYNAMIC TARGET ACTUALLY SITS  (locked trades)")
    print("=" * 108)
    q = base.rr.describe(percentiles=[.1, .25, .5, .75, .9])
    print("  planned R:R distribution")
    print("   " + "  ".join(f"{k} {v:.2f}" for k, v in q.items() if k != "count"))
    print(f"\n  {'planned R:R band':<20}{'n':>5}{'WR':>8}{'ER':>9}{'PF':>8}{'totR':>9}")
    bins = [2, 2.5, 3, 4, 5, 7, 10]
    b = base.copy()
    b["band"] = pd.cut(b.rr, bins)
    for k, g in b.groupby("band", observed=True):
        print(f"  {str(k):<20}{len(g):>5}{(g.out==1).mean():>8.3f}"
              f"{g.netR.mean():>+9.3f}{L.pf(g.netR.values):>8.3f}{g.netR.sum():>+9.1f}")
