"""Execution lab for the index Unicorn.

The detector is FROZEN - `unicorn_v5.detect` with the SETUP_INDEX configuration. Nothing
here touches signal generation. Only the execution layer changes, because that is where
the measured problem is: the edge exists across twelve years at spread-only cost and dies
at about 0.5 index points of extra cost. So the question is not "is there an edge" but
"why is the R per trade too small to carry a real cost", and every lever below attacks
exactly that.

Three levers, none of them new to this project and none of them yet tried on the Unicorn:

  CRI GATE       brodenbeck v4 Screen 2 - cost / structural risk must stay under a
                 threshold. A 2R target on a 6-point stop pays 25% of its risk in cost
                 before it starts. These are the trades cost kills first, and they are
                 identifiable at signal time.
  DOL TARGET     draw-on-liquidity.md - the target is an identifiable UNSWEPT pool, not a
                 fixed multiple, gated on a minimum R:R. This is what turned the Asian
                 range model from flat to PF 1.30, and the Unicorn has only ever been
                 tested against a flat 2R.
  EXIT RULES     break-even at +BeAtR, target capped at CapRR, and a soft exit if price
                 sits at or below SoftR after SoftMin minutes. Measured on the Asia model
                 (PF 1.296 -> 1.420) and never applied here.

Fills are on 1-minute bid/ask: a long enters at ASK and exits on BID. One position at a
time; a signal arriving before the previous trade's exit bar is skipped, and an order that
never fills changes no state.
"""
import numpy as np
import pandas as pd

KZ = {"LDN": [(9, 12)], "NYAM": [(15, 18)], "NYPM": [(20, 23)],
      "IDX": [(9, 12), (15, 18)], "IDXALL": [(15, 18), (20, 23)],
      "ALL": None}


