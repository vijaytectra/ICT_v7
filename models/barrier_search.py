"""Search for selection that lifts p(+2R before -1R) from 1/3 toward 1/2.

The reframing that makes this the right experiment:

    the locked model wins 33.6% of its trades at an AVERAGE PLANNED TARGET of 3.69R.
    A driftless walk would win 1/(1+3.69) = 21.3% of those.  The model's selection is
    therefore already worth about +12.3 percentage points of barrier probability.

    PF 2.0 at a 2R target needs a 50% win rate, which is +16.7pp over the 33.3% base.
    The gap between what selection already delivers and what is being asked for is
    roughly 4 percentage points - a measurable distance, not a wall.

The target metric here is NOT profit factor.  It is a single probability measured on the
real M1 path, which is far harder to overfit than a P&L curve: a filter either lifts the
race or it does not, and it has to do it in both periods.

Every feature is knowable before the fill.  No outcome information builds a filter.
"""
import sys

import numpy as np
import pandas as pd
from numba import njit

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

pd.set_option("display.width", 220)
K = 2.0                                   # the barrier that was specified
BASE = 1.0 / (1.0 + K)                    # 33.33% for a driftless walk


@njit(cache=True)
def race(bl, bh, start, px, stop, side, k, max_hold):
    R = abs(px - stop)
    tp = px + side * k * R
    end = min(start + max_hold, bl.shape[0] - 1)
    i = start + 1
    while i <= end:
        if side == 1:
            if bl[i] <= stop:
                return 0
            if bh[i] >= tp:
                return 1
        else:
            if bh[i] >= stop:
                return 0
            if bl[i] <= tp:
                return 1
        i += 1
    return -1


def build(syms, hold):
    rows = []
    for s in syms:
        p = s + "_H" if hold else s
        df = pd.read_parquet(L.DATA / f"{p}.parquet")
        bars, atr = L.resample(df)
        ctx = ict_system.daily_context(df)
        asia = ict_system.session_pools(df)
        sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
        al, ah = df.l_a.values, df.h_a.values
        bl, bh = df.l_b.values, df.h_b.values
        o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
        pos = df.index
        unit = L.UNIT[s]
        cost = L.cost_for(s, hold)
        E = L.EXECUTE
        med_atr = np.nanmedian(atr[np.isfinite(atr)])
        busy = -1
        for sg in sigs:
            b = sg["bar"]
            i0 = pos.searchsorted(bars.index[b] + pd.Timedelta(L.TF), "left")
            if i0 >= len(pos) - 2 or i0 <= busy:
                continue
            side = sg["side"]
            px = sg["ce"]
            stop = sg["sweep_px"]
            R = (px - stop) * side
            if R <= 0:
                continue
            Rp = R / unit
            if cost / Rp > E["cri_max"]:
                continue
            a = atr[b]
            if not np.isfinite(a) or a <= 0:
                continue
            end = min(i0 + E["window_min"], len(pos) - 1)
            fill = -1
            for j in range(i0, end):
                if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                    fill = j
                    break
            if fill < 0 or pos[fill].dayofweek == 0:
                continue
            busy = fill + 60
            res = race(bl, bh, fill, px, stop, side, K, E["max_hold"])
            if res < 0:
                continue

            aw = (sg["ah"] - sg["al"]) if (np.isfinite(sg["ah"])
                                           and np.isfinite(sg["al"])) else np.nan
            wide = aw if (aw is not np.nan and aw and aw > 0) else np.nan
            depth = (((sg["al"] - stop) if side == 1 else (stop - sg["ah"])) / wide
                     if wide == wide else np.nan)
            epos = (((px - sg["al"]) if side == 1 else (sg["ah"] - px)) / wide
                    if wide == wide else np.nan)
            pool = []
            for key in (("pdh", "ah") if side == 1 else ("pdl", "al")):
                v = sg.get(key)
                if v is not None and np.isfinite(v):
                    if (v > px) if side == 1 else (v < px):
                        pool.append(v)
            tgt = (min(pool) if side == 1 else max(pool)) if pool else np.nan
            rr = side * (tgt - px) / R if tgt == tgt else np.nan
            stl = np.float64(sg["stl"]) if sg["stl"] is not None else np.nan

            rows.append(dict(
                sym=s, t=pos[fill], side=side, win=res, Rp=Rp, cost_r=cost / Rp,
                rr_pool=rr, R_atr=R / a, atr_pct=a / med_atr,
                asia_w_atr=(wide / a if wide == wide else np.nan),
                depth=depth, entry_pos=epos,
                lag=b - sg["sweep_bar"],
                fvg_atr=(sg["zone_hi"] - sg["zone_lo"]) / a,
                disp=abs(c[b] - o[b]) / max(h[b] - l[b], 1e-12),
                raid_h=bars.index[sg["sweep_bar"]].hour,
                sig_h=bars.index[b].hour, fill_h=pos[fill].hour,
                dow=pos[fill].dayofweek,
                bias_agree=int(np.sign(sg["bias"]) == side),
                has_stl=int(stl == stl),
                pool_n=len(pool)))
    return pd.DataFrame(rows)


