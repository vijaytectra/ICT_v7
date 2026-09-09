"""Trade-management simulator — the 32% of losses that reached 1R+ and gave it back.

The forensic pass established what is and is not fixable:

  NOT fixable by a wider stop.  Price overshoots the stop by a MEDIAN of 2.4R (live)
  and 1.8R (holdout) before turning.  Widening by 0.5R saves 17-21% of the revisits and
  pays 0.5R extra on every loss that never comes back.  Dead.

  NOT fixable by a tighter stop.  Winners have median MAE -0.35R / -0.42R and 11-19%
  of them dip past -0.75R.  A tighter stop kills the winners first.

  FIXABLE, maybe: 32% of losses reached +1R or more before returning to the stop.
  That cohort is a MANAGEMENT problem, and management rules are cheap to test exactly.

Everything is simulated on the real M1 path, in the same order the bars arrived, with
the same fills as the locked model.  Nothing here is applied to the lock.

Rules available (all off by default = the locked model):

  be_at        move the stop to entry once MFE >= X R          (breakeven)
  be_lock      move the stop to +Y R once MFE >= X R           (lock in profit)
  partial_at   take `partial_frac` off at X R                  (scale out)
  trail_r      once MFE >= trail_start, trail the stop trail_r behind the high
  time_stop    exit flat after N minutes if MFE has not reached time_mfe
  close_stop   only stop out on an M15 CLOSE through the level, not a wick
               (SrsBlack failed-breaker.md: "require a closing print")
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

E = L.EXECUTE


def simulate(df, sigs, bar_index, unit, tf_delta, cost, m15_close=None,
             shorts_only=False, skip_dow=(0,),
             be_at=None, be_lock=0.0, partial_at=None, partial_frac=0.5,
             trail_start=None, trail_r=None, time_stop=None, time_mfe=0.25,
             close_stop=False):
    al, ah = df.l_a.values, df.h_a.values
    bl, bh, bc = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index
    out = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy:
            continue
        side = s["side"]
        px = s["ce"]
        stop0 = s["sweep_px"]
        R = (px - stop0) * side
        if R <= 0:
            continue
        Rp = R / unit
        if cost > 0 and cost / Rp > E["cri_max"]:
            continue
        pool = []
        for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
            v = s.get(key)
            if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                pool.append(v)
        if not pool:
            continue
        tp = min(pool) if side == 1 else max(pool)
        rr = side * (tp - px) / R
        if rr < E["min_rr"] or (E["max_rr"] and rr > E["max_rr"]):
            continue

        end = min(i0 + E["window_min"], len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                fill = j
                break
        if fill < 0:
            continue
        if skip_dow and pos[fill].dayofweek in skip_dow:
            continue
        if shorts_only and side != -1:
            continue

        stop = stop0
        mfe = 0.0
        booked = 0.0          # R already banked from a partial
        size = 1.0
        res = "timeout"
        k = fill + 1
        stop_end = min(fill + E["max_hold"], len(pos) - 1)
        exit_r = 0.0
        while k <= stop_end:
            fav = (bh[k] - px) * side / R if side == 1 else (px - bl[k]) / R
            if fav > mfe:
                mfe = fav

            # ---- partial ------------------------------------------------------
            if partial_at is not None and size == 1.0 and mfe >= partial_at:
                booked += partial_frac * partial_at
                size = 1.0 - partial_frac

            # ---- breakeven / profit lock --------------------------------------
            if be_at is not None and mfe >= be_at:
                lvl = px + side * be_lock * R
                if (side == 1 and lvl > stop) or (side == -1 and lvl < stop):
                    stop = lvl

            # ---- trail ---------------------------------------------------------
            if trail_r is not None and mfe >= (trail_start or trail_r):
                lvl = px + side * (mfe - trail_r) * R
                if (side == 1 and lvl > stop) or (side == -1 and lvl < stop):
                    stop = lvl

            # ---- time stop -----------------------------------------------------
            if time_stop is not None and (k - fill) >= time_stop and mfe < time_mfe:
                exit_r = (bc[k] - px) * side / R
                res = "time"
                break

            hit_stop = (bl[k] <= stop) if side == 1 else (bh[k] >= stop)
            hit_tp = (bh[k] >= tp) if side == 1 else (bl[k] <= tp)
            if hit_stop:
                if close_stop and m15_close is not None:
                    if not m15_close[k]:
                        k += 1
                        continue              # mid-bar wick - wait for the print
                    through = (bc[k] < stop) if side == 1 else (bc[k] > stop)
                    if not through:
                        k += 1
                        continue              # closed back on our side - still alive
                    # CRITICAL: a close-based stop does NOT fill at the stop level.
                    # By the time an M15 bar closes through it, price has already gone
                    # a long way past - the forensic pass measured a MEDIAN overshoot
                    # of 2.4R.  Booking -1R here would understate every loss and make
                    # the rule look like free money.  Exit at the actual close.
                    exit_r = (bc[k] - px) * side / R
                    res = "stop"
                    break
                exit_r = (stop - px) * side / R
                res = "stop"
                break
            if hit_tp:
                exit_r = rr
                res = "tp"
                break
            k += 1
        if res == "timeout":
            # match the locked convention exactly: a 24 h timeout books gross 0,
            # not the actual close.  Only 3 trades, but the baseline must be identical.
            exit_r = 0.0

        gross = booked + size * exit_r
        net = gross - cost / Rp
        busy = k
        out.append(dict(t=pos[fill], side=side, res=res, netR=net, gross=gross,
                        R_units=Rp, rr=rr, mfe=mfe, bars=k - fill,
                        win=int(net > 0)))
    return pd.DataFrame(out)


_P = {}


def prep(sym, path=None):
    if sym not in _P:
        df = pd.read_parquet(L.DATA / f"{path or sym}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        # mark the M1 bar on which each M15 bar closes
        m15 = np.zeros(len(df), bool)
        idx = df.index.searchsorted(bars.index + pd.Timedelta(L.TF) - pd.Timedelta("1min"))
        m15[np.clip(idx, 0, len(df) - 1)] = True
        _P[sym] = (df, bars, atr, sigs, m15)
    return _P[sym]


def run(sym, unit=None, cost=None, path=None, **kw):
    df, bars, atr, sigs, m15 = prep(sym, path)
    t = simulate(df, sigs, bars.index, unit or L.UNIT[sym], pd.Timedelta(L.TF),
                 cost if cost is not None else L.COST[sym], m15_close=m15, **kw)
    if len(t):
        t["sym"] = sym
    return t


def live(**kw):
    o = [run(s, **kw) for s in L.ALL]
    return pd.concat([x for x in o if len(x)]).sort_values("t").reset_index(drop=True)


def hold(**kw):
    o = [run(s + "_H", 1.0, 1.5, s + "_H", **kw)
         for s in ("USATECH", "USA500", "USA30")]
    return pd.concat([x for x in o if len(x)]).sort_values("t").reset_index(drop=True)


def stat(t, label):
    if t is None or len(t) < 15:
        return None
    v = t.netR.values
    gl = -v[v < 0].sum()
    eq = v.cumsum()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0
        mx = max(mx, s)
    p, ci = L.bootstrap(v)
    return dict(rule=label, n=len(v), WR=float((v > 0).mean()),
                ER=float(v.mean()), PF=float(v[v > 0].sum() / gl) if gl else np.inf,
                totR=float(v.sum()),
                maxDD=float((eq - np.maximum.accumulate(eq)).min()), streak=mx,
                P_edge=p, ci_lo=ci[0])
