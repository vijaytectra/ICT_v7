"""Trade forensics — what actually HAPPENED inside every trade, bar by bar.

Cohort analysis (by day, by stop size, by ATR) only says WHICH trades lost.  It cannot
say WHY, and every fix built on it is a guess.  This module replays each trade on M1
and records the things that distinguish the possible causes:

  MFE      max favourable excursion in R before the exit.
           A loss with MFE 1.8R is not the same animal as a loss with MFE 0.1R.
           High MFE  -> the READ was right, the EXIT was wrong (management problem).
           Low  MFE  -> the read was wrong (selection problem).

  MAE      max adverse excursion in R.  On WINNERS this says how much room the stop
           actually needed; if winners routinely dip to -0.8R the stop is barely
           surviving and a tighter one destroys the model.

  heat_first  the adverse excursion BEFORE any favourable excursion.  Separates
           "filled and immediately went our way" from "filled and bled first".

  revisit  after the stop was hit, did price reach the ORIGINAL target within the
           following 24 h?  This is the single most diagnostic number in the whole
           study.  A high revisit rate means the premise was correct and the stop was
           in the wrong PLACE - the algorithm came back for the level.  A low revisit
           rate means the setup was simply wrong and no stop placement saves it.

  stop_kind  'wick'  the bar that hit the stop CLOSED back on our side
             'close' the bar closed through the stop
           SrsBlack 08-breaker-blocks/failed-breaker.md: "a wick through the zone
           followed by recovery is NOT a failure - require a closing print."  If most
           stop-outs are wicks, that doctrine is directly actionable here.

  fvg_state  was the FVG fully filled (price traded through its far edge) before the
           stop?  06-fair-value-gaps/fvg-mitigation.md treats a fully mitigated gap as
           spent; a stop-out AFTER full mitigation is a different failure from one
           before it.

Nothing here touches the locked config.  It re-runs the same signals through an
instrumented executor and reports; models/asia_locked.py is imported read-only.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

REVISIT_BARS = 1440          # 24 h of M1 to look for the target after a stop-out


def replay(df, sigs, bar_index, unit, tf_delta, cost, shorts_only=False,
           skip_dow=(0,)):
    """The locked execution, instrumented.  Same fills, same stops, same targets."""
    al, ah = df.l_a.values, df.h_a.values
    bl, bh, bc, bo = df.l_b.values, df.h_b.values, df.c_b.values, df.o_b.values
    pos = df.index
    E = L.EXECUTE
    out = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy:
            continue
        side = s["side"]
        px = s["ce"]
        stop = s["sweep_px"]
        R = (px - stop) * side
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

        # ---- replay bar by bar -------------------------------------------------
        res = 0
        k = fill + 1
        stop_end = min(fill + E["max_hold"], len(pos) - 1)
        mfe = mae = 0.0
        heat_first = 0.0
        seen_up = False
        bars_to_mfe = 0
        stop_kind = ""
        fvg_lo, fvg_hi = s["zone_lo"], s["zone_hi"]
        fvg_full = False
        while k <= stop_end:
            fav = side * (bh[k] - px) / R if side == 1 else side * (bl[k] - px) / R
            adv = side * (bl[k] - px) / R if side == 1 else side * (bh[k] - px) / R
            if fav > mfe:
                mfe = fav
                bars_to_mfe = k - fill
            if adv < mae:
                mae = adv
            if not seen_up:
                if fav >= 0.25:
                    seen_up = True
                elif adv < heat_first:
                    heat_first = adv
            # a bullish FVG is fully mitigated when price trades through its LOW
            if not fvg_full:
                if (side == 1 and bl[k] < fvg_lo) or (side == -1 and bh[k] > fvg_hi):
                    fvg_full = True
            hit_stop = (bl[k] <= stop) if side == 1 else (bh[k] >= stop)
            hit_tp = (bh[k] >= tp) if side == 1 else (bl[k] <= tp)
            if hit_stop:
                res = -1
                through = (bc[k] < stop) if side == 1 else (bc[k] > stop)
                stop_kind = "close" if through else "wick"
                break
            if hit_tp:
                res = 1
                break
            k += 1

        # ---- did the algorithm come back for the target after stopping us out? --
        revisit = np.nan
        revisit_bars = np.nan
        if res == -1:
            e2 = min(k + REVISIT_BARS, len(pos) - 1)
            revisit = 0
            for j in range(k + 1, e2):
                if (side == 1 and bh[j] >= tp) or (side == -1 and bl[j] <= tp):
                    revisit = 1
                    revisit_bars = j - k
                    break
        busy = k
        net = (rr - cost / Rp) if res == 1 else (
            -(1 + cost / Rp) if res == -1 else -cost / Rp)
        out.append(dict(
            t=pos[fill], side=side, out=res, netR=net, R_units=Rp, rr=rr,
            bars=k - fill, mfe=mfe, mae=mae, heat_first=heat_first,
            bars_to_mfe=bars_to_mfe, stop_kind=stop_kind, fvg_full=int(fvg_full),
            revisit=revisit, revisit_bars=revisit_bars,
            hour=pos[fill].hour, dow=pos[fill].dayofweek,
            sweep_bar=s["sweep_bar"], sig_bar=s["bar"],
            zone_lo=fvg_lo, zone_hi=fvg_hi, px=px, stop=stop, tp=tp,
            ah=s.get("ah"), al=s.get("al")))
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
    t = replay(df, sigs, bars.index, unit or L.UNIT[sym],
               pd.Timedelta(L.TF), cost if cost is not None else L.COST[sym], **kw)
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
