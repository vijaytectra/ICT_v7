"""Excursion recorder for the Asian-range model on any instrument set.

Same entry, stop, fill and gates as ict_bt.run. Only the exit is left open: for every
filled trade store the per-minute favourable and adverse excursion in R, plus the planned
R:R the DOL target implied. Any exit rule can then be scored exactly, and the reach curve -
how often price gets to xR before the stop - can be read off directly.
"""
import pathlib, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L, asia_dev


def paths(sym, hist, cost=None, max_hold=1440, window_min=360, min_rr=None):
    df, bars, sigs = asia_dev.prep(sym, hist)
    pip = L.UNIT[sym]; c = L.cost_for(sym, hist) if cost is None else cost
    E = L.EXECUTE
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h, bi_c = df.l_b.values, df.h_b.values, df.c_b.values
    pos = df.index; out = []; busy = -1
    for s in sigs:
        i0 = pos.searchsorted(bars.index[s["bar"]] + pd.Timedelta(L.TF), "left")
        if i0 >= len(pos) - 2 or i0 <= busy: continue
        side = s["side"]; px = s["ce"]; stop = s["sweep_px"]
        R = (px - stop) * side
        if R <= 0: continue
        Rp = R / pip
        if c > 0 and E["cri_max"] > 0 and c / Rp > E["cri_max"]: continue
        pool = [s.get(k) for k in (("pdh", "ah") if side == 1 else ("pdl", "al"))]
        pool = [v for v in pool if v is not None and np.isfinite(v)
                and ((v > px) if side == 1 else (v < px))]
        if not pool: continue
        tp = min(pool) if side == 1 else max(pool)
        rr = side * (tp - px) / R
        # DOL REACHABILITY (see DOL_REACHABILITY.md): how many times has price CLOSED
        # across the target in the last 96 M15 bars?  Zero means price spent a whole day
        # on one side of it - the trade is reaching for liquidity it has not been near.
        cb = bars.c_b.values
        j0 = max(0, s["bar"] - 96)
        sdd = cb[j0:s["bar"] + 1] > tp
        xings = int(np.sum(sdd[1:] != sdd[:-1]))
        lo_rr = E["min_rr"] if min_rr is None else min_rr
        if rr < lo_rr or (E["max_rr"] and rr > E["max_rr"]): continue
        end = min(i0 + window_min, len(pos) - 1); fill = -1
        for j in range(i0, end):
            if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px): fill = j; break
        if fill < 0: continue
        k1 = min(fill + max_hold, len(pos) - 1)
        fav = side * ((bi_h[fill+1:k1+1] if side == 1 else bi_l[fill+1:k1+1]) - px) / R
        adv = side * ((bi_l[fill+1:k1+1] if side == 1 else bi_h[fill+1:k1+1]) - px) / R
        cls = side * (bi_c[fill+1:k1+1] - px) / R
        if len(fav) == 0: continue
        j = np.argmax(adv <= -1.0) + 1 if (adv <= -1.0).any() else 10**6
        out.append(dict(sym=sym, t=pos[fill], side=side, rr=rr, cost_R=c / Rp, xings=xings,
                        R_pips=Rp, dow=pos[fill].dayofweek,
                        fav=fav.astype(np.float32), adv=adv.astype(np.float32),
                        cls=cls.astype(np.float32)))
        busy = fill + min(j, max_hold)
    return out


def score(rows, target="dol", cap=0.0, floor_rr=0.0, be_at=0.0,
          soft_min=0, soft_r=0.0, max_hold=1440, skip_monday=True, min_x=0):
    """Replay one exit rule over recorded paths. Returns netR per trade."""
    res = []
    for r in rows:
        if skip_monday and r["dow"] == 0: continue
        if min_x and r.get("xings", 99) < min_x: continue
        rr = r["rr"]
        if floor_rr and rr < floor_rr: continue
        t = rr if target == "dol" else float(target)
        if cap and t > cap: t = cap
        fav, adv, cls = r["fav"], r["adv"], r["cls"]
        n = min(len(fav), max_hold)
        stop = -1.0; g = None
        for i in range(n):
            if adv[i] <= stop: g = stop if stop < 0 else 0.0; break
            if fav[i] >= t: g = t; break
            if be_at and stop < 0 and fav[i] >= be_at: stop = 0.0
            if soft_min and i + 1 == soft_min and cls[i] <= soft_r: g = float(cls[i]); break
        if g is None: g = float(cls[n-1])
        res.append(dict(sym=r["sym"], t=r["t"], netR=g - r["cost_R"], planned=rr))
    return pd.DataFrame(res)


if __name__ == "__main__":
    store = {}
    for tag, syms, hist in (("DEV", L.INDICES, True), ("VAL", L.ALL, False)):
        rows = []
        for s in syms:
            p = paths(s, hist, min_rr=1.5); rows += p
            print(f"{tag} {s}: {len(p)}", flush=True)
        store[tag] = rows
    with open(r"C:\personal\ICT_v7\reports\asia_paths_x.pkl", "wb") as f:
        pickle.dump(store, f)
    print("done")


def score_partial(rows, p1_at=1.0, p1_frac=0.5, be_after_p1=True, floor_rr=1.5,
                  cap=0.0, max_hold=1440, skip_monday=True, min_x=0):
    """Scale out `p1_frac` of the position at +p1_at R, optionally move the stop to
    break-even, and let the runner go to the dynamic draw-on-liquidity target.

    This is the only mechanism that legitimately raises the WIN RATE: a trade that
    reaches p1_at and then reverses now finishes positive instead of at -1R. It does
    not create expectancy - the runner gives back what the partial banks - so both
    numbers must always be reported together.
    """
    res = []
    for r in rows:
        if skip_monday and r["dow"] == 0: continue
        if min_x and r.get("xings", 99) < min_x: continue
        rr = r["rr"]
        if floor_rr and rr < floor_rr: continue
        t = min(rr, cap) if cap else rr
        fav, adv, cls = r["fav"], r["adv"], r["cls"]
        n = min(len(fav), max_hold)
        stop = -1.0
        banked = 0.0          # R already realised on the part taken off
        live = 1.0            # fraction still open
        out = None
        for i in range(n):
            if adv[i] <= stop:
                out = banked + live * stop; break
            if fav[i] >= t:
                out = banked + live * t; break
            if live > (1.0 - p1_frac) + 1e-9 and fav[i] >= p1_at:
                banked += p1_frac * p1_at
                live -= p1_frac
                if be_after_p1: stop = 0.0
            i += 0
        if out is None: out = banked + live * float(cls[n - 1])
        res.append(dict(sym=r["sym"], t=r["t"], netR=out - r["cost_R"], planned=rr))
    return pd.DataFrame(res)
