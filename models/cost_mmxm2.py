"""The decisive test for the MMXM v2 result: does it survive real cost?

Median risk on the FX pairs is 5-8 pips.  At that size a 0.7-pip commission is
10-14% of risk, which is exactly the artefact brodenbeck v4 Screen 2 exists to catch
(sub-pip stops make cost dominate and manufacture a fake profit factor).  A result
that dies at 0.5 pip is not tradeable, whatever the spread-only number says.

Also run: the structural risk floor, quarterly stability, per-pair IS/OOS, and the
same sweep with the floor applied so the two effects can be separated.
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


def go(syms, period=None, pip_cost=0.0, floor=None, **over):
    c = {s: (pip_cost * (1.5 if s in IDX else 1.0)) for s in syms}
    e = {**EXE, **over}
    if floor is not None:
        e["max_cost_frac"] = floor
    return mmxm2_lab.pooled(syms, DET, e, period=period, cost=c)


if __name__ == "__main__":
    print("=== COST SENSITIVITY, six FX majors (pips on top of the real spread) ===\n")
    print(f"{'cost':>6} {'n':>6} {'WR':>7} {'PF':>7} {'totR':>9} {'IS PF':>7} "
          f"{'OOS PF':>7} {'P(edge)':>8}")
    for c in (0.0, 0.2, 0.4, 0.5, 0.7, 1.0, 1.5):
        t = go(FX, pip_cost=c)
        i_t = go(FX, "IS", pip_cost=c); o_t = go(FX, "OOS", pip_cost=c)
        pe, _ = mmxm_bt.bootstrap(t)
        print(f"{c:>6.1f} {len(t):>6d} {(t.netR>0).mean():>7.3f} "
              f"{mmxm2_lab.pf(t):>7.3f} {t.netR.sum():>+9.1f} "
              f"{mmxm2_lab.pf(i_t):>7.3f} {mmxm2_lab.pf(o_t):>7.3f} {pe:>8.3f}")

    print("\n=== WITH brodenbeck v4 Screen 2 RISK FLOOR (cost/risk <= 20%), FX ===\n")
    print(f"{'cost':>6} {'n':>6} {'WR':>7} {'PF':>7} {'totR':>9} {'IS PF':>7} "
          f"{'OOS PF':>7} {'medRisk':>8}")
    for c in (0.2, 0.4, 0.7, 1.0, 1.5):
        t = go(FX, pip_cost=c, floor=0.20)
        i_t = go(FX, "IS", pip_cost=c, floor=0.20)
        o_t = go(FX, "OOS", pip_cost=c, floor=0.20)
        if not len(t):
            continue
        print(f"{c:>6.1f} {len(t):>6d} {(t.netR>0).mean():>7.3f} "
              f"{mmxm2_lab.pf(t):>7.3f} {t.netR.sum():>+9.1f} "
              f"{mmxm2_lab.pf(i_t):>7.3f} {mmxm2_lab.pf(o_t):>7.3f} "
              f"{t.R_units.median():>8.2f}")

    print("\n=== RISK COHORTS at 0.7 pip - where does the profit actually sit? ===\n")
    t = go(FX, pip_cost=0.7)
    bins = [0, 3, 5, 8, 12, 20, 1e9]
    lab = ["<3p", "3-5p", "5-8p", "8-12p", "12-20p", ">20p"]
    t = t.copy(); t["coh"] = pd.cut(t.R_units, bins, labels=lab)
    g = t.groupby("coh", observed=True).agg(
        n=("netR", "size"), WR=("netR", lambda v: (v > 0).mean()),
        ER=("netR", "mean"), totR=("netR", "sum"),
        PF=("netR", lambda v: v[v > 0].sum() / max(-v[v < 0].sum(), 1e-9)))
    print(g.to_string(float_format=f))

    print("\n=== PER PAIR at 0.7 pip ===\n")
    rows = []
    for s in FX:
        a = go([s], pip_cost=0.7)
        if not len(a):
            continue
        pe, ci = mmxm_bt.bootstrap(a)
        rows.append(dict(pair=s, n=len(a), WR=float((a.netR > 0).mean()),
                         PF=mmxm2_lab.pf(a), totR=float(a.netR.sum()),
                         is_PF=mmxm2_lab.pf(go([s], "IS", pip_cost=0.7)),
                         oos_PF=mmxm2_lab.pf(go([s], "OOS", pip_cost=0.7)),
                         P_edge=pe, med_risk=float(a.R_units.median())))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n=== QUARTERLY, FX at 0.7 pip ===\n")
    a = go(FX, pip_cost=0.7).set_index("t")
    q = a.netR.groupby(pd.Grouper(freq="QE")).agg(["size", "sum"])
    q["PF"] = a.netR.groupby(pd.Grouper(freq="QE")).apply(
        lambda v: (v[v > 0].sum() / -v[v < 0].sum()) if (v < 0).any() else np.nan)
    print(q.to_string(float_format=f))
    print(f"\n  positive quarters {(q['sum']>0).sum()} of {len(q)}")
    v = a.netR.values; o = np.argsort(-v)
    pf_ = lambda x: x[x > 0].sum() / max(-x[x < 0].sum(), 1e-9)
    print(f"  drop 10 best -> PF {pf_(np.delete(v,o[:10])):.3f}   "
          f"drop 50 best -> PF {pf_(np.delete(v,o[:50])):.3f}")
    print(f"  top 10 trades = {v[o[:10]].sum()/v[v>0].sum()*100:.1f}% of gross profit")
