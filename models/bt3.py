"""bt2 + the loss-reduction rules mined from the reference repos.

  LR1 failed-breaker exit   SrsBlack 08-breaker-blocks/failed-breaker.md
        "A wick through the breaker zone followed by recovery is NOT a failure —
         require a closing print."  -> exit on a CLOSED M5 bar through the breaker,
         instead of riding to the swept-extreme stop.
  LR2 displacement score    SrsBlack 09-displacement/displacement-strength-criteria.md
        4 causal factors of the 5 (follow-through needs future bars, so it is dropped).
  LR3 HTF bias              SrsBlack 25-htf-bias/htf-bias-framework.md
        "Bullish-FVG long against bearish HTF bias" is listed as a mistake.
  LR4 partials + breakeven  SrsBlack 32-risk-management/partial-takes.md
        "After TP1 fills, move SL to break-even."
"""
import numpy as np, pandas as pd
# EET = New York + 7.  Forex and index killzones are DIFFERENT windows
# (brodenbeck time_and_price/killzones.md): NY forex 07:00-10:00 NY, but the
# index AM killzone - "the project's main hunting ground" - is 08:30-11:00 NY.
KZ = {"LDN":    [(9, 12)],      # London 02:00-05:00 NY
      "NY":     [(14, 17)],     # NY forex 07:00-10:00 NY
      "NYAM":   [(15, 18)],     # index AM 08:30-11:00 NY
      "NYPM":   [(20, 23)],     # index PM 13:30-16:00 NY
      "LDN+NY": [(9, 12), (14, 17)],
      "IDX":    [(9, 12), (15, 18)],      # London + index AM
      "IDXALL": [(15, 18), (20, 23)]}     # index AM + PM

def score(s):
    v = 0
    v += 3 if s["d_body_ratio"] >= .85 else 2 if s["d_body_ratio"] >= .70 else 1
    v += 3 if s["d_opp_wick"] < .10 else 2 if s["d_opp_wick"] < .20 else 1
    v += 3 if s["d_body_avg"] >= 2.0 else 2 if s["d_body_avg"] >= 1.5 else 1
    v += 3 if s["d_fvg_w"] >= .50 else 2 if s["d_fvg_w"] >= .20 else 1
    return v                                            # 4..12

def _equal_cluster(levels, tol):
    """Relative equal highs/lows: 2+ swing levels within `tol` of each other.
    The sources call these the draw on liquidity, not any minor swing."""
    out = []
    for x in levels:
        grp = [y for y in levels if abs(y - x) <= tol]
        if len(grp) >= 2: out.append(sum(grp) / len(grp))
    return out


