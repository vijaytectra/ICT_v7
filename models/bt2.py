"""Backtest for unicorn_v2. Signals are detected once; every gate that depends only on
the entry price (premium/discount, OTE, killzone, RR) is applied here as a filter, so an
ablation is cheap and every arm sees the identical signal population."""
import numpy as np, pandas as pd

KZ = {"LDN": [(9, 12)], "NY": [(14, 17)], "LDN+NY": [(9, 12), (14, 17)]}  # EET (= NY + 7)

def run(df, sigs, stf_index, pip, tf_delta, entry_mode="edge", stop_mode="sweep",
        rr=1.0, kz=None, pd_gate=None, ote=False, comm_pips=0.0,
        window_min=240, max_hold=1440):
    al, ah = df.l_a.values, df.h_a.values
    bl, bh = df.l_b.values, df.h_b.values
    pos = df.index; hr = pos.hour
    tr = []; busy = -1
    for s in sigs:
        i0 = pos.searchsorted(stf_index[s["bar"]] + tf_delta, "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        lo, hi, side = s["zone_lo"], s["zone_hi"], s["side"]
        px = (hi if side == 1 else lo) if entry_mode == "edge" else (lo + hi) / 2

        if pd_gate is not None:                                   # R10 premium/discount
            rl, rh = s["rng_lo"], s["rng_hi"]
            if not np.isfinite(rl) or rh <= rl: continue
            p = (px - rl) / (rh - rl)
            if side == 1 and p > pd_gate: continue
            if side == -1 and p < 1 - pd_gate: continue
        if ote:                                                   # R11 OTE 62-79%
            L = s["leg_hi"] - s["leg_lo"]
            if L <= 0: continue
            r_ = (s["leg_hi"] - px) / L if side == 1 else (px - s["leg_lo"]) / L
            if not (0.62 <= r_ <= 0.79): continue

        if stop_mode == "sweep":   stop = s["sweep_px"]           # R15 widest
        elif stop_mode == "zone":  stop = lo if side == 1 else hi #    tightest
        else:                      stop = s["mss_origin"]         #    middle
        R = (px - stop) if side == 1 else (stop - px)
        if R <= 0: continue
        tp = px + rr * R if side == 1 else px - rr * R

        end = min(i0 + window_min, len(pos) - 1); fill = -1
        for j in range(i0, end):
            if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                fill = j; break
        if fill < 0: continue
        if kz and not any(a <= hr[fill] < b for a, b in KZ[kz]): continue   # R12 killzone

        out = 0; k = fill + 1; stop_end = min(fill + max_hold, len(pos) - 1)
        while k <= stop_end:
            if side == 1:
                if bl[k] <= stop: out = -1; break
                if bh[k] >= tp:   out = 1;  break
            else:
                if bh[k] >= stop: out = -1; break
                if bl[k] <= tp:   out = 1;  break
            k += 1
        busy = k
        Rp = R / pip
        netR = (rr - comm_pips / Rp) if out == 1 else (-(1 + comm_pips / Rp) if out == -1 else -comm_pips / Rp)
        tr.append(dict(t=pos[fill], side=side, R_pips=Rp, out=out, netR=netR, bars=k - fill))
    return pd.DataFrame(tr)


def summarise(t, label=""):
    if len(t) == 0: return None
    d = t[t.out != 0]; k = int((t.out == 1).sum()); n = len(t)
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    z = 1.96; p = k / n; dd = 1 + z*z/n
    ctr = (p + z*z/(2*n))/dd; hw = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/dd
    return dict(arm=label, trades=n, wr=p, wl=ctr-hw, wh=ctr+hw,
                ER=float(t.netR.mean()), PF=float(g/b) if b > 0 else np.inf,
                totR=float(t.netR.sum()), med_R_pips=float(t.R_pips.median()),
                med_hold=int(t.bars.median()), timeouts=int((t.out == 0).sum()))
