"""Can ANY stop placement beat the martingale barrier probability?

The reach curve on the current entry lands on 1/(1+k) at every target - 50.1% at 1R,
32.1% at 2R, 22.9% at 3R, 17.2% at 4R, against the driftless-walk values 50.0 / 33.3 /
25.0 / 20.0.  Barrier-touch on these signals carries no edge at all; every point of the
model's profit factor comes from choosing WHERE the target is, not from the race.

That is a property of THIS (entry, stop) pair, not a law of markets.  p(+kR before -1R)
is invariant to the size of R only under a driftless walk.  Real price is not one: there
is a spread floor that punishes tiny stops, and there is genuine structure at specific
levels.  So the question is empirical and worth asking properly:

    is there any stop placement, or any pre-trade subset, where p(2R) is materially
    above 1/3?

If yes, a high-win-rate configuration exists and is worth building.
If no, the 70% target is unreachable on this signal family and the honest move is to
stop asking for it.

Stops tested, all causal and all known at entry:
    raid      the swept extreme                      (current)
    fvg_far   the far edge of the entry FVG          (tighter)
    fvg_x2    the FVG height doubled below its far edge
    atr25/50/100  fractions of ATR at the signal bar
    half/double   half and twice the current distance
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from numba import njit
from models import asia_locked as L
from models import ict_system

pd.set_option("display.width", 210); f = lambda x: f"{x:.3f}"
TARGETS = (1.0, 1.5, 2.0, 3.0)


@njit(cache=True)
def first_touch_k(bl, bh, start, px, stop, side, k, max_hold):
    """1 if +kR is touched before the stop, 0 if the stop comes first, -1 if neither."""
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


def run(syms, hold):
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
            side = sg["side"]; px = sg["ce"]
            raid = sg["sweep_px"]
            zlo, zhi = sg["zone_lo"], sg["zone_hi"]
            a = atr[sg["bar"]]
            if not np.isfinite(a) or a <= 0:
                continue
            base = (px - raid) * side
            if base <= 0:
                continue
            end = min(i0 + E["window_min"], len(pos) - 1)
            fill = -1
            for j in range(i0, end):
                if (side == 1 and al[j] <= px) or (side == -1 and ah[j] >= px):
                    fill = j; break
            if fill < 0 or pos[fill].dayofweek == 0:
                continue
            busy = fill + 60
            far = zlo if side == 1 else zhi
            cand = {
                "raid": raid,
                "fvg_far": far - side * 0.0,
                "fvg_x2": far - side * abs(zhi - zlo),
                "atr25": px - side * 0.25 * a,
                "atr50": px - side * 0.50 * a,
                "atr100": px - side * 1.00 * a,
                "half": px - side * 0.5 * base,
                "double": px - side * 2.0 * base,
            }
            for nm, st in cand.items():
                R = (px - st) * side
                if R <= 0:
                    continue
                Rp = R / unit
                row = dict(sym=s, stop=nm, Rp=Rp, cost_r=cost / Rp)
                for k in TARGETS:
                    row[f"k{k}"] = first_touch_k(bl, bh, fill, px, st, side, k,
                                                 E["max_hold"])
                rows.append(row)
    return pd.DataFrame(rows)


def report(d, nm):
    print("=" * 118)
    print(f"BARRIER RACE BY STOP PLACEMENT — {nm}")
    print("  theory for a driftless walk: p(+kR before -1R) = 1/(1+k)")
    print("=" * 118)
    print(f"{'stop':<10}{'n':>7}{'med R':>9}{'cost/R':>9}", end="")
    for k in TARGETS:
        print(f"{'p(' + str(k) + 'R)':>10}", end="")
    print(f"{'excess vs theory @2R':>23}")
    for nm2, g in d.groupby("stop"):
        n = len(g)
        line = f"{nm2:<10}{n:>7}{g.Rp.median():>9.2f}{g.cost_r.mean()*100:>8.1f}%"
        exc = 0.0
        for k in TARGETS:
            v = g[f"k{k}"]
            dec = v[v >= 0]
            p = float(dec.mean()) if len(dec) else np.nan
            line += f"{p*100:>9.1f}%"
            if k == 2.0:
                exc = (p - 1 / 3) * 100
        print(line + f"{exc:>+22.1f}pp")
    print()


if __name__ == "__main__":
    for nm, syms, hold in (("2024-2026, all 9", L.ALL, False),
                           ("2015-2023 holdout, indices", L.INDICES, True)):
        d = run(syms, hold)
        d.to_csv(rf"C:\personal\ICT_v7\reports\mart_{'hold' if hold else 'live'}.csv",
                 index=False)
        report(d, nm)
