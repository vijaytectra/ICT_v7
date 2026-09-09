"""Unicorn backtest. Signals on the structure timeframe, fills on 1m bid/ask.

  LONG : limit buy in the overlap zone -> fills when ASK trades down to it.
         TP on BID high, SL on BID low.   (SHORT mirrors; full spread paid both ways)
  Stop = sweep extreme. Target = 1R. Both barriers in one bar counts as a LOSS.
  One position at a time -> every trade is an independent observation.
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn import detect

PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}

def resample(df, tf):
    b = df[["o_b","h_b","l_b","c_b"]].resample(tf).agg(
        {"o_b":"first","h_b":"max","l_b":"min","c_b":"last"}).dropna()
    tr = pd.concat([b.h_b-b.l_b, (b.h_b-b.c_b.shift()).abs(),
                    (b.l_b-b.c_b.shift()).abs()], axis=1).max(1)
    return b, tr.rolling(14).mean().values

def backtest(df, sigs, stf_index, pip, tf_delta, entry_mode="edge", window_min=240, max_hold=1440):
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h = df.l_b.values, df.h_b.values
    pos = df.index
    trades = []
    busy_until = -1
    for s in sigs:
        # resample labels a bar by its START. A bar labelled 10:00 on 60min covers
        # [10:00, 11:00) and is only knowable at 11:00 -- entry may not precede that.
        t0 = stf_index[s["bar"]] + tf_delta
        i0 = pos.searchsorted(t0, "left")
        if i0 >= len(pos) - 2 or i0 <= busy_until: continue
        lo, hi, stop = s["zone_lo"], s["zone_hi"], s["stop"]
        px = (hi if s["side"] == 1 else lo) if entry_mode == "edge" else (lo + hi) / 2
        R = (px - stop) if s["side"] == 1 else (stop - px)
        if R <= 0: continue
        tp = px + R if s["side"] == 1 else px - R
        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):                          # wait for the retrace
            if (s["side"] == 1 and ai_l[j] <= px) or (s["side"] == -1 and ai_h[j] >= px):
                fill = j; break
        if fill < 0: continue
        out = 0; k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if s["side"] == 1:
                if bi_l[k] <= stop: out = -1; break
                if bi_h[k] >= tp:   out = 1;  break
            else:
                if bi_h[k] >= stop: out = -1; break
                if bi_l[k] <= tp:   out = 1;  break
            k += 1
        busy_until = k
        trades.append(dict(t=pos[fill], side=s["side"], R_pips=R/pip,
                           out=out, bars=k-fill))
    return pd.DataFrame(trades)

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return c-h, c+h
