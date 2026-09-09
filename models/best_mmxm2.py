"""Deep dive on the top config of the MMXM v2 grid.

  detector : accumulation = Asian range, sweep of its bound, CISD reversal.
             ALL FOUR doctrinal gates OFF - no SMT, no contraction test, no Judas
             time window, no HTF bias.
  execution: limit at the order-block mean threshold, stop at the swept extreme,
             target the OPPOSITE accumulation bound (the engineered pool the cycle
             was built to reach), min R:R 1.0.

It is the only config in 144 that is positive on all three indices.  Everything
below decides whether that is an edge or a large sample of noise.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm2_lab, mmxm_bt

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
IDX, FX = mmxm2_lab.INDICES, mmxm2_lab.FX
DET = dict(n=5, target_mode="accum", max_hold_bars=60, require_smt=False,
           require_contraction=False, require_judas=False, require_bias=False)
EXE = dict(entry="mt", kz="ALL", target="pool", min_rr=1.0)
f = lambda x: f"{x:.3f}"


def go(syms, period=None, cost=None, **over):
    c = None if cost is None else {s: cost * (1.5 if s in IDX else 0.8) for s in syms}
    return mmxm2_lab.pooled(syms, DET, {**EXE, **over}, period=period, cost=c)


if __name__ == "__main__":
    print("=== PER INSTRUMENT, spread-only, full period ===\n")
    rows = []
    for s in IDX + FX:
        t = go([s])
        st = mmxm_bt.stats(t, s)
        if st:
            st["P_edge"], ci = mmxm_bt.bootstrap(t)
            st["ci_lo"], st["ci_hi"] = ci
            st["is_PF"] = mmxm2_lab.pf(go([s], "IS"))
            st["oos_PF"] = mmxm2_lab.pf(go([s], "OOS"))
            rows.append(st)
    p = pd.DataFrame(rows)
    print(p[["arm", "n", "wr", "ER", "PF", "totR", "maxDD", "lose_streak", "avg_rr",
             "med_risk", "med_hold", "is_PF", "oos_PF", "P_edge"]]
          .to_string(index=False, float_format=f))

    for nm, syms in (("US INDICES", IDX), ("SIX FX MAJORS", FX), ("ALL NINE", IDX + FX)):
        t = go(syms); i_t = go(syms, "IS"); o_t = go(syms, "OOS")
        st = mmxm_bt.stats(t, nm)
        pe, ci = mmxm_bt.bootstrap(t)
        eq = t.netR.cumsum()
        print(f"\n=== {nm} ===")
        print(f"  n {st['n']}   WR {st['wr']:.3f}   E[R] {st['ER']:+.4f}   "
              f"PF {st['PF']:.3f}   totR {st['totR']:+.1f}   maxDD {st['maxDD']:.1f}R")
        print(f"  IS PF {mmxm2_lab.pf(i_t):.3f} (n={len(i_t)})  ->  "
              f"OOS PF {mmxm2_lab.pf(o_t):.3f} (n={len(o_t)})   "
              f"decay {mmxm2_lab.pf(o_t)-mmxm2_lab.pf(i_t):+.3f}")
        print(f"  P(edge>0) {pe:.3f}   95% CI on E[R] [{ci[0]:+.4f}, {ci[1]:+.4f}]")
        print(f"  longest losing streak {st['lose_streak']}   "
              f"median hold {st['med_hold']} min   avg planned R:R {st['avg_rr']:.2f}")

    print("\n=== COST SENSITIVITY, indices (scale x 1.5 index points) ===")
    for cs in (0.0, 0.33, 0.67, 1.0, 1.33):
        t = go(IDX, cost=cs)
        print(f"  +{cs*1.5:.2f} pt : n {len(t):4d}  PF {mmxm2_lab.pf(t):.3f}  "
              f"totR {t.netR.sum():+7.1f}")

    print("\n=== QUARTERLY STABILITY, indices ===")
    t = go(IDX)
    q = t.set_index("t").netR.groupby(pd.Grouper(freq="QE")).agg(["size", "sum"])
    q["PF"] = t.set_index("t").netR.groupby(pd.Grouper(freq="QE")).apply(
        lambda v: (v[v > 0].sum() / -v[v < 0].sum()) if (v < 0).any() else np.nan)
    print(q.to_string(float_format=f))
    print(f"\n  positive quarters: {(q['sum']>0).sum()} of {len(q)}")
    v = t.netR.values
    o = np.argsort(-v)
    def pf_(x):
        g = x[x > 0].sum(); b = -x[x < 0].sum(); return g / b if b > 0 else np.inf
    print(f"  drop 5 best trades  -> PF {pf_(np.delete(v, o[:5])):.3f}")
    print(f"  drop 20 best trades -> PF {pf_(np.delete(v, o[:20])):.3f}")
    print(f"  top 5 trades = {v[o[:5]].sum()/v[v>0].sum()*100:.1f}% of gross profit")
    t.to_csv(REP / "mmxm2_best_trades.csv", index=False)
