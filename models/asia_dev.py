"""DEV/VAL harness for the Asian-range model.

`asia_locked.portfolio()` only reaches 2024-2026, because the FX parquets start there. The
three US indices have a separate nine-year file, so the only honest split available is:

  DEV  the three indices, 2015-2023   (`*_H.parquet`)   -- search here, and only here
  VAL  everything, 2024-2026                            -- read once, never tuned on

Nothing about the detector changes. `over` reaches ict_bt.run, which is the execution layer.
"""
import pathlib, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L, ict_bt, ict_system

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
_cache = {}


def load(sym, hist):
    key = (sym, hist)
    if key not in _cache:
        _cache[key] = pd.read_parquet(DATA / f"{sym}{'_H' if hist else ''}.parquet")
    return _cache[key]


_prep = {}


def prep(sym, hist):
    key = (sym, hist)
    if key not in _prep:
        df = load(sym, hist)
        bars, atr = L.resample(df)
        ctx = ict_system.daily_context(df)
        asia = ict_system.session_pools(df)
        sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
        _prep[key] = (df, bars, sigs)
    return _prep[key]


def trades(sym, hist, cost=None, skip_dow=L.SKIP_DOW, **over):
    df, bars, sigs = prep(sym, hist)
    kw = dict(L.EXECUTE)
    kw["cost"] = L.cost_for(sym, hist) if cost is None else cost
    kw.update(over)
    kw.setdefault("stf_close", bars.c_b.values)
    t = ict_bt.run(df, sigs, bars.index, L.UNIT[sym], pd.Timedelta(L.TF), **kw)
    if len(t) and skip_dow:
        t = t[~t.t.dt.dayofweek.isin(skip_dow)].reset_index(drop=True)
    return t


def book(syms, hist, **over):
    out = []
    for s in syms:
        t = trades(s, hist, **over)
        if len(t): out.append(t.assign(sym=s))
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


DEVSET = L.INDICES
VALSET = L.ALL


def dev(**over):  return book(DEVSET, True,  **over)
def val(**over):  return book(VALSET, False, **over)


def line(label, d, v):
    def s(t):
        if t is None or len(t) == 0: return (0, np.nan, np.nan, np.nan)
        x = t.netR.values; g = x[x > 0].sum(); b = -x[x < 0].sum()
        return (len(t), g / b if b > 0 else np.inf, x.sum(), 100 * (x > 0).mean())
    dn, dp, dt, dw = s(d); vn, vp, vt, vw = s(v)
    print("%-34s DEV n=%4d PF=%5.3f totR=%+7.1f WR=%4.1f%% | VAL n=%4d PF=%5.3f totR=%+6.1f WR=%4.1f%%"
          % (label, dn, dp, dt, dw, vn, vp, vt, vw))
    return (dn, dp, dt), (vn, vp, vt)
