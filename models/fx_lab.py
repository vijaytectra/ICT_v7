"""FX LAB - corrected engine + the untested ideas from THE_SYSTEM.md PART 5.

WHAT IS FIXED RELATIVE TO models/ict_bt.py
------------------------------------------
1. SHORT SIDE PAYS THE SPREAD.  ict_bt.py:83 fills a short on the ASK high and
   ict_bt.py:94-95 exits it on the BID.  Both are the favourable side.  A sell limit
   fills when the BID rises to it; the buy-back happens on the ASK.  Measured impact on
   the locked 9-instrument model: PF 1.539 -> 1.337, +104.5R -> +66.4R.  Since 100% of
   the locked model's profit is on the short side, this is not a rounding error.
2. THE FILL BAR IS SCANNED FOR THE STOP.  ict_bt.py:87 starts the exit walk at fill+1,
   so a stop taken during the same minute the limit filled is invisible.  Optional here
   (`fill_bar_stop`) because on M1 it is a one-minute blind spot, not a 15-minute one.

WHAT IS NEW (never tested in this project - see THE_SYSTEM.md PART 5 items 5 and 6)
----------------------------------------------------------------------------------
  entry_frac   Where inside the FVG the limit sits.  0.0 = the near edge (first touched,
               shallow, fills often, small R:R), 1.0 = the far edge (deep, fills rarely,
               large R:R).  0.5 is `ce`, the locked behaviour, and the ONLY value the
               project has ever measured besides the near edge.
  min_hz       PATH FILTER.  How much headroom the target has: the distance from entry to
               the target divided by the distance from entry to the NEAREST OPPOSING
               pool in front of it.  THE_SYSTEM.md PART 5 item 5 says no repo in the
               audit measures a property of the path to the target, and that the one
               filter that ever worked here (DOL reachability) is exactly that class.
  recency      PATH FILTER.  Bars since the target level was last CROSSED on a close.
               DOL reachability counts HOW MANY times; this asks HOW RECENTLY.

DISCIPLINE
----------
DEV = the first 60% of each instrument's history, VAL = the last 40%.  Variants are
scored on DEV, and VAL is printed beside it so the decay is visible.  With ~226 FX
trades in total this is a small sample and the multiple-comparisons cost is real; the
report prints the detection floor so a lift cannot be read as a result when it is noise.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import ict_system, asia_locked as L

FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"]
IDX = ["USATECH", "USA500", "USA30"]

# R multiples at which a partial exit / break-even stop can be armed.  For each one the
# engine records whether price later returned to the entry, i.e. whether a break-even stop
# armed there would have fired.  Without this a ladder study cannot be honest.
BE_LEVELS = (0.25, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5)


def run_fixed(df, sigs, bar_index, pip, tf_delta, entry_frac=0.5, stop_buf=0.0,
              rr_fixed=2.0, min_rr=2.0, max_rr=0.0, cost=0.0, cri_max=0.20,
              window_min=360, max_hold=1440, stf_close=None, min_target_x=0,
              x_lookback=96, fill_bar_stop=True, min_hz=0.0, max_recency=0,
              target="dol", **_):
    """The locked logic with the two quote-side defects corrected."""
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h = df.l_b.values, df.h_b.values
    pos = df.index
    trades = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy:
            continue
        side = s["side"]

        # ---- entry: anywhere inside the gap, not just its midpoint -------------------
        zlo, zhi = s["zone_lo"], s["zone_hi"]
        if not (np.isfinite(zlo) and np.isfinite(zhi)) or zhi <= zlo:
            continue
        px = (zhi - entry_frac * (zhi - zlo)) if side == 1 else (zlo + entry_frac * (zhi - zlo))

        stop = s["sweep_px"] - side * stop_buf * pip
        R = (px - stop) * side
        if R <= 0:
            continue
        Rp0 = R / pip
        if cost > 0 and cri_max > 0 and cost / Rp0 > cri_max:
            continue

        # ---- target -------------------------------------------------------------------
        pool = []
        for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
            v = s.get(key)
            if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                pool.append(v)
        if not pool:
            continue
        tp = min(pool) if side == 1 else max(pool)

        # ---- DOL reachability (unchanged, the one validated filter) -------------------
        if min_target_x > 0 and stf_close is not None:
            j0 = max(0, s["bar"] - x_lookback)
            sd = stf_close[j0:s["bar"] + 1] > tp
            if int(np.sum(sd[1:] != sd[:-1])) < min_target_x:
                continue

        # ---- NEW path filter: recency of the last close across the target -------------
        if max_recency > 0 and stf_close is not None:
            j0 = max(0, s["bar"] - x_lookback)
            seg = stf_close[j0:s["bar"] + 1] > tp
            flips = np.flatnonzero(seg[1:] != seg[:-1])
            if len(flips) == 0 or (len(seg) - 1 - flips[-1]) > max_recency:
                continue

        # ---- NEW path filter: headroom to the nearest opposing pool -------------------
        if min_hz > 0:
            opp = []
            for key in ("pdl", "al") if side == 1 else ("pdh", "ah"):
                v = s.get(key)
                if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                    opp.append(v)
            if opp:
                obstacle = min(opp) if side == 1 else max(opp)
                d_t = abs(tp - px)
                d_o = abs(obstacle - px)
                if d_o > 0 and d_t / d_o < min_hz:
                    continue

        rr = side * (tp - px) / R
        if rr < min_rr:
            continue
        if max_rr and rr > max_rr:
            continue

        # ---- fill: long buys the ASK, short SELLS to the BID --------------------------
        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            hit = (ai_l[j] <= px) if side == 1 else (bi_h[j] >= px)
            if hit:
                fill = j
                break
        if fill < 0:
            continue

        # ---- exit: long sells the BID, short BUYS BACK on the ASK.  Loss first. -------
        # MFE is accumulated on the EXIT quote and BEFORE the barrier test on each bar,
        # so `mfe_r` is the best R a partial exit could actually have been filled at.
        #
        # BE_HIT[x] answers the question a partial-exit study cannot skip: after the trade
        # first reached +x R, did price come BACK to the entry before the trade ended?
        # If it did, a break-even stop armed at +x R would have closed the remainder at 0
        # - including on trades that went on to hit the target.  Without this a ladder
        # study silently keeps every winner AND rescues every loser, which is not a rule,
        # it is a wish.
        out = 0
        mfe = 0.0
        reached = {x: -1 for x in BE_LEVELS}          # bar at which +x R was first seen
        be_hit = {x: False for x in BE_LEVELS}        # entry revisited after that bar
        k = fill if fill_bar_stop else fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if side == 1:
                fav, adv = (bi_h[k] - px) / R, (bi_l[k] - px) / R
            else:
                fav, adv = (px - ai_l[k]) / R, (px - ai_h[k]) / R
            mfe = max(mfe, fav)
            for x in BE_LEVELS:
                if reached[x] < 0 and fav >= x:
                    reached[x] = k
                # Same bar counts.  If the bar that first printed +x R also traded back
                # through the entry, the intrabar order is unknowable at this resolution,
                # so the pessimistic reading is taken: the break-even stop fired.  The
                # opposite assumption is exactly the one that manufactures free wins.
                if reached[x] >= 0 and adv <= 0.0:
                    be_hit[x] = True
            if side == 1:
                if bi_l[k] <= stop:
                    out = -1
                    break
                if bi_h[k] >= tp:
                    out = 1
                    break
            else:
                if ai_h[k] >= stop:
                    out = -1
                    break
                if ai_l[k] <= tp:
                    out = 1
                    break
            k += 1
        busy = k

        Rp = R / pip
        net = (rr - cost / Rp) if out == 1 else (-(1 + cost / Rp) if out == -1 else -cost / Rp)
        rec = dict(t=pos[fill], side=side, R_pips=Rp, rr=rr, out=out,
                   netR=net, bars=k - fill, mfe_r=float(mfe),
                   cost_r=float(cost / Rp))
        for x in BE_LEVELS:
            rec[f"be_{x}"] = bool(be_hit[x])
        trades.append(rec)
    return pd.DataFrame(trades)


def trades_for(sym, **over):
    df = L.load(sym)
    bars, atr = L.resample(df)
    ctx = ict_system.daily_context(df)
    asia = ict_system.session_pools(df)
    sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
    kw = dict(L.EXECUTE)
    kw["cost"] = L.cost_for(sym)
    kw["stf_close"] = bars.c_b.values
    kw.update(over)
    t = run_fixed(df, sigs, bars.index, L.UNIT[sym], pd.Timedelta(L.TF), **kw)
    if len(t) and L.SKIP_DOW:
        t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)].reset_index(drop=True)
    if len(t):
        t["sym"] = sym
    return t


def book(syms, **over):
    out = [trades_for(s, **over) for s in syms]
    out = [x for x in out if len(x)]
    return pd.concat(out, ignore_index=True).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def pf(v):
    g = v[v > 0].sum()
    b = -v[v < 0].sum()
    return float(g / b) if b > 0 else float("nan")


def split(t, frac=0.6):
    """Chronological DEV/VAL on the pooled book."""
    if not len(t):
        return t, t
    cut = t.t.quantile(frac)
    return t[t.t <= cut], t[t.t > cut]


def line(tag, t):
    if not len(t):
        return f"{tag:34} no trades"
    d, v = split(t)
    def part(x):
        if not len(x):
            return "   n=0"
        return (f"n={len(x):4} PF={pf(x.netR):5.3f} R={x.netR.sum():+7.1f} "
                f"WR={(x.netR > 0).mean()*100:4.1f}%")
    return f"{tag:34} DEV {part(d)}   |   VAL {part(v)}"
