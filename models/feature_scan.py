"""Systematic search for more filters of the same class as the reachability gate.

The reachability gate worked because it measured a property of the TARGET that nothing else
in the model looked at. This module computes every other structural property I can define
causally at the moment the order is placed, so each can be put through the same test rather
than guessed at one at a time.

EVERY feature here is computed from M15 bars at or before the signal bar, plus values the
detector already carries (all of which are themselves causal - the previous day's levels are
shifted a day, the Asian range is only read after it closes). Nothing reads forward.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L, asia_dev, ict_bt, ict_system


def features(sym, hist):
    df, b, sigs = asia_dev.prep(sym, hist)
    o, h, l, c = b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values
    idx = b.index
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    atr = tr.rolling(14).mean().values
    hi_s, hp, lo_s, lp = ict_system.swings(h, l, 5)
    day = idx.normalize()
    out = {}
    for s in sigs:
        i, side, sb = s["bar"], s["side"], s["sweep_bar"]
        px, stop = s["ce"], s["sweep_px"]
        R = (px - stop) * side
        if R <= 0 or not np.isfinite(atr[i]) or atr[i] <= 0: continue
        pool = [s.get(k) for k in (("pdh", "ah") if side == 1 else ("pdl", "al"))]
        pool = [v for v in pool if v is not None and np.isfinite(v)
                and ((v > px) if side == 1 else (v < px))]
        if not pool: continue
        tgt = min(pool) if side == 1 else max(pool)
        A = atr[i]
        f = {}

        def crossings(level, lb):
            j0 = max(0, i - lb); sd = c[j0:i + 1] > level
            return int(np.sum(sd[1:] != sd[:-1]))

        # ---- TARGET properties -------------------------------------------------------
        f["x_tgt"]      = crossings(tgt, 96)                       # the locked gate
        f["x_tgt_48"]   = crossings(tgt, 48)
        f["tgt_atr"]    = side * (tgt - px) / A                    # distance in volatility
        # how long since price last traded AT the target
        touch = np.where((h[max(0,i-480):i+1] >= tgt) & (l[max(0,i-480):i+1] <= tgt))[0]
        f["tgt_age"]    = (len(c[max(0,i-480):i+1]) - 1 - touch[-1]) if len(touch) else 999
        # confirmed swings sitting between entry and target - structure in the way
        w0 = max(0, i - 192)
        sw = [hp[j] for j in range(w0, i + 1) if hi_s[j]] + [lp[j] for j in range(w0, i + 1) if lo_s[j]]
        sw = [v for v in sw if np.isfinite(v)]
        lo_b, hi_b = (px, tgt) if side == 1 else (tgt, px)
        f["path_swings"] = sum(1 for v in sw if lo_b < v < hi_b)
        # is the target the extreme of the recent range, or inside it?
        rh, rl = h[w0:i + 1].max(), l[w0:i + 1].min()
        f["tgt_pos"]    = (tgt - rl) / max(rh - rl, 1e-9)

        # ---- STOP properties ---------------------------------------------------------
        f["x_stop"]     = crossings(stop, 96)                      # is the stop in a busy zone?
        f["stop_atr"]   = R / A

        # ---- RAID properties ---------------------------------------------------------
        lvl = s.get("al") if side == 1 else s.get("ah")
        f["raid_atr"]   = (abs(lvl - stop) / A) if (lvl is not None and np.isfinite(lvl)) else np.nan
        ah, al = s.get("ah"), s.get("al")
        f["asia_atr"]   = ((ah - al) / A) if (ah is not None and al is not None
                                              and np.isfinite(ah) and np.isfinite(al)) else np.nan
        # has the OTHER side of the Asian range also been taken today? (seek and destroy)
        d0 = np.searchsorted(day.values, day.values[i], "left")
        if ah is not None and al is not None and np.isfinite(ah) and np.isfinite(al):
            other = (h[d0:i + 1] > ah).any() if side == 1 else (l[d0:i + 1] < al).any()
            f["both_swept"] = int(bool(other))
        else:
            f["both_swept"] = np.nan
        # how many separate raids of our own level already today
        own = (l[d0:i + 1] < al) if side == 1 else (h[d0:i + 1] > ah)
        f["raids_today"] = int(np.sum(own[1:] & ~own[:-1])) if len(own) > 1 else 0

        # ---- LEG / TIMING ------------------------------------------------------------
        f["leg_bars"]   = i - sb
        f["hour"]       = idx[i].hour
        f["disp_body"]  = abs(c[i] - o[i]) / max(h[i] - l[i], 1e-9)
        f["leg_atr"]    = abs(c[i] - stop) / A
        # where the entry sits inside the sweep-to-signal leg: 0 at the sweep, 1 at the close
        span = abs(c[i] - stop)
        f["entry_in_leg"] = (abs(px - stop) / span) if span > 1e-9 else np.nan
        # how much of the day's usual range is already used
        rng20 = np.nanmedian([h[k] - l[k] for k in range(max(0, d0 - 20 * 96), d0, 96)]) if d0 > 96 else np.nan
        f["day_used"]   = (h[d0:i + 1].max() - l[d0:i + 1].min()) / A

        # ---- REGIME ------------------------------------------------------------------
        past = atr[max(0, i - 480):i + 1]
        past = past[np.isfinite(past)]
        f["atr_pct"]    = float((past < A).mean()) if len(past) > 20 else np.nan

        out[(i, side)] = f
    return out, (df, b, sigs)


def book(syms, hist):
    rows = []
    for sym in syms:
        F, (df, b, sigs) = features(sym, hist)
        t = ict_bt.run(df, sigs, b.index, L.UNIT[sym], pd.Timedelta(L.TF),
                       **{**L.EXECUTE, "cost": L.cost_for(sym, hist),
                          "stf_close": b.c_b.values, "min_target_x": 0, "extra": ["pool"]})
        if not len(t): continue
        t = t.assign(sym=sym)
        keys = sorted({k for v in F.values() for k in v})
        for k in keys:
            t[k] = [F.get((int(bb), int(sd)), {}).get(k, np.nan)
                    for bb, sd in zip(t["_bar"], t["side"])]
        rows.append(t)
    r = pd.concat(rows)
    if L.SKIP_DOW: r = r[~r.t.dt.dayofweek.isin(L.SKIP_DOW)]
    return r.reset_index(drop=True)


if __name__ == "__main__":
    D = book(L.INDICES, True); D.to_csv(r"C:\personal\ICT_v7\reports\scan_dev.csv", index=False)
    print("DEV", len(D), flush=True)
    V = book(L.ALL, False);    V.to_csv(r"C:\personal\ICT_v7\reports\scan_val.csv", index=False)
    print("VAL", len(V))
    print("done")
