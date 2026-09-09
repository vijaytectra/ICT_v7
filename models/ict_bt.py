"""Execution for ict_system.detect.

Entry  - 2022 model step 5, "entry on FVG retest at CE (per 2025 default)".
Stop   - step 6, beyond the swept extreme. stop-placement.md: the swept extreme is the
         "protected" level - "if the model's premise is true the algorithm should not
         revisit it".
Target - step 7 plus draw-on-liquidity.md: an identifiable, UNSWEPT pool that aligns
         with HTF bias. targets-and-exits.md gates the trade: "if rr_planned < min_rr the
         setup is skipped even if every other box is checked."

Fills are on 1m bid/ask: a long enters at ASK, exits on BID; a short mirrors. Both
barriers inside one bar counts as a loss. One position at a time.
"""
import numpy as np
import pandas as pd


def run(df, sigs, bar_index, pip, tf_delta, entry="ce", stop_buf=0.0,
        target="dol", rr_fixed=2.0, min_rr=2.0, max_rr=0.0, cost=0.0,
        cri_max=0.20, window_min=360, max_hold=1440, exit_rr=None, cap_rr=None, extra=None,
        stf_close=None, min_target_x=0, x_lookback=96):
    """cri_max is brodenbeck v4 Screen 2: cost / structural risk must stay <= 20%.
    Without it the population fills with degenerate setups whose FVG midpoint sits on
    the sweep low - a sub-pip stop, an RR in the hundreds, and a 2% win rate."""
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h = df.l_b.values, df.h_b.values
    pos = df.index
    trades = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        side = s["side"]
        px = s["ce"] if entry == "ce" else (s["zone_hi"] if side == 1 else s["zone_lo"])
        stop = s["sweep_px"] - side * stop_buf * pip
        R = (px - stop) * side
        if R <= 0: continue
        Rp0 = R / pip
        if cost > 0 and cri_max > 0 and cost / Rp0 > cri_max: continue   # CRI gate

        # ---- target: the draw on liquidity, or a fixed R -------------------------
        if target == "dol":
            pool = []
            for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
                v = s.get(key)
                if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
                    pool.append(v)
            if not pool: continue
            tp = min(pool) if side == 1 else max(pool)

            # ---- DRAW-ON-LIQUIDITY REACHABILITY (DOL_REACHABILITY.md) ---------------
            # How many times has price CLOSED across this target in the last x_lookback
            # structure bars?  Zero means price spent the whole window on one side of it,
            # so the trade is reaching for liquidity it has not been near all day - the
            # model's premise is not in play.  Causal: every close is at or before the
            # signal bar, and the target itself is the prior day's level or the closed
            # Asian range.  Measured 2015-2026: DEV PF 1.233 -> 1.576, VAL 1.367 -> 1.712,
            # with MORE total R, a higher win rate and half the drawdown. Permutation
            # p = 0.0002 / 0.0000, so it selects trades rather than merely dropping them.
            if min_target_x > 0 and stf_close is not None:
                j0 = max(0, s["bar"] - x_lookback)
                sd = stf_close[j0:s["bar"] + 1] > tp
                if int(np.sum(sd[1:] != sd[:-1])) < min_target_x: continue

            rr = side * (tp - px) / R
            if rr < min_rr: continue                       # the R:R gate - skip, never resize
            if max_rr and rr > max_rr: continue
            # analysis-only overrides.  Both default to None so the locked config is
            # untouched.  They keep the DOL population and change ONLY where the
            # target is placed, which is the clean way to ask "would a flat 3R do?"
            if exit_rr is not None:
                rr = exit_rr; tp = px + side * rr * R
            elif cap_rr is not None and rr > cap_rr:
                rr = cap_rr; tp = px + side * rr * R
        else:
            rr = rr_fixed
            tp = px + side * rr * R

        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px):
                fill = j; break
        if fill < 0: continue

        out = 0; k = fill + 1
        stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if side == 1:
                if bi_l[k] <= stop: out = -1; break
                if bi_h[k] >= tp:   out = 1;  break
            else:
                if bi_h[k] >= stop: out = -1; break
                if bi_l[k] <= tp:   out = 1;  break
            k += 1
        busy = k
        Rp = R / pip
        net = (rr - cost / Rp) if out == 1 else (-(1 + cost / Rp) if out == -1 else -cost / Rp)
        rec = dict(t=pos[fill], side=side, pool=s["pool"], R_pips=Rp, rr=rr,
                   out=out, netR=net, bars=k - fill)
        if extra:                      # analysis only; default None = locked behaviour
            rec["_bar"] = s["bar"]; rec["_sweep_bar"] = s["sweep_bar"]
            rec["_fill_i"] = fill; rec["_px"] = px
            for key in extra:
                rec[key] = s.get(key)
        trades.append(rec)
    return pd.DataFrame(trades)


def stats(t, label=""):
    if len(t) == 0: return None
    n = len(t); w = int((t.out == 1).sum())
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    z = 1.96; p = w / n; d = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / d
    hw = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    eq = t.netR.cumsum(); dd = float((eq - eq.cummax()).min())
    return dict(arm=label, n=n, wr=p, wl=ctr - hw, wh=ctr + hw,
                ER=float(t.netR.mean()), PF=float(g / b) if b > 0 else np.inf,
                totR=float(t.netR.sum()), maxDD=dd, avg_rr=float(t.rr.mean()),
                med_stop=float(t.R_pips.median()), med_hold=int(t.bars.median()),
                timeouts=int((t.out == 0).sum()))
