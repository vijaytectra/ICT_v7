"""Symmetric triple-barrier (1:1 RR) first-touch engine.

Realistic fills:
  LONG  : enter at ASK close, TP/SL measured on BID high/low
  SHORT : enter at BID close, TP/SL measured on ASK low/high
Both barriers inside one bar -> counted as a LOSS (conservative).
"""
import numpy as np
from numba import njit, prange

WIN, LOSS, TIMEOUT = 1, -1, 0

@njit(cache=True, parallel=True)
def first_touch(entry_px, hi, lo, idx, width, max_bars, is_long):
    n = idx.shape[0]
    out = np.zeros(n, np.int8)
    held = np.zeros(n, np.int32)
    for k in prange(n):
        i = idx[k]
        e = entry_px[i]
        if is_long:
            tp, sl = e + width, e - width
        else:
            tp, sl = e - width, e + width
        end = min(i + max_bars, hi.shape[0] - 1)
        res = TIMEOUT
        j = i + 1
        while j <= end:
            if is_long:
                hit_sl = lo[j] <= sl
                hit_tp = hi[j] >= tp
            else:
                hit_sl = hi[j] >= sl
                hit_tp = lo[j] <= tp
            if hit_sl:              # loss checked first = conservative
                res = LOSS
                break
            if hit_tp:
                res = WIN
                break
            j += 1
        out[k] = res
        held[k] = j - i
    return out, held


def run(df, pip, width_pips, is_long, idx, max_bars=1440):
    w = width_pips * pip
    if is_long:
        entry, hi, lo = df.c_a.values, df.h_b.values, df.l_b.values
    else:
        entry, hi, lo = df.c_b.values, df.h_a.values, df.l_a.values
    return first_touch(np.ascontiguousarray(entry), np.ascontiguousarray(hi),
                       np.ascontiguousarray(lo), idx.astype(np.int64),
                       w, max_bars, is_long)


@njit(cache=True)
def sequential(signal, out, held):
    """Non-overlapping trades: take a signal, hold to its barrier, then resume
    scanning from the exit bar. One position at a time — what an EA actually does.
    Removes the overlap that makes 110k bar-signals look like 110k observations."""
    n = signal.shape[0]
    res = np.empty(n, np.int8)
    ent = np.empty(n, np.int64)
    k = 0
    i = 0
    while i < n:
        if signal[i]:
            res[k] = out[i]
            ent[k] = i
            k += 1
            step = held[i]
            i += step if step > 0 else 1
        else:
            i += 1
    return res[:k], ent[:k]
