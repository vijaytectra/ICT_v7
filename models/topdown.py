"""Top-down Unicorn: the M15 Unicorn is only the TRIGGER. The trade is decided on H4.

This is the usage every annotated case actually shows and every earlier test in this
project skipped: the Unicorn was tested as a standalone pattern, taken wherever it
formed. ICT's own framing (ict-core-patterns.md: "condition -> stage -> execution",
top-down-analysis.md, the H4 cases in the OpenMobius KB) puts an HTF PD array first
and the LTF pattern last.

Sequence
  1. On H4, maintain the unmitigated PD arrays: fair value gaps and order blocks
     (last opposite-close candle before an H4 displacement that broke a swing).
  2. H4 bias = direction of the most recent H4 structure break.
  3. An M15 Unicorn is accepted ONLY IF its entry zone sits inside an unmitigated H4
     array of the same polarity, and its direction matches H4 bias.
  4. Stop beyond the H4 array's far edge (the array is the invalidation) or the sweep.
  5. Target: the HTF draw - the far side of the H4 dealing range in the bias direction,
     gated on a minimum R:R.

Everything at bar i uses only H4 candles that have CLOSED before the M15 bar's time.
"""
import numpy as np
import pandas as pd
from models.unicorn_v5 import detect as unicorn_detect, swings


def h4_context(df, n_swing=2, lookback_bars=60):
    """Per H4 bar (indexed by its CLOSE time): bias, dealing range, and the list of
    unmitigated FVGs and OBs that exist as of that close."""
    b = df.resample("4h", label="right", closed="right").agg(
        {"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    o, h, l, c = b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n_swing)
    fvgs, obs = [], []              # live arrays: dict(lo, hi, side, born)
    rows = []
    last_sh = last_sl = np.nan
    bias = 0
    for i in range(3, N):
        if hi[i]: last_sh = hp[i]
        if lo[i]: last_sl = lp[i]
        # structure break -> bias, and the OB is the last opposite candle before it
        if np.isfinite(last_sh) and c[i] > last_sh and c[i] > o[i]:
            bias = 1
            j = i - 1
            while j > max(0, i - 12) and not (c[j] < o[j]): j -= 1
            if c[j] < o[j]: obs.append(dict(lo=min(o[j], c[j]), hi=max(o[j], c[j]), side=1, born=i))
            last_sh = np.nan
        if np.isfinite(last_sl) and c[i] < last_sl and c[i] < o[i]:
            bias = -1
            j = i - 1
            while j > max(0, i - 12) and not (c[j] > o[j]): j -= 1
            if c[j] > o[j]: obs.append(dict(lo=min(o[j], c[j]), hi=max(o[j], c[j]), side=-1, born=i))
            last_sl = np.nan
        # new H4 FVGs
        if l[i] > h[i-2]: fvgs.append(dict(lo=h[i-2], hi=l[i], side=1, born=i))
        if h[i] < l[i-2]: fvgs.append(dict(lo=h[i], hi=l[i-2], side=-1, born=i))
        # mitigation: price traded through the array's far edge
        fvgs = [g for g in fvgs if not ((g["side"] == 1 and l[i] < g["lo"]) or
                                        (g["side"] == -1 and h[i] > g["hi"])) and i - g["born"] < 200]
        obs = [g for g in obs if not ((g["side"] == 1 and l[i] < g["lo"]) or
                                      (g["side"] == -1 and h[i] > g["hi"])) and i - g["born"] < 200]
        rng_hi = h[max(0, i - lookback_bars):i + 1].max()
        rng_lo = l[max(0, i - lookback_bars):i + 1].min()
        rows.append(dict(t=b.index[i], bias=bias, rng_hi=rng_hi, rng_lo=rng_lo,
                         fvgs=list(fvgs), obs=list(obs)))
    return pd.DataFrame(rows).set_index("t")


def filter_signals(sigs, m15_index, ctx, array="fvg", require_bias=True, tol_frac=0.0):
    """Keep only M15 Unicorns whose entry zone sits inside a live H4 array of the same
    polarity, as of the last H4 close before the M15 bar."""
    out = []
    ct = ctx.index.values
    for s in sigs:
        t = m15_index[s["bar"]]
        k = np.searchsorted(ct, np.datetime64(t), "right") - 1     # last CLOSED H4 bar
        if k < 0: continue
        row = ctx.iloc[k]
        side = s["side"]
        if require_bias and row.bias != side: continue
        arrays = row.fvgs if array == "fvg" else (row.obs if array == "ob" else row.fvgs + row.obs)
        px = s["mt"]
        hit = None
        for g in arrays:
            if g["side"] != side: continue
            tol = tol_frac * (g["hi"] - g["lo"])
            if g["lo"] - tol <= px <= g["hi"] + tol:
                hit = g; break
        if hit is None: continue
        s = dict(s); s["h4_lo"] = hit["lo"]; s["h4_hi"] = hit["hi"]
        s["h4_rng_hi"] = row.rng_hi; s["h4_rng_lo"] = row.rng_lo
        out.append(s)
    return out
