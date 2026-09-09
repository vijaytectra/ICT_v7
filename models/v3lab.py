"""Shared harness for the asia_v3 detector experiments."""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L, asia_v3, ict_bt, ict_system

IDX = ["USATECH", "USA500", "USA30"]
_C = {}

def data(sym, hold):
    k = (sym, hold)
    if k not in _C:
        p = sym + "_H" if hold else sym
        df = pd.read_parquet(L.DATA / f"{p}.parquet"); bars, atr = L.resample(df)
        _C[k] = (df, bars, atr, ict_system.daily_context(df), ict_system.session_pools(df))
    return _C[k]

def port(syms, hold, shorts=False, **det):
    out = []
    for s in syms:
        df, bars, atr, ctx, asia = data(s, hold)
        sigs = asia_v3.detect(df, bars, atr, ctx, asia, **{**L.DETECT, **det})
        kw = dict(L.EXECUTE); kw["cost"] = 1.5 if hold else L.COST[s]
        t = ict_bt.run(df, sigs, bars.index, 1.0 if hold else L.UNIT[s],
                       pd.Timedelta(L.TF), **kw)
        if len(t):
            t = t[~t.t.dt.dayofweek.isin([0])]
            if shorts and len(t): t = t[t.side == -1]
            if len(t):
                t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()

def st(d, l, mo):
    if d is None or len(d) < 25:
        return dict(arm=l, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = L.bootstrap(v)
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    return dict(arm=l, n=len(v), per_mo=len(v) / mo, WR=float((d.out == 1).mean()),
                ER=v.mean(), PF=L.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(),
                RdD=v.sum() / abs((eq - np.maximum.accumulate(eq)).min()),
                streak=mx, P_edge=p, ci_lo=ci[0])