def run(df, sigs, bar_index, pip, tf_delta, ctx=None, asia=None,
        entry="mt", stop_mode="sweep", stop_buf=0.0, kz="IDX", cost=1.5,
        target="fixed", rr_fixed=2.0, min_rr=0.0, max_rr=0.0,
        cri_max=0.0, window_min=360, max_hold=1440,
        be_at=0.0, cap_rr=0.0, soft_min=0, soft_r=0.0, pd_zone=None,
        stf_close=None, min_target_x=0, x_lookback=96, extra=False):
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h, bi_c = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index
    hr = pos.hour
    day = pos.normalize()
    win = KZ[kz] if kz else None

    if ctx is not None:
        C = ctx.reindex(day).values                 # bias, trending, pdh, pdl
    if asia is not None:
        A = asia.reindex(day).values                # ah, al

    trades = []
    busy = -1
    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        side = s["side"]
        lo, hi = s["zone_lo"], s["zone_hi"]
        px = s.get("mt", (lo + hi) / 2) if entry == "mt" else (
             (hi if side == 1 else lo) if entry == "edge" else (lo + hi) / 2)
        # stop_mode: 'sweep' the swept extreme (widest, what SETUP_INDEX froze),
        #            'breaker' just beyond the breaker body - what the annotated cases in
        #            all three repos actually use, and never tried in the index config,
        #            'zone' the overlap's far edge (tightest).
        b_ = stop_buf * pip
        if stop_mode == "sweep":     stop = s["sweep_px"] - side * b_
        elif stop_mode == "breaker": stop = (s["brk_lo"] - b_) if side == 1 else (s["brk_hi"] + b_)
        elif stop_mode == "zone":    stop = (s["zone_lo"] - b_) if side == 1 else (s["zone_hi"] + b_)
        else:                        stop = s["mss_origin"] - side * b_
        R = (px - stop) * side
        if R <= 0: continue
        Rp = R / pip

        # ---- premium / discount ----------------------------------------------------
        # ICT's most basic filter and one this config never applied: buy only in the
        # DISCOUNT half of the dealing range, sell only in the premium half.  'ote'
        # narrows it to the 62-79% retracement band the sources single out.
        if pd_zone:
            rl, rh = s["rng_lo"], s["rng_hi"]
            if not (np.isfinite(rl) and np.isfinite(rh)) or rh <= rl: continue
            f = (px - rl) / (rh - rl)                # 0 = range low, 1 = range high
            f = f if side == 1 else 1.0 - f          # fraction from the trade's own low
            if pd_zone == "half" and f > 0.5: continue
            if pd_zone == "ote" and not (0.21 <= f <= 0.38): continue

        # ---- CRI: cost as a fraction of structural risk ---------------------------
        if cri_max > 0 and cost > 0 and cost / Rp > cri_max: continue

        # ---- target ---------------------------------------------------------------
        if target == "fixed":
            rr = rr_fixed
            tp = px + side * rr * R
        else:
            pool = []
            if "asia" in target and asia is not None and hr[i0] >= 9:
                ah, al = A[i0]
                v = ah if side == 1 else al
                if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                    pool.append(v)
            if "pdhl" in target and ctx is not None:
                _, _, pdh, pdl = C[i0]
                v = pdh if side == 1 else pdl
                if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                    pool.append(v)
            if "range" in target:
                v = s["rng_hi"] if side == 1 else s["rng_lo"]
                if np.isfinite(v) and ((v > px) if side == 1 else (v < px)): pool.append(v)
            if not pool: continue
            tp = min(pool) if side == 1 else max(pool)

            # ---- DOL REACHABILITY, transplanted from the Asian-range model ----------
            # There it took profit factor 1.20 -> 1.52 with a permutation p of 0.0002.
            # The Unicorn has never had a draw-on-liquidity target at all, let alone a
            # test of whether that target is reachable, so this is the first time the
            # two things that fixed the other model are being applied here.
            if min_target_x > 0 and stf_close is not None:
                j0 = max(0, s["bar"] - x_lookback)
                sd = stf_close[j0:s["bar"] + 1] > tp
                if int(np.sum(sd[1:] != sd[:-1])) < min_target_x: continue

            rr = side * (tp - px) / R
            if min_rr and rr < min_rr: continue          # gate - skip, never resize
            if max_rr and rr > max_rr: continue
            if cap_rr and rr > cap_rr:
                rr = cap_rr; tp = px + side * rr * R

        # ---- fill ------------------------------------------------------------------
        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px): fill = j; break
        if fill < 0: continue
        if win and not any(a <= hr[fill] < b for a, b in win): continue

        # ---- manage -----------------------------------------------------------------
        cur_stop = stop
        be_done = False
        res = None
        k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if (side == 1 and bi_l[k] <= cur_stop) or (side == -1 and bi_h[k] >= cur_stop):
                res = "be" if be_done else "stop"; break
            if (side == 1 and bi_h[k] >= tp) or (side == -1 and bi_l[k] <= tp):
                res = "tp"; break
            fav = side * ((bi_h[k] if side == 1 else bi_l[k]) - px) / R
            if be_at > 0 and not be_done and fav >= be_at:
                be_done = True; cur_stop = px
            if soft_min > 0 and (k - fill) == soft_min:
                now = side * (bi_c[k] - px) / R
                if now <= soft_r: res = "soft"; break
            k += 1
        if res is None: res = "time"
        exitpx = {"tp": tp, "stop": cur_stop, "be": px,
                  "soft": bi_c[min(k, len(bi_c) - 1)],
                  "time": bi_c[min(k, len(bi_c) - 1)]}[res]
        gross = side * (exitpx - px) / R
        net = gross - cost / Rp
        busy = k
        rec = dict(t=pos[fill], side=side, res=res, netR=net, rr=rr,
                   R_pips=Rp, win=int(net > 0), bars=k - fill)
        if extra:
            rec["_bar"] = s["bar"]; rec["_px"] = px; rec["_stop"] = stop
        trades.append(rec)
    return pd.DataFrame(trades)


def stats(t, label=""):
    if t is None or len(t) == 0:
        return dict(arm=label, n=0, PF=np.nan, totR=np.nan, wr=np.nan, maxDD=np.nan, ER=np.nan)
    v = t.netR
    g = v[v > 0].sum(); b = -v[v < 0].sum()
    eq = v.cumsum()
    return dict(arm=label, n=len(t), PF=float(g / b) if b > 0 else np.inf,
                totR=float(v.sum()), wr=float((v > 0).mean()), ER=float(v.mean()),
                maxDD=float((eq - eq.cummax()).min()),
                med_stop=float(t.R_pips.median()), avg_rr=float(t.rr.mean()))
