"""FX does not fail because the setup fails there.  It fails because the stop is too
tight relative to what the trade costs.

Across the nine instruments the rank order of cost/risk and the rank order of profit
factor are almost the same list.  The `cri_max = 0.20` gate - brodenbeck v4 Screen 2 -
is doing the right job but at the wrong threshold: 20% of risk is a tax no 30%-win-rate
model survives, and only FX ever gets near it.

Two knobs are swept together, because they push trade count in opposite directions:

  cri_max   tighter -> removes the expensive trades  (fewer trades, better quality)
  min_rr    2.0 -> 1.5 opens the draw-on-liquidity targets currently rejected for being
            between 1.5R and 2.0R away  (more trades)

1.5R is not a number chosen here; it is the floor the reach-curve work already
established and the floor the operator specified.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import itertools, numpy as np, pandas as pd
from models import asia_locked as L

pd.set_option("display.width", 220); f = lambda x: f"{x:.3f}"
IDX = L.INDICES


def stat(d, lab):
    if d is None or len(d) < 15:
        return dict(arm=lab, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = L.bootstrap(v)
    mo = (d.t.max() - d.t.min()).days / 30.4
    i, o = d[d.t < L.IS_END], d[d.t >= L.IS_END]
    return dict(arm=lab, n=len(v), per_wk=len(v) / (mo * 4.33),
                WR=float((d.out == 1).mean()), PF=L.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(),
                avg_rr=d.rr.mean(),
                is_PF=L.pf(i.netR.values) if len(i) else np.nan,
                oos_PF=L.pf(o.netR.values) if len(o) else np.nan,
                P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    print("=" * 150)
    print("cri_max x min_rr — all nine instruments")
    print("locked baseline: cri 0.20 / rr 2.0 -> n=268 WR 0.336 PF 1.539 +104.5R")
    print("=" * 150)
    rows = []
    for cri, mrr in itertools.product((0.20, 0.12, 0.08, 0.06, 0.04), (2.0, 1.5)):
        d = L.portfolio(cri_max=cri, min_rr=mrr)
        r = stat(d, f"cri {cri:.2f}  min_rr {mrr}")
        if r.get("n", 0) >= 15:
            fx = d[~d.sym.isin(IDX)]; ix = d[d.sym.isin(IDX)]
            r["fx_n"] = len(fx); r["fx_PF"] = L.pf(fx.netR.values) if len(fx) else np.nan
            r["fx_totR"] = fx.netR.sum()
            r["idx_n"] = len(ix); r["idx_PF"] = L.pf(ix.netR.values) if len(ix) else np.nan
            r["idx_totR"] = ix.netR.sum()
        rows.append(r)
    r = pd.DataFrame(rows)
    r.to_csv(r"C:\personal\ICT_v7\reports\cost_norm.csv", index=False)
    print(r.to_string(index=False, float_format=f))
