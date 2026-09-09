"""Exit-architecture experiment. ENTRY LOGIC IS FROZEN.

The detector, the entry price, the stop, the R:R gate and the cost gate are byte-identical
to the baseline that produced PF 1.189 / +68.9R / 471 trades. The only thing that varies
below the entry fill is how the position is managed out.

Definitions fixed BEFORE looking at any result, and not tuned:
  IRL  the NEARER of the two candidate pools in the trade direction (previous-day extreme,
       Asian-range extreme). SrsBlack internal-range-liquidity.md: IRL is "the staging or
       partial-take zone".
  ERL  the FURTHER of the two. Same page: ERL is "the full-delivery destination".
       If only one pool exists, IRL and ERL are that same level.
  partial fraction = 0.50, as briefed. Not swept.
  BE trigger = the moment the IRL partial fills. No offset, no buffer.
  EOD = 23:00 EET on the entry day (New York session close); if the entry is later than
       that, the next 23:00. Applied identically to every variant.

Variants
  A   TP at the chosen target / SL / EOD                (target = IRL, the current rule)
  A0  the literal current baseline: 24h max-hold fallback instead of EOD
  B   50% at IRL, 50% runs to ERL, EOD fallback
  C   50% at IRL, stop to break-even on that fill, 50% to ERL, EOD fallback
  D   100% to ERL, EOD fallback
"""
import numpy as np
import pandas as pd

EOD_HOUR = 23           # EET; New York close


def _pools(s, side, px):
    cand = []
    for key in (("pdh", "ah") if side == 1 else ("pdl", "al")):
        v = s.get(key)
        if v is not None and np.isfinite(v) and ((v > px) if side == 1 else (v < px)):
            cand.append(float(v))
    if not cand:
        return None, None
    irl = min(cand) if side == 1 else max(cand)
    erl = max(cand) if side == 1 else min(cand)
    return irl, erl


def run(df, sigs, bar_index, pip, tf_delta, variant="A", cost=0.0,
        min_rr=2.0, max_rr=10.0, cri_max=0.20, partial=0.50,
        window_min=360, max_hold=1440):
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h, bi_c = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index
    hour = pos.hour.values
    daynum = (pos.normalize().astype("int64") // 86_400_000_000_000).astype(np.int64)
    trades = []
    busy = -1

    for s in sigs:
        i0 = pos.searchsorted(bar_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        side = s["side"]
        px = s["ce"]                                   # FROZEN: entry at FVG CE
        stop0 = s["sweep_px"]                          # FROZEN: swept extreme
        R = (px - stop0) * side
        if R <= 0: continue
        Rp = R / pip
        if cost > 0 and cri_max > 0 and cost / Rp > cri_max: continue     # FROZEN cost gate

        irl, erl = _pools(s, side, px)
        if irl is None: continue
        rr_irl = side * (irl - px) / R
        rr_erl = side * (erl - px) / R
        if rr_irl < min_rr: continue                   # FROZEN R:R gate (measured on IRL)
        if max_rr and rr_irl > max_rr: continue

        end = min(i0 + window_min, len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px):
                fill = j; break
        if fill < 0: continue

        # ---- exit clock -------------------------------------------------------
        if variant == "A0":
            limit = min(fill + max_hold, len(pos) - 1)
        else:
            d0 = daynum[fill] + (1 if hour[fill] >= EOD_HOUR else 0)
            limit = fill
            while limit + 1 < len(pos) and not (daynum[limit + 1] > d0 or
                    (daynum[limit + 1] == d0 and hour[limit + 1] >= EOD_HOUR)):
                limit += 1
            limit = min(limit, len(pos) - 1)

        stop = stop0
        got1 = False
        res = None
        k = fill + 1
        mfe = mae = 0.0
        while k <= limit:
            fav = side * ((bi_h[k] if side == 1 else bi_l[k]) - px) / R
            adv = side * ((bi_l[k] if side == 1 else bi_h[k]) - px) / R
            if fav > mfe: mfe = fav
            if adv < mae: mae = adv
            hit_stop = (bi_l[k] <= stop) if side == 1 else (bi_h[k] >= stop)
            if hit_stop:
                res = "be" if (got1 and variant == "C") else "stop"; break
            if variant in ("A", "A0"):
                if (bi_h[k] >= irl) if side == 1 else (bi_l[k] <= irl): res = "tp"; break
            else:
                if not got1 and variant in ("B", "C"):
                    if (bi_h[k] >= irl) if side == 1 else (bi_l[k] <= irl):
                        got1 = True
                        if variant == "C": stop = px               # break-even on the runner
                if (bi_h[k] >= erl) if side == 1 else (bi_l[k] <= erl): res = "tp"; break
            k += 1
        if res is None: res = "eod"
        busy = k

        # ---- payoff -----------------------------------------------------------
        if variant in ("A", "A0"):
            gross = rr_irl if res == "tp" else (-1.0 if res == "stop"
                    else side * (bi_c[min(k, len(bi_c)-1)] - px) / R)
        elif variant == "D":
            gross = rr_erl if res == "tp" else (-1.0 if res == "stop"
                    else side * (bi_c[min(k, len(bi_c)-1)] - px) / R)
        else:  # B and C
            runner = (rr_erl if res == "tp" else
                      (0.0 if res == "be" else
                       (-1.0 if res == "stop" else side * (bi_c[min(k, len(bi_c)-1)] - px) / R)))
            if got1:
                gross = partial * rr_irl + (1 - partial) * runner
            else:
                gross = runner
        net = gross - cost / Rp
        trades.append(dict(t=pos[fill], side=side, sym=None, res=res, netR=net,
                           gross=gross, R_pips=Rp, rr_irl=rr_irl, rr_erl=rr_erl,
                           mfe=mfe, mae=mae, bars=k - fill, partial_hit=int(got1)))
    return pd.DataFrame(trades)


def metrics(t, label, is_end):
    if len(t) == 0: return None
    n = len(t)
    win = t.netR > 0
    g = t.netR[win].sum(); b = -t.netR[~win].sum()
    eq = t.netR.cumsum(); dd = float((eq - eq.cummax()).min())
    m = t.set_index("t").netR.resample("ME").sum()
    sharpe = float(m.mean() / m.std() * np.sqrt(12)) if m.std() > 0 else np.nan
    dn = m[m < 0]
    sortino = float(m.mean() / dn.std() * np.sqrt(12)) if len(dn) > 1 and dn.std() > 0 else np.nan
    i = t[t.t <= is_end]; o = t[t.t > is_end]
    pf = lambda x: float(x.netR[x.netR > 0].sum() / max(-x.netR[x.netR < 0].sum(), 1e-9))
    return dict(variant=label, trades=n, PF=float(g / b) if b > 0 else np.inf,
                ER=float(t.netR.mean()), totR=float(t.netR.sum()), maxDD=dd,
                RdD=float(t.netR.sum() / -dd) if dd < 0 else np.nan,
                Sharpe=sharpe, Sortino=sortino,
                TPpct=float((t.res == "tp").mean()), EODpct=float((t.res.isin(["eod"])).mean()),
                avg_win=float(t.netR[win].mean()) if win.any() else np.nan,
                avg_loss=float(t.netR[~win].mean()) if (~win).any() else np.nan,
                MFE=float(t.mfe.mean()), MAE=float(t.mae.mean()),
                IS_PF=pf(i) if len(i) > 5 else np.nan,
                OOS_PF=pf(o) if len(o) > 5 else np.nan)
