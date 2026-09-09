"""Where do the trades go?  A funnel from raw signal to booked trade.

The locked model takes 395 trades in 32 months across 9 instruments - 12.3 a month.
Before adding anything, it is worth knowing exactly where the other signals die,
because each stage is a different lever and some of them are free.

Stages, in the order the executor applies them:

  1  signals emitted by the detector
  2  - R <= 0                     entry is on the wrong side of the stop (degenerate)
  3  - cost / risk > 20%          brodenbeck v4 Screen 2
  4  - no unswept pool above/below the entry
  5  - planned R:R < 2            the pool is too close
  6  - planned R:R > 10           the pool is too far
  7  - the limit never filled inside 6 h
  8  - a position was already open on that instrument   <- the one-at-a-time rule
  9  - the fill landed on a Monday
  = trades

Stage 8 is the interesting one: those are real, valid setups that were simply crowded
out.  Stage 7 is the second: entries that never got their retrace.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

E = L.EXECUTE


def funnel(df, sigs, bar_index, unit, tf_delta, cost, skip_dow=(0,)):
    al, ah = df.l_a.values, df.h_a.values
    pos = df.index
    c = dict(signals=len(sigs), bad_R=0, cost_gate=0, no_pool=0, rr_low=0, rr_high=0,
             no_fill=0, busy=0, monday=0, taken=0)
    busy = -1
    blocked = []
    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2:
            continue
        side = s["side"]
        px, stop = s["ce"], s["sweep_px"]
        R = (px - stop) * side
        if R <= 0:
            c["bad_R"] += 1; continue
        Rp = R / unit
        if cost > 0 and cost / Rp > E["cri_max"]:
            c["cost_gate"] += 1; continue
        pool = []
        for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
            v = s.get(key)
            if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                pool.append(v)
        if not pool:
            c["no_pool"] += 1; continue
        tp = min(pool) if side == 1 else max(pool)
        rr = side * (tp - px) / R
        if rr < E["min_rr"]:
            c["rr_low"] += 1; continue
        if E["max_rr"] and rr > E["max_rr"]:
            c["rr_high"] += 1; continue
        end = min(i0 + E["window_min"], len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                fill = j; break
        if fill < 0:
            c["no_fill"] += 1; continue
        if i0 <= busy:
            c["busy"] += 1
            blocked.append(dict(t=pos[fill], side=side, rr=rr, R_units=Rp))
            continue
        if skip_dow and pos[fill].dayofweek in skip_dow:
            c["monday"] += 1; continue
        # walk the trade only far enough to know when it ends
        bl, bh = df.l_b.values, df.h_b.values
        k = fill + 1
        stop_end = min(fill + E["max_hold"], len(pos) - 1)
        while k <= stop_end:
            if (side == 1 and bl[k] <= stop) or (side == -1 and bh[k] >= stop):
                break
            if (side == 1 and bh[k] >= tp) or (side == -1 and bl[k] <= tp):
                break
            k += 1
        busy = k
        c["taken"] += 1
    return c, pd.DataFrame(blocked)


_P = {}


def prep(sym, path=None):
    if sym not in _P:
        df = pd.read_parquet(L.DATA / f"{path or sym}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        _P[sym] = (df, bars, atr, sigs)
    return _P[sym]


if __name__ == "__main__":
    tot = {}
    allblocked = []
    print(f"{'instrument':<12}" + "".join(f"{k:>10}" for k in
          ("signals", "bad_R", "cost", "no_pool", "rr_low", "rr_high",
           "no_fill", "busy", "monday", "taken")))
    for s in L.ALL:
        df, bars, atr, sigs = prep(s)
        c, bl = funnel(df, sigs, bars.index, L.UNIT[s], pd.Timedelta(L.TF), L.COST[s])
        if len(bl):
            bl["sym"] = s; allblocked.append(bl)
        print(f"{s:<12}" + "".join(f"{c[k]:>10}" for k in
              ("signals", "bad_R", "cost_gate", "no_pool", "rr_low", "rr_high",
               "no_fill", "busy", "monday", "taken")))
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
    print(f"{'TOTAL':<12}" + "".join(f"{tot[k]:>10}" for k in
          ("signals", "bad_R", "cost_gate", "no_pool", "rr_low", "rr_high",
           "no_fill", "busy", "monday", "taken")))

    n = tot["signals"]
    print(f"\n  {n} raw signals -> {tot['taken']} trades ({tot['taken']/n*100:.1f}%)\n")
    for k, lab in (("bad_R", "entry on the wrong side of the stop"),
                   ("cost_gate", "cost > 20% of risk (Screen 2)"),
                   ("no_pool", "no unswept pool in front"),
                   ("rr_low", "pool closer than 2R"),
                   ("rr_high", "pool further than 10R"),
                   ("no_fill", "limit never filled in 6 h"),
                   ("busy", "crowded out - a position was already open"),
                   ("monday", "Monday")):
        print(f"    {tot[k]:>6} ({tot[k]/n*100:>4.1f}%)  {lab}")

    if allblocked:
        b = pd.concat(allblocked)
        b.to_csv(r"C:\personal\ICT_v7\reports\funnel_blocked.csv", index=False)
        print(f"\n  the {len(b)} crowded-out setups had median planned R:R "
              f"{b.rr.median():.2f} and median risk {b.R_units.median():.2f} units "
              f"- they are ordinary setups, not junk.")