CUTS = [
    ("rr_pool >= 2.5", lambda d: d.rr_pool >= 2.5),
    ("rr_pool >= 3.0", lambda d: d.rr_pool >= 3.0),
    ("rr_pool >= 4.0", lambda d: d.rr_pool >= 4.0),
    ("rr_pool 2 to 3", lambda d: d.rr_pool.between(2, 3)),
    ("R_atr >= 1.0", lambda d: d.R_atr >= 1.0),
    ("R_atr <= 0.6", lambda d: d.R_atr <= 0.6),
    ("cost_r <= 0.08", lambda d: d.cost_r <= 0.08),
    ("atr_pct >= 1.2", lambda d: d.atr_pct >= 1.2),
    ("atr_pct <= 0.9", lambda d: d.atr_pct <= 0.9),
    ("asia_w_atr <= 3", lambda d: d.asia_w_atr <= 3),
    ("asia_w_atr >= 4", lambda d: d.asia_w_atr >= 4),
    ("depth <= 0.10", lambda d: d.depth <= 0.10),
    ("depth >= 0.20", lambda d: d.depth >= 0.20),
    ("entry_pos <= 0.15", lambda d: d.entry_pos <= 0.15),
    ("entry_pos >= 0.30", lambda d: d.entry_pos >= 0.30),
    ("lag <= 5", lambda d: d.lag <= 5),
    ("lag >= 15", lambda d: d.lag >= 15),
    ("fvg_atr >= 0.5", lambda d: d.fvg_atr >= 0.5),
    ("fvg_atr <= 0.15", lambda d: d.fvg_atr <= 0.15),
    ("disp >= 0.8", lambda d: d.disp >= 0.8),
    ("raid in LDN 9-12", lambda d: d.raid_h.between(9, 11)),
    ("raid in NY 15-18", lambda d: d.raid_h.between(15, 17)),
    ("fill 14-18", lambda d: d.fill_h.between(14, 17)),
    ("bias agrees", lambda d: d.bias_agree == 1),
    ("bias disagrees", lambda d: d.bias_agree == 0),
    ("no short-term low", lambda d: d.has_stl == 0),
    ("two pools ahead", lambda d: d.pool_n >= 2),
    ("longs", lambda d: d.side == 1),
    ("shorts", lambda d: d.side == -1),
]


def score(d, mask, lab, floor=30):
    g = d[mask(d).fillna(False)]
    if len(g) < floor:
        return None
    p = float(g.win.mean())
    return dict(cut=lab, n=len(g), p=p, lift=(p - BASE) * 100,
                pf=(p * K) / max((1 - p), 1e-9))


if __name__ == "__main__":
    f = lambda x: f"{x:.3f}"
    dev = build(L.INDICES, True)
    val = build(L.ALL, False)
    dev.to_csv(r"C:\personal\ICT_v7\reports\barrier_dev.csv", index=False)
    val.to_csv(r"C:\personal\ICT_v7\reports\barrier_val.csv", index=False)
    print("=" * 118)
    print(f"BARRIER SEARCH at k={K}R.   driftless-walk base = {BASE*100:.1f}%")
    print(f"  DEV  indices 2015-2023   n={len(dev)}   p={dev.win.mean()*100:.1f}%")
    print(f"  VAL  all nine 2024-2026  n={len(val)}   p={val.win.mean()*100:.1f}%")
    print("  PF 2.0 needs p = 50.0%")
    print("=" * 118)
    rows = []
    for lab, fn in CUTS:
        a = score(dev, fn, lab)
        b = score(val, fn, lab)
        if a and b:
            rows.append(dict(cut=lab, dev_n=a["n"], dev_p=a["p"] * 100,
                             val_n=b["n"], val_p=b["p"] * 100,
                             dev_lift=a["lift"], val_lift=b["lift"],
                             dev_pf=a["pf"], val_pf=b["pf"]))
    r = pd.DataFrame(rows).sort_values("dev_p", ascending=False)
    r.to_csv(r"C:\personal\ICT_v7\reports\barrier_single.csv", index=False)
    print(r.to_string(index=False, float_format=f))
    ok = r[(r.dev_lift > 3) & (r.val_lift > 3)]
    print(f"\n  lift > 3pp in BOTH periods: {len(ok)} of {len(r)}")
    if len(ok):
        print(ok.to_string(index=False, float_format=f))
