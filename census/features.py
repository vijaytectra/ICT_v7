"""Causal feature set. Every value at bar i uses only bars <= i."""
import numpy as np, pandas as pd

def build(df, pip):
    c, h, l, o = df.c_b, df.h_b, df.l_b, df.o_b
    f = pd.DataFrame(index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(1)
    atr = tr.rolling(14).mean()

    for k in (5, 15, 60, 240):
        f[f"ret{k}"] = (c - c.shift(k)) / atr                    # momentum, vol-normalised
    for k in (20, 60, 240):
        m = c.rolling(k).mean(); s = c.rolling(k).std()
        f[f"z{k}"] = (c - m) / s                                 # mean-reversion stretch
    for k in (20, 60, 240, 1440):
        hi = h.rolling(k).max(); lo = l.rolling(k).min()
        f[f"pos{k}"] = (c - lo) / (hi - lo)                      # range position
        f[f"brk{k}"] = (c - hi.shift()) / atr                    # breakout distance
    f["atr_pct"] = atr.rolling(2000).rank(pct=True)              # vol regime
    f["spread_pct"] = df.spread.rolling(2000).rank(pct=True)
    f["vol_pct"] = df.v_b.rolling(2000).rank(pct=True)
    f["body"] = (c - o) / atr                                    # last candle body
    f["wick_up"] = (h - np.maximum(c, o)) / atr
    f["wick_dn"] = (np.minimum(c, o) - l) / atr
    run = np.sign(c.diff())
    f["streak"] = run.groupby((run != run.shift()).cumsum()).cumcount() * run
    d = df.index.normalize()
    pdh = h.groupby(d).max().shift(); pdl = l.groupby(d).min().shift()
    f["dist_pdh"] = (c - c.index.normalize().map(pdh)) / atr     # prior-day high dist
    f["dist_pdl"] = (c - c.index.normalize().map(pdl)) / atr
    f["hour"] = df.index.hour
    f["dow"] = df.index.dayofweek
    rnd = (c / (pip * 100)).round() * (pip * 100)
    f["dist_round"] = (c - rnd) / atr
    return f
