"""Loading / caching / evaluation for MMXM v2, including the SMT peer wiring."""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm, mmxm2, mmxm_bt
from models.mmxm_lab import FX, INDICES, IS_END, UNIT, load, resample

# positively correlated groups.  SMT is only meaningful inside one of these:
# 16-smt-divergence/correlated-pairs-smt.md - the pair must move together.
GROUPS = {
    "idx": ["USATECH", "USA500", "USA30"],          # NQ / ES / YM proxies
    "usd_base": ["EURUSD", "GBPUSD", "AUDUSD"],     # all quoted against USD
    "usd_quote": ["USDCHF", "USDCAD", "USDJPY"],    # all with USD as base
}
GROUP_OF = {s: g for g, m in GROUPS.items() for s in m}

_p = {}


def prep(sym, tf="15min", a_win=mmxm2.A_WIN, atr_ratio=0.7, overlap_min=0.7):
    key = (sym, tf, a_win, atr_ratio, overlap_min)
    if key not in _p:
        df = load(sym)
        bars, atr = resample(df, tf)
        acc = mmxm2.accumulation(bars, a_win, atr_ratio, overlap_min)
        clock = mmxm2.sweep_clock(bars, acc, a_win)
        ctx, _ = mmxm.htf_context(df, "1D", 2)
        _p[key] = (df, bars, atr, acc, clock, ctx.bias)
    return _p[key]


def peers_for(sym, bars, tf="15min", **kw):
    """Each group member's own sweep clock, reindexed onto this instrument's bars."""
    out = {}
    for p in GROUPS[GROUP_OF[sym]]:
        if p == sym:
            continue
        _, pb, _, _, pc, _ = prep(p, tf, **kw)
        out[p] = pc.reindex(bars.index, method="ffill").fillna(False)
    return out


_s = {}


def signals(sym, tf="15min", prep_kw=None, **det):
    prep_kw = prep_kw or {}
    key = (sym, tf, tuple(sorted(prep_kw.items())), tuple(sorted(det.items())))
    if key not in _s:
        df, bars, atr, acc, clock, bias = prep(sym, tf, **prep_kw)
        pr = peers_for(sym, bars, tf, **prep_kw) if det.get("require_smt") else None
        _s[key] = mmxm2.detect(bars, acc, peers=pr, htf_bias=bias, **det)
    return _s[key]


def evaluate(sym, det, exe, tf="15min", prep_kw=None, period=None):
    df, bars, atr, acc, clock, bias = prep(sym, tf, **(prep_kw or {}))
    sg = signals(sym, tf, prep_kw, **det)
    if period == "IS":
        sg = [s for s in sg if bars.index[s["bar"]] < IS_END]
    elif period == "OOS":
        sg = [s for s in sg if bars.index[s["bar"]] >= IS_END]
    return mmxm_bt.run(df, sg, bars.index, UNIT[sym], pd.Timedelta(tf), **exe)


def pooled(syms, det, exe, tf="15min", prep_kw=None, period=None, cost=None):
    out = []
    for s in syms:
        e = dict(exe)
        if cost is not None:
            e["cost"] = cost[s]
        t = evaluate(s, det, e, tf, prep_kw, period)
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out \
        else pd.DataFrame()


def pf(t):
    if t is None or len(t) == 0:
        return np.nan
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    return float(g / b) if b > 0 else np.inf
