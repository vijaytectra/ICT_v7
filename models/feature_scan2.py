"""Second feature batch - the mechanical rules mined from the ICT transcripts.

All of them measure a property of the TARGET, the PATH to it, or the day's prior behaviour,
which is the only class of filter that has ever worked here.  Same rules as batch one:
computed at or before the signal bar, nothing reads forward, and each is scored by
permutation with a Bonferroni threshold.

The one to watch is `rejects`.  The locked gate counts how often price CROSSED the target.
ICT claims the opposite - a level price approached and was REPELLED from is the stronger
magnet, because that is where the stops pile up.  Both cannot be right, and computing them
side by side either sharpens the gate or explains it.
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
    daynum = pd.Series(day).rank(method="dense").values      # trading-session index
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
        A = atr[i]; f = {}
        w = max(0, i - 96)

        # ---- the challenge to the locked gate ---------------------------------------
        # REJECTIONS: bars whose extreme came within 0.25 ATR of the target but whose
        # CLOSE stayed on our side of it.  Price reached for the level and was repelled.
        seg_h, seg_l, seg_c = h[w:i+1], l[w:i+1], c[w:i+1]
        near = 0.25 * A
        if side == 1:
            approached = seg_h >= (tgt - near); held = seg_c < tgt
        else:
            approached = seg_l <= (tgt + near); held = seg_c > tgt
        f["rejects"] = int(np.sum(approached & held))
        f["reject_frac"] = f["rejects"] / max(len(seg_c), 1)

        # ---- target age in TRADING SESSIONS (the 20/40/60 IPDA lookback) -------------
        touched = np.where((seg_h >= tgt) & (seg_l <= tgt))[0]
        f["tgt_sessions"] = (daynum[i] - daynum[w + touched[-1]]) if len(touched) else 99

        # ---- minimum room to target: the untested half of the band -------------------
        f["room_atr"] = side * (tgt - px) / A

        # ---- opposing breaker in the path (trapped order flow) ----------------------
        lo_b, hi_b = (px, tgt) if side == 1 else (tgt, px)
        opp = 0
        for j in range(max(0, i - 192), i + 1):
            if side == 1 and hi_s[j] and np.isfinite(hp[j]) and lo_b < hp[j] < hi_b:
                # a bearish breaker for a long: swing high later violated to the downside
                if (c[j:i+1] < hp[j]).any(): opp += 1
            if side == -1 and lo_s[j] and np.isfinite(lp[j]) and lo_b < lp[j] < hi_b:
                if (c[j:i+1] > lp[j]).any(): opp += 1
        f["path_opp"] = opp

        # ---- seek and destroy: both sides swept AND we are entering near the middle --
        ah, al = s.get("ah"), s.get("al")
        d0 = int(np.searchsorted(day.values, day.values[i], "left"))
        if ah is not None and al is not None and np.isfinite(ah) and np.isfinite(al) and ah > al:
            other = (h[d0:i+1] > ah).any() if side == 1 else (l[d0:i+1] < al).any()
            mid = (px - al) / (ah - al)
            f["seek_destroy"] = int(bool(other) and 0.35 <= mid <= 0.65)
            f["asia_atr"] = (ah - al) / A
            # the raid-sequence gate: was the OPPOSING pool already taken today?
            f["opp_taken"] = int(bool(other))
        else:
            f["seek_destroy"] = f["asia_atr"] = f["opp_taken"] = np.nan

        # ---- entry inside the PREVIOUS DAY's range (not the setup swing) -------------
        pdh, pdl = s.get("pdh"), s.get("pdl")
        if pdh is not None and pdl is not None and np.isfinite(pdh) and np.isfinite(pdl) and pdh > pdl:
            pos = (px - pdl) / (pdh - pdl)
            f["pd_pos"] = pos if side == 1 else 1.0 - pos
        else:
            f["pd_pos"] = np.nan

        # ---- sweep overshoot beyond the raided level, in ATR ------------------------
        lvl = al if side == 1 else ah
        f["overshoot"] = (abs(lvl - stop) / A) if (lvl is not None and np.isfinite(lvl)) else np.nan

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
        for k in sorted({k for v in F.values() for k in v}):
            t[k] = [F.get((int(bb), int(sd)), {}).get(k, np.nan)
                    for bb, sd in zip(t["_bar"], t["side"])]
        rows.append(t)
    r = pd.concat(rows)
    if L.SKIP_DOW: r = r[~r.t.dt.dayofweek.isin(L.SKIP_DOW)]
    return r.reset_index(drop=True)


if __name__ == "__main__":
    D = book(L.INDICES, True); D.to_csv(r"C:\personal\ICT_v7\reports\scan2_dev.csv", index=False)
    print("DEV", len(D), flush=True)
    V = book(L.ALL, False);    V.to_csv(r"C:\personal\ICT_v7\reports\scan2_val.csv", index=False)
    print("VAL", len(V)); print("done")
