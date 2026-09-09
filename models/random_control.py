"""TEST 7 — random-entry control.

The question a backtest cannot answer on its own: does the SETUP add anything, or would
any trade taken at these hours, on these instruments, with this stop and this target
have done as well?

Everything is held constant except the one thing under test:

  same instruments          same calendar days
  same session hours        same risk distance R (per matched trade)
  same planned R:R          same execution model (M1 bid/ask, loss-first, 24 h cap)
  same cost                 same Monday exclusion
  same number of trades

Three controls, because "random" can mean three different things:

  C1  random TIME, real side   - does WHERE in the day we enter matter?
  C2  real time, random SIDE   - does the DIRECTIONAL read matter?
  C3  random time AND side     - the full null

Each is replicated 200 times so the answer is a distribution, not one lucky draw.
A single random pass proves nothing; the real PF has to sit outside the control's
spread to mean anything.
"""
import sys

import numpy as np
import pandas as pd
from numba import njit

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L

MAX_HOLD = 1440


@njit(cache=True)
def walk(bi_l, bi_h, start, px, stop, tp, side, max_hold):
    """Loss checked first, exactly as the locked executor does."""
    end = min(start + max_hold, bi_l.shape[0] - 1)
    k = start + 1
    while k <= end:
        if side == 1:
            if bi_l[k] <= stop:
                return -1, k - start
            if bi_h[k] >= tp:
                return 1, k - start
        else:
            if bi_h[k] >= stop:
                return -1, k - start
            if bi_l[k] <= tp:
                return 1, k - start
        k += 1
    return 0, end - start


@njit(cache=True)
def run_rep(idx_choices, px_a, px_b, bi_l, bi_h, R_arr, rr_arr, sides, cost_u, unit):
    n = idx_choices.shape[0]
    out = np.empty(n)
    for i in range(n):
        j = idx_choices[i]
        side = sides[i]
        px = px_a[j] if side == 1 else px_b[j]
        R = R_arr[i]
        stop = px - side * R
        tp = px + side * rr_arr[i] * R
        res, _ = walk(bi_l, bi_h, j, px, stop, tp, side, MAX_HOLD)
        Rp = R / unit
        if res == 1:
            out[i] = rr_arr[i] - cost_u / Rp
        elif res == -1:
            out[i] = -(1.0 + cost_u / Rp)
        else:
            out[i] = -cost_u / Rp
    return out


def prep(sym):
    df = pd.read_parquet(L.DATA / f"{sym}.parquet")
    return df


def build_pool(df, hours):
    """Candidate entry bars: inside the session hours, not Monday."""
    h = df.index.hour
    ok = np.zeros(len(df), bool)
    for a, b in hours:
        ok |= (h >= a) & (h < b)
    ok &= (df.index.dayofweek != 0)
    return np.flatnonzero(ok)


def control(real, sym, df, mode, reps=200, seed=0):
    """real: the locked trades for this instrument."""
    unit = L.UNIT[sym]
    cost = L.COST[sym]
    pos = df.index
    px_a, px_b = df.c_a.values, df.c_b.values
    bi_l, bi_h = df.l_b.values, df.h_b.values
    day = pos.normalize()

    # match each real trade to the same calendar day and session hour band
    hours = [(9, 23)]
    pool = build_pool(df, hours)
    pool_day = day.values[pool]

    R_arr = (real.R_pips.values * unit).astype(np.float64)
    rr_arr = real.rr.values.astype(np.float64)
    real_side = real.side.values.astype(np.int64)
    real_idx = pos.searchsorted(real.t.values).astype(np.int64)
    real_days = day.values[np.clip(real_idx, 0, len(pos) - 1)]

    # per real trade, the candidate bars on that same day
    by_day = {}
    for k, d in enumerate(pool_day):
        by_day.setdefault(d, []).append(pool[k])
    cand = [np.array(by_day.get(d, []), dtype=np.int64) for d in real_days]

    rng = np.random.default_rng(seed)
    pfs, ers, ns = [], [], []
    for r in range(reps):
        if mode in ("C1", "C3"):
            j = np.array([c[rng.integers(len(c))] if len(c) else -1 for c in cand],
                         dtype=np.int64)
        else:
            j = real_idx.copy()
        keep = j >= 0
        sides = (real_side.copy() if mode == "C1"
                 else rng.choice(np.array([-1, 1]), size=len(real_side)))
        v = run_rep(j[keep], px_a, px_b, bi_l, bi_h,
                    R_arr[keep], rr_arr[keep], sides[keep].astype(np.int64),
                    cost, unit)
        g = v[v > 0].sum(); b = -v[v < 0].sum()
        pfs.append(g / b if b > 0 else np.nan)
        ers.append(v.mean())
        ns.append(len(v))
    return np.array(pfs), np.array(ers), int(np.median(ns))