def run(df, sigs, stf_index, pip, tf_delta, m5_close_idx=None, htf_bias=None,
        entry_mode="edge", stop_mode="sweep", buf_pips=0.0, rr=2.0, kz="LDN",
        comm_pips=0.7, lr1=False, lr2=0, lr3=False, lr4=0.0,
        target="fixed", min_rr=0.0, eq_tol_pips=1.5, pdh=None, pdl=None,
        window_min=240, max_hold=1440):
    """stop_mode: 'sweep'   swept extreme (widest)
                  'breaker' just beyond the breaker block  <- what the annotated cases use
                  'zone'    overlap far edge (tightest)
                  'mss'     MSS origin candle"""
    al, ah = df.l_a.values, df.h_a.values
    bl, bh, bc = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index; hr = pos.hour
    tr = []; busy = -1
    for s in sigs:
        if lr2 and score(s) < lr2: continue                       # LR2
        i0 = pos.searchsorted(stf_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        lo, hi, side = s["zone_lo"], s["zone_hi"], s["side"]
        if entry_mode == "edge":  px = hi if side == 1 else lo
        elif entry_mode == "mt":  px = s.get("mt", (lo + hi) / 2)     # order-block mean threshold
        else:                     px = (lo + hi) / 2                  # CE of the overlap
        if not (min(lo, hi) - 1e-9 <= px <= max(lo, hi) + 1e-9) and entry_mode == "mt":
            px = (lo + hi) / 2
        b = buf_pips * pip
        if stop_mode == "sweep":     stop = s["sweep_px"] - side * b
        elif stop_mode == "breaker": stop = (s["brk_lo"] - b) if side == 1 else (s["brk_hi"] + b)
        elif stop_mode == "zone":    stop = (lo - b) if side == 1 else (hi + b)
        else:                        stop = s["mss_origin"] - side * b
        R = (px - stop) * side
        if R <= 0: continue
        tp1 = px + side * R
        if target in ("equal", "pdhl", "both"):
            pool = []
            if target in ("equal", "both"):
                lv = _equal_cluster(s["sh_hist"] if side == 1 else s["sl_hist"],
                                    eq_tol_pips * pip)
                pool += [x for x in lv if (x > px if side == 1 else x < px)]
            if target in ("pdhl", "both") and pdh is not None:
                v = pdh[i0] if side == 1 else pdl[i0]
                if np.isfinite(v) and ((v > px) if side == 1 else (v < px)): pool.append(v)
            if not pool: continue
            tp = min(pool) if side == 1 else max(pool)
            rr_planned = side * (tp - px) / R
            if rr_planned < min_rr: continue          # R:R gate - skip, do not resize
        else:
            tp = px + side * rr * R
            rr_planned = rr
        brk = s["brk_lo"] if side == 1 else s["brk_hi"]           # LR1 invalidation level

        end = min(i0 + window_min, len(pos) - 1); fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px): fill = j; break
        if fill < 0: continue
        if kz and not any(a <= hr[fill] < b for a, b in KZ[kz]): continue
        if lr3 and htf_bias is not None and htf_bias[fill] != side: continue   # LR3

        got1 = False; res = None; k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if side * (bl[k] if side == 1 else -bh[k]) <= side * (stop if side == 1 else -stop) \
               if False else ((side == 1 and bl[k] <= stop) or (side == -1 and bh[k] >= stop)):
                res = ("be" if (lr4 and got1) else "stop"); break
            if (side == 1 and bh[k] >= tp) or (side == -1 and bl[k] <= tp): res = "tp"; break
            if lr4 and not got1 and ((side == 1 and bh[k] >= tp1) or (side == -1 and bl[k] <= tp1)):
                got1 = True; stop = px                             # LR4 move to breakeven
            if lr1 and m5_close_idx is not None and m5_close_idx[k]:
                if (side == 1 and bc[k] < brk) or (side == -1 and bc[k] > brk):
                    res = "inval"; break                           # LR1 early exit
            k += 1
        if res is None: res = "timeout"
        rr = rr_planned
        exitpx = {"tp": tp, "stop": stop if not (lr4 and got1) else px,
                  "be": px, "inval": bc[k] if k <= stop_end else px,
                  "timeout": bc[min(k, len(bc)-1)]}[res]
        gross = side * (exitpx - px) / (R)                        # in R units
        if lr4 and got1 and res != "tp":
            gross = lr4 * 1.0 + (1 - lr4) * gross
        elif lr4 and res == "tp":
            gross = lr4 * 1.0 + (1 - lr4) * rr
        net = gross - comm_pips / (R / pip)
        busy = k
        tr.append(dict(t=pos[fill], side=side, R_pips=R/pip, res=res,
                       win=int(net > 0), netR=net, bars=k - fill))
    return pd.DataFrame(tr)

def summarise(t, label=""):
    if len(t) == 0: return None
    n = len(t); k = int(t.win.sum())
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    z = 1.96; p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; hw = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return dict(arm=label, trades=n, wr=p, wl=c-hw, ER=float(t.netR.mean()),
                PF=float(g/b) if b > 0 else np.inf, totR=float(t.netR.sum()),
                stopped=int((t.res == "stop").sum()), inval=int((t.res == "inval").sum()),
                be=int((t.res == "be").sum()), tp=int((t.res == "tp").sum()))
