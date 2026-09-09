"""Loading, preparation and one-call evaluation for the MMXM model."""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm, mmxm_bt

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")

# one pip (FX) or one index point
UNIT = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "AUDUSD": 1e-4, "USDCAD": 1e-4,
        "USDCHF": 1e-4, "USDJPY": 1e-2,
        "USATECH": 1.0, "USA500": 1.0, "USA30": 1.0}

INDICES = ["USATECH", "USA500", "USA30"]
FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD"]

IS_END = pd.Timestamp("2025-07-01")

_cache = {}


def load(sym):
    if sym not in _cache:
        _cache[sym] = pd.read_parquet(DATA / f"{sym}.parquet")
    return _cache[sym]


def resample(df, tf):
    b = df[["o_b", "h_b", "l_b", "c_b"]].resample(tf).agg(
        {"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    return b, tr.rolling(14).mean().values


_prep = {}


def prep(sym, tf="15min", htf="4h", htf_n=2, max_fvg_age=60):
    """Structure-timeframe bars + higher-timeframe context.  Cached."""
    key = (sym, tf, htf, htf_n, max_fvg_age)
    if key not in _prep:
        df = load(sym)
        bars, atr = resample(df, tf)
        ctx, fvgs = mmxm.htf_context(df, htf, htf_n, max_fvg_age)
        _prep[key] = (df, bars, atr, ctx, fvgs)
    return _prep[key]


_sig = {}


def signals(sym, tf="15min", htf="4h", **kw):
    key = (sym, tf, htf, tuple(sorted(kw.items())))
    if key not in _sig:
        df, bars, atr, ctx, fvgs = prep(sym, tf, htf)
        _sig[key] = mmxm.detect(bars, ctx, fvgs, atr=atr, **kw)
    return _sig[key]


def evaluate(sym, det, exe, tf="15min", htf="4h", period=None):
    """det = detector kwargs, exe = execution kwargs.  period in {None,'IS','OOS'}."""
    df, bars, atr, ctx, fvgs = prep(sym, tf, htf)
    sg = signals(sym, tf, htf, **det)
    if period == "IS":
        sg = [s for s in sg if bars.index[s["bar"]] < IS_END]
    elif period == "OOS":
        sg = [s for s in sg if bars.index[s["bar"]] >= IS_END]
    return mmxm_bt.run(df, sg, bars.index, UNIT[sym], pd.Timedelta(tf), **exe)


def pooled(syms, det, exe, tf="15min", htf="4h", period=None):
    """Trades from several instruments, pooled.  Each instrument is traded
    independently (one position at a time per instrument, not across them)."""
    out = []
    for s in syms:
        t = evaluate(s, det, exe, tf, htf, period)
        if len(t):
            t = t.copy(); t["sym"] = s
            out.append(t)
    if not out:
        return pd.DataFrame()
    return pd.concat(out).sort_values("t").reset_index(drop=True)
