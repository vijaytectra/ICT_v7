"""What win rate is PHYSICALLY available on these signals?

The operator's target is WR 70-80% at a minimum 1:2 reward-to-risk.  Before arguing
about whether a filter can deliver it, measure the ceiling: for every signal the model
already takes, how far does price actually travel in our favour BEFORE it travels 1R
against us?

That curve is the hard limit.  No entry filter, no ML model and no confluence stack can
put a trade above its own reach curve - a filter can only choose which trades to take,
and the best any filter can do is pick the subset that reached the target.  So:

    max achievable WR at kR  =  fraction of signals whose MFE reached kR before -1R

and the profit factor that WR implies is then arithmetic, not opinion.

Measured on the real M1 path, both periods, with cost charged.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from numba import njit
from models import asia_locked as L
from models import ict_system

pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"


@njit(cache=True)
def race(bl, bh, start, px, stop, side, targets, max_hold):
    """For one trade: the largest k in `targets` reached BEFORE the stop."""
    out = -1.0
    end = min(start + max_hold, bl.shape[0] - 1)
    R = abs(px - stop)
    k = start + 1
    best = 0.0
    while k <= end:
        if side == 1:
            if bl[k] <= stop:
                break
            fav = (bh[k] - px) / R
        else:
            if bh[k] >= stop:
                break
            fav = (px - bl[k]) / R
        if fav > best:
            best = fav
        k += 1
    return best


def curve(syms, hold, targets):
    rows = []
    for s in syms:
        p = s + "_H" if hold else s
        df = pd.read_parquet(L.DATA / f"{p}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        al, ah = df.l_a.values, df.h_a.values
        bl, bh = df.l_b.values, df.h_b.values
        pos = df.index
        unit = L.UNIT[s]; cost = L.cost_for(s, hold)
        E = L.EXECUTE
        busy = -1
        for sg in sigs:
            i0 = pos.searchsorted(bars.index[sg["bar"]] + pd.Timedelta(L.TF), "left")
            if i0 >= len(pos) - 2 or i0 <= busy:
                continue
            side = sg["side"]; px = sg["ce"]; stop = sg["sweep_px"]
            R = (px - stop) * side
            if R <= 0:
                continue
            Rp = R / unit
            if cost / Rp > E["cri_max"]:
                continue
            end = min(i0 + E["window_min"], len(pos) - 1)
            fill = -1
            for j in range(i0, end):
                if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                    fill = j; break
            if fill < 0 or pos[fill].dayofweek == 0:
                continue
            best = race(bl, bh, fill, px, stop, side, targets, E["max_hold"])
            busy = fill + 60
            rows.append(dict(sym=s, t=pos[fill], side=side, Rp=Rp, mfe=best,
                             cost_r=cost / Rp))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    T = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
    for nm, syms, hold in (("2024-2026, all 9", L.ALL, False),
                           ("2015-2023 holdout, indices", L.INDICES, True)):
        d = curve(syms, hold, T)
        d.to_csv(rf"C:\personal\ICT_v7\reports\reach_{'hold' if hold else 'live'}.csv",
                 index=False)
        print("=" * 100)
        print(f"REACH CURVE — {nm}   n={len(d)} signals that filled")
        print("=" * 100)
        print(f"{'target':>8}{'reached before -1R':>21}{'= max WR':>11}"
              f"{'PF at that WR':>16}{'net PF after cost':>19}")
        for k in T:
            hit = float((d.mfe >= k).mean())
            pf = (hit * k) / max((1 - hit) * 1.0, 1e-9)
            cr = float(d.cost_r.mean())
            pfn = (hit * (k - cr)) / max((1 - hit) * (1 + cr), 1e-9)
            print(f"{k:>8.1f}{hit*100:>20.1f}%{hit*100:>10.1f}%{pf:>16.2f}{pfn:>19.2f}")
        print(f"\n  mean cost as a fraction of risk: {d.cost_r.mean()*100:.1f}%")
        print(f"  WR needed for PF 2.0 at 2R: 50.0%   at 3R: 40.0%   at 4R: 33.3%")
        print()
