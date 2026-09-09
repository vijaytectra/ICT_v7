"""Adding trades WITHOUT touching the locked 395.

The funnel showed 4,903 raw signals become 395 trades.  The one-position-at-a-time rule
costs only 3 of them, so relaxing it is pointless.  The volume sits in four cohorts that
the locked rules reject, and each is rejected for a DIFFERENT reason, so each needs a
different alternative rule:

  A  rr_low   2000 signals  the draw-on-liquidity pool sits closer than 2R.
                            Alternative: stop targeting the pool and use a FIXED R.
                            The pool being near is a fact about the pool, not about the
                            setup.
  B  bad_R     908 signals  the FVG's consequent encroachment sits on the wrong side of
                            the raid extreme, so the CE entry is impossible.
                            Alternative: a different entry level in the same zone.
  C  no_fill   634 signals  the CE limit never traded in 6 h.
                            Alternative: a shallower entry that fills more often, or a
                            longer validity window.
  D  cost      746 signals  risk so small that cost exceeds 20% of it.
                            Alternative: a stop placed further away so the setup becomes
                            economic.

These are ADDITIVE cohorts.  The locked population is untouched; anything kept here is a
second book running alongside it.  Every arm is measured on 2024-2026 AND on the
2015-2023 holdout, and nothing is kept unless it clears both.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

E = L.EXECUTE


def run_cohort(df, sigs, bar_index, unit, tf_delta, cost, cohort,
               entry="ce", stop_mode="sweep", stop_buf=0.0, target="fixed",
               rr=2.0, min_rr=2.0, max_rr=10.0, cri_max=0.20,
               window_min=360, max_hold=1440, skip_dow=(0,)):
    """Trade ONLY the signals the locked model rejected for `cohort`'s reason."""
    al, ah = df.l_a.values, df.h_a.values
    bl, bh, bc = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index
    out = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2:
            continue
        side = s["side"]
        lo, hi = s["zone_lo"], s["zone_hi"]
        ce = s["ce"]
        raid = s["sweep_px"]

        # ---- classify against the LOCKED rules -------------------------------
        R_lock = (ce - raid) * side
        lock_bad_R = R_lock <= 0
        lock_cost = (not lock_bad_R) and cost > 0 and cost / (R_lock / unit) > E["cri_max"]
        pool = []
        for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
            v = s.get(key)
            if v is not None and np.isfinite(v) and ((v > ce) if side == 1 else (v < ce)):
                pool.append(v)
        tp_pool = (min(pool) if side == 1 else max(pool)) if pool else np.nan
        rr_pool = (side * (tp_pool - ce) / R_lock) if (pool and not lock_bad_R) else np.nan
        lock_rr_low = (not lock_bad_R) and (not lock_cost) and pool and rr_pool < E["min_rr"]

        if cohort == "bad_R" and not lock_bad_R:
            continue
        if cohort == "cost" and not lock_cost:
            continue
        if cohort == "rr_low" and not lock_rr_low:
            continue
        if cohort == "no_fill":
            # locked-valid in every other way; the fill test happens below
            if lock_bad_R or lock_cost or (not pool) or rr_pool < E["min_rr"] \
               or rr_pool > E["max_rr"]:
                continue

        # ---- the alternative rules -------------------------------------------
        if entry == "ce":
            px = ce
        elif entry == "near":                      # the edge price reaches FIRST
            px = hi if side == 1 else lo
        elif entry == "far":
            px = lo if side == 1 else hi
        elif entry == "q25":                       # a quarter into the gap
            px = hi - 0.25 * (hi - lo) if side == 1 else lo + 0.25 * (hi - lo)
        else:
            px = ce

        if stop_mode == "sweep":
            stop = raid - side * stop_buf * unit
        elif stop_mode == "zone":                  # just beyond the far edge of the FVG
            stop = (lo - stop_buf * unit) if side == 1 else (hi + stop_buf * unit)
        else:                                      # 'min' - whichever is further away
            a = raid
            b = (lo - stop_buf * unit) if side == 1 else (hi + stop_buf * unit)
            stop = min(a, b) if side == 1 else max(a, b)

        R = (px - stop) * side
        if R <= 0:
            continue
        Rp = R / unit
        if cri_max and cost > 0 and cost / Rp > cri_max:
            continue

        if target == "dol":
            if not np.isfinite(tp_pool):
                continue
            if (tp_pool <= px) if side == 1 else (tp_pool >= px):
                continue
            tp = tp_pool
            rr_p = side * (tp - px) / R
            if rr_p < min_rr or (max_rr and rr_p > max_rr):
                continue
        else:
            rr_p = rr
            tp = px + side * rr * R

        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                fill = j
                break
        if cohort == "no_fill":
            # only interested in the ones the LOCKED entry would have missed
            f0 = -1
            e0 = min(i0 + E["window_min"], len(pos) - 1)
            for j in range(i0, e0):
                if (side == 1 and al[j] <= ce) or (side == -1 and ah[j] >= ce):
                    f0 = j
                    break
            if f0 >= 0:
                continue
        if fill < 0 or fill <= busy:
            continue
        if skip_dow and pos[fill].dayofweek in skip_dow:
            continue

        res = 0
        k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if (side == 1 and bl[k] <= stop) or (side == -1 and bh[k] >= stop):
                res = -1
                break
            if (side == 1 and bh[k] >= tp) or (side == -1 and bl[k] <= tp):
                res = 1
                break
            k += 1
        busy = k
        net = (rr_p - cost / Rp) if res == 1 else (
            -(1 + cost / Rp) if res == -1 else -cost / Rp)
        out.append(dict(t=pos[fill], side=side, out=res, netR=net, R_units=Rp,
                        rr=rr_p, bars=k - fill))
    return pd.DataFrame(out)


_P = {}


def prep(sym, path=None):
    if sym not in _P:
        df = pd.read_parquet(L.DATA / f"{path or sym}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        _P[sym] = (df, bars, atr, sigs)
    return _P[sym]


def run(sym, unit=None, cost=None, path=None, **kw):
    df, bars, atr, sigs = prep(sym, path)
    t = run_cohort(df, sigs, bars.index, unit or L.UNIT[sym], pd.Timedelta(L.TF),
                   cost if cost is not None else L.COST[sym], **kw)
    if len(t):
        t["sym"] = sym
    return t


def live(**kw):
    o = [run(s, **kw) for s in L.ALL]
    o = [x for x in o if len(x)]
    return pd.concat(o).sort_values("t").reset_index(drop=True) if o else pd.DataFrame()


def hold(**kw):
    o = [run(s + "_H", 1.0, 1.5, s + "_H", **kw)
         for s in ("USATECH", "USA500", "USA30")]
    o = [x for x in o if len(x)]
    return pd.concat(o).sort_values("t").reset_index(drop=True) if o else pd.DataFrame()


def stat(t, label):
    if t is None or len(t) < 20:
        return None
    v = t.netR.values
    gl = -v[v < 0].sum()
    eq = v.cumsum()
    p, ci = L.bootstrap(v)
    return dict(arm=label, n=len(v), WR=float((t.out == 1).mean()),
                ER=float(v.mean()), PF=float(v[v > 0].sum() / gl) if gl else np.inf,
                totR=float(v.sum()),
                maxDD=float((eq - np.maximum.accumulate(eq)).min()),
                P_edge=p, ci_lo=ci[0])
