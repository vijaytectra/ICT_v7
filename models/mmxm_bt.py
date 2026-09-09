"""Execution for the MMXM model.  Signals on the structure timeframe, fills on M1.

  LONG  : resting limit buy -> fills when the ASK trades down to it; TP/SL measured on
          the BID.  SHORT mirrors.  The full spread is paid on both sides.
  Stop  : the swept extreme (phase-B manipulation low/high).  brodenbeck
          stop-placement.md - it is the PROTECTED level; if the premise holds the
          algorithm should not revisit it.
  Both barriers inside one M1 bar counts as a LOSS.
  One position at a time - every trade is an independent observation.
"""
import numpy as np
import pandas as pd

# EET = New York + 7.  Forex and index killzones are different windows.
KZ = {"LDN":    [(9, 12)],                  # London open      02:00-05:00 NY
      "NY":     [(14, 17)],                 # NY AM forex      07:00-10:00 NY
      "NYAM":   [(15, 18)],                 # NY AM indices    08:30-11:00 NY
      "LDN+NY": [(9, 12), (14, 17)],
      "IDX":    [(9, 12), (15, 18)],        # London + index AM
      "ALL":    None}


def run(df, sigs, stf_index, unit, tf_delta, entry="mt", stop_buf=0.0,
        target="fixed", rr=2.0, min_rr=1.5, kz="ALL", cost=0.0,
        window_min=360, max_hold=1440, max_risk=None, max_cost_frac=None):
    """unit = one pip (FX) or one index point.  cost is extra cost in those units,
    charged on top of the spread that is already inside the bid/ask fills."""
    al, ah = df.l_a.values, df.h_a.values
    bl, bh, bc = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index
    hr = pos.hour
    win = KZ[kz]
    trades = []
    busy = -1

    for s in sigs:
        # a structure bar labelled t covers [t, t+delta) and is knowable only at t+delta
        i0 = pos.searchsorted(stf_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy:
            continue
        side = s["side"]
        lo, hi = s["zone_lo"], s["zone_hi"]
        if entry == "mt":     px = (lo + hi) / 2
        elif entry == "edge": px = hi if side == 1 else lo
        elif entry == "cisd": px = s["cisd"]
        else:                                                     # displacement FVG CE
            if not np.isfinite(s["fvg_lo"]): continue
            px = (s["fvg_lo"] + s["fvg_hi"]) / 2
        stop = s["sweep_px"] - side * stop_buf * unit
        R = (px - stop) * side
        if R <= 0:
            continue
        if max_risk is not None and R / unit > max_risk:
            continue
        # brodenbeck v4 Screen 2 - cost / structural risk.  Without a floor the
        # population fills with setups whose entry sits on the sweep extreme:
        # sub-pip stops, planned R:R in the hundreds, ~2% win rate.
        if max_cost_frac is not None and cost > 0 and cost / (R / unit) > max_cost_frac:
            continue

        if target in ("erl", "pool"):
            v = (s["target"] if target == "pool"
                 else (s["erl_hi"] if side == 1 else s["erl_lo"]))
            if not np.isfinite(v) or side * (v - px) <= 0: continue
            tp = v
            rr_p = side * (tp - px) / R
            if rr_p < min_rr: continue                # R:R gate - skip, never resize
        else:
            rr_p = rr
            tp = px + side * rr * R

        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                fill = j; break
        if fill < 0:
            continue
        if win is not None and not any(a <= hr[fill] < b for a, b in win):
            continue

        out = 0
        k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if side == 1:
                if bl[k] <= stop: out = -1; break     # loss checked first
                if bh[k] >= tp:   out = 1;  break
            else:
                if bh[k] >= stop: out = -1; break
                if bl[k] <= tp:   out = 1;  break
            k += 1
        busy = k
        Rp = R / unit
        gross = rr_p if out == 1 else (-1.0 if out == -1 else
                                       side * (bc[min(k, len(bc) - 1)] - px) / R)
        net = gross - cost / Rp
        trades.append(dict(t=pos[fill], side=side, R_units=Rp, rr=rr_p, out=out,
                           netR=net, bars=k - fill, poi_lo=s["poi_lo"]))
    return pd.DataFrame(trades)


def stats(t, label=""):
    if t is None or len(t) == 0:
        return None
    n = len(t)
    w = int((t.netR > 0).sum())
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    eq = t.netR.cumsum()
    dd = float((eq - eq.cummax()).min())
    streak = mx = 0
    for v in t.netR.values:
        streak = streak + 1 if v <= 0 else 0
        mx = max(mx, streak)
    return dict(arm=label, n=n, wr=w / n, ER=float(t.netR.mean()),
                PF=float(g / b) if b > 0 else np.inf, totR=float(t.netR.sum()),
                maxDD=dd, lose_streak=mx, avg_rr=float(t.rr.mean()),
                med_risk=float(t.R_units.median()), med_hold=int(t.bars.median()),
                tp=int((t.out == 1).sum()), sl=int((t.out == -1).sum()),
                timeout=int((t.out == 0).sum()))


def bootstrap(t, iters=4000, seed=11):
    """P(edge > 0) and a 95% CI on expectancy, resampling trades with replacement."""
    if t is None or len(t) < 10:
        return np.nan, (np.nan, np.nan)
    r = np.random.default_rng(seed)
    v = t.netR.values
    m = v[r.integers(0, len(v), (iters, len(v)))].mean(1)
    return float((m > 0).mean()), (float(np.percentile(m, 2.5)),
                                   float(np.percentile(m, 97.5)))
