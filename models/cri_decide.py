"""Choosing cri_max properly instead of picking the best number on one period.

Three questions, in order:

  1  Does the effect survive the 2015-2023 index holdout - nine years the model has
     never been fitted on?  If it only exists in 2024-2026 it is a fitted threshold.
  2  Is it a REGION or a POINT?  A real threshold degrades smoothly on both sides.
  3  WHAT is it selecting?  cri_max = cost / risk, so tightening it selects trades with
     WIDER STOPS.  That could be two different mechanisms:
        (a) less cost drag on the same setups, or
        (b) wide-stop setups are structurally better trades.
     They are separable: replace the cost gate with a pure stop-size floor in ATR
     units, which has no cost in it at all.  If the ATR floor reproduces the gain, the
     mechanism is structure.  If it does not, the mechanism is cost.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models import ict_bt, ict_system

pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"
IDX = L.INDICES
_C = {}


def data(sym, hold):
    k = (sym, hold)
    if k not in _C:
        p = sym + "_H" if hold else sym
        df = pd.read_parquet(L.DATA / f"{p}.parquet")
        bars, atr = L.resample(df)
        _C[k] = (df, bars, atr, ict_system.daily_context(df),
                 ict_system.session_pools(df))
    return _C[k]


def book(syms, hold, cri=0.20, min_rr=2.0, atr_floor=None):
    """atr_floor: instead of the cost gate, require stop >= atr_floor x ATR."""
    out = []
    for s in syms:
        df, bars, atr, ctx, asia = data(s, hold)
        sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
        kw = dict(L.EXECUTE)
        kw["cost"] = L.cost_for(s, hold)
        kw["min_rr"] = min_rr
        kw["cri_max"] = 0.0 if atr_floor is not None else cri
        t = ict_bt.run(df, sigs, bars.index, L.UNIT[s], pd.Timedelta(L.TF), **kw)
        if not len(t):
            continue
        if atr_floor is not None:
            a = pd.Series(atr, index=bars.index).reindex(t.t, method="ffill").values
            t = t[(t.R_pips.values * L.UNIT[s]) >= atr_floor * a]
        t = t[~t.t.dt.dayofweek.isin([0])]
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def st(d, lab, months):
    if d is None or len(d) < 15:
        return dict(arm=lab, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = L.bootstrap(v)
    return dict(arm=lab, n=len(v), per_wk=len(v) / (months * 4.33),
                WR=float((d.out == 1).mean()), PF=L.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(),
                med_stop=d.R_pips.median(), P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    print("=" * 128)
    print("Q1+Q2  cri_max on the 2015-2023 INDEX HOLDOUT (9 years, never fitted on)")
    print("=" * 128)
    rows = []
    for c in (0.20, 0.16, 0.12, 0.10, 0.08, 0.06, 0.04):
        rows.append(st(book(IDX, True, cri=c), f"holdout  cri {c:.2f}", 108))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n" + "=" * 128)
    print("the same sweep on 2024-2026, indices only, so the two are comparable")
    print("=" * 128)
    rows = []
    for c in (0.20, 0.16, 0.12, 0.10, 0.08, 0.06, 0.04):
        rows.append(st(book(IDX, False, cri=c), f"live idx cri {c:.2f}", 32))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n" + "=" * 128)
    print("Q3  is it COST or STRUCTURE?  a pure ATR stop-floor has no cost in it")
    print("=" * 128)
    rows = []
    for a in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        rows.append(st(book(IDX, True, atr_floor=a if a else None,
                            cri=0.20 if not a else 0.20),
                       f"holdout  stop >= {a:.2f} ATR", 108))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))
