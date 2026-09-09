"""Record the per-trade favourable/adverse excursion of the frozen Unicorn population.

Once this exists any exit rule can be re-scored without re-running the backtest, which is
what made the Asian-range exit work trustworthy.  Entry, stop and fill are exactly the
locked ones; only the exit is left open.
"""
import pathlib, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.uni_arms import _C, frame, IDX


def paths(per, kz="IDX", window_min=360, max_hold=1440, cri_max=0.0, cost=1.5):
    from models.unicorn_lab import KZ
    win = KZ[kz]
    rows = []
    for sym in IDX:
        c = _C[(per, sym)]; df = frame(per, sym)
        ai_l, ai_h = df.l_a.values, df.h_a.values
        bi_l, bi_h, bi_c = df.l_b.values, df.h_b.values, df.c_b.values
        pos = df.index; hr = pos.hour
        busy = -1
        for s in c["sigs"]:
            i0 = pos.searchsorted(c["bars"][s["bar"]] + pd.Timedelta("15min"), "left")
            if i0 >= len(pos) - 2 or i0 <= busy: continue
            side = s["side"]; px = s.get("mt", (s["zone_lo"] + s["zone_hi"]) / 2)
            stop = s["sweep_px"]; R = (px - stop) * side
            if R <= 0: continue
            if cri_max > 0 and cost / R > cri_max: continue
            end = min(i0 + window_min, len(pos) - 1); fill = -1
            for j in range(i0, end):
                if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px): fill = j; break
            if fill < 0: continue
            if win and not any(a <= hr[fill] < b for a, b in win): continue
            k1 = min(fill + max_hold, len(pos) - 1)
            fav = side * ((bi_h[fill+1:k1+1] if side == 1 else bi_l[fill+1:k1+1]) - px) / R
            adv = side * ((bi_l[fill+1:k1+1] if side == 1 else bi_h[fill+1:k1+1]) - px) / R
            cls = side * (bi_c[fill+1:k1+1] - px) / R
            if len(fav) == 0: continue
            # the bar the stop would first be hit, in minutes after the fill
            hit = np.argmax(adv <= -1.0) + 1 if (adv <= -1.0).any() else 10**6
            rows.append(dict(sym=sym, t=pos[fill], side=side, R_pips=R,
                             fav=fav.astype(np.float32), adv=adv.astype(np.float32),
                             cls=cls.astype(np.float32), stop_min=hit))
            # non-overlap: advance past whichever of stop/target would end it soonest,
            # resolved later by the replay; use the stop bar as the conservative bound
            busy = fill + min(hit, max_hold)
    return rows


if __name__ == "__main__":
    out = {}
    for per in ("DEV", "VAL"):
        out[per] = paths(per)
        print(per, len(out[per]), "paths", flush=True)
    with open(r"C:\personal\ICT_v7\reports\uni_paths.pkl", "wb") as f:
        pickle.dump(out, f)
