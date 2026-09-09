"""The locked Asian-range detector, with the REVERSAL TRIGGER made parametric.

Everything about the locked model has now been varied except the detector itself.  Its
one unexamined assumption is how the reversal is confirmed:

    locked:  a candle CLOSES ABOVE THE SWING HIGH that was current at the raid
             (a full market-structure shift)

That swing high can sit a long way above the raid low, so the trigger fires late - and
"late" is exactly the shape of the two biggest failure modes measured in the forensics:
33% of losses never move 0.25R in our favour (we arrived after the move), and 634
signals never fill because price never came back.

brodenbeck `change-in-state-of-delivery.md` names the alternative directly:

    "A bullish CISD: after a down-leg sweeps liquidity, price closes ABOVE THE HIGH OF
     THE CONSECUTIVE BEARISH CANDLES that made that final low ... CISD often triggers a
     few bars EARLIER than a full MSS, so some models use CISD as the entry trigger and
     MSS as added confirmation."

trigger modes
    'mss'      close through the swing high current at the raid          (LOCKED)
    'cisd'     close through the high of the consecutive down-close run that made the
               raid extreme
    'reclaim'  close back through the raided Asian bound itself - the weakest and
               earliest confirmation
    'cisd_mss' CISD first, then require the MSS as well before entering

`trigger='mss'` reproduces models/asia_locked.py exactly; the lock test proves it.
"""
import numpy as np
import pandas as pd

from models.ict_system import ASIA_EET, KILLZONES, daily_context, session_pools, swings


def detect(df, bars, atr, ctx, asia, n=5, max_gap=40, disp_ratio=0.5,
           pools=("asia",), require_stl=False, require_bias=False,
           require_trend=False, kz=None,
           trigger="mss", max_leg=10, raid_kz=None):
    """raid_kz: optional (start, end) EET hour window the RAID must fall inside.
    The Asian range is the accumulation for the LONDON manipulation, so a raid at
    20:00 EET is not the same event as one at 10:00 - never tested until now."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n)
    day = idx.normalize()
    C = ctx.reindex(day).values
    A = asia.reindex(day).values
    hour = idx.hour
    win = KILLZONES[kz] if kz else None

    out = []
    sh = sl = np.nan
    sweep = {1: None, -1: None}
    stl = {1: np.nan, -1: np.nan}
    ah = al = np.nan

    for i in range(n + 4, N):
        if hi[i]: sh = hp[i]
        if lo[i]: sl = lp[i]
        bias, trending, pdh, pdl = C[i]
        # the Asian range is knowable only after its session closes, AND must be
        # reset outside that window - carrying a stale range into the 00:00-09:00
        # hours silently adds signals (18 of them, found by the sanity check)
        if hour[i] >= ASIA_EET[1]:
            ah, al = A[i]
        else:
            ah = al = np.nan

        for s in (1, -1):
            if sweep[s] and i - sweep[s]["bar"] > max_gap:
                sweep[s] = None; stl[s] = np.nan

        if require_bias and not np.isfinite(bias): continue
        if require_trend and trending != 1: continue

        lows, highs = [], []
        if "asia" in pools:
            if np.isfinite(al): lows.append(("asia", al))
            if np.isfinite(ah): highs.append(("asia", ah))
        if "pdhl" in pools:
            if np.isfinite(pdl): lows.append(("pdl", pdl))
            if np.isfinite(pdh): highs.append(("pdh", pdh))

        raid_ok = (raid_kz is None) or (raid_kz[0] <= hour[i] < raid_kz[1])
        for name, lv in lows:
            if l[i] < lv <= (l[i-1] if i else lv) and raid_ok \
               and (not require_bias or bias >= 0):
                if sweep[1] is None or l[i] < sweep[1]["px"]:
                    sweep[1] = dict(bar=i, px=l[i], pool=name, ref=sh, lvl=lv)
                    stl[1] = np.nan
        for name, lv in highs:
            if h[i] > lv >= (h[i-1] if i else lv) and raid_ok \
               and (not require_bias or bias <= 0):
                if sweep[-1] is None or h[i] > sweep[-1]["px"]:
                    sweep[-1] = dict(bar=i, px=h[i], pool=name, ref=sl, lvl=lv)
                    stl[-1] = np.nan

        if sweep[1] and lo[i] and i - n > sweep[1]["bar"]: stl[1] = lp[i]
        if sweep[-1] and hi[i] and i - n > sweep[-1]["bar"]: stl[-1] = hp[i]

        if np.isnan(atr[i]) or atr[i] <= 0: continue
        rng_i = max(h[i] - l[i], 1e-12)
        if abs(c[i] - o[i]) / rng_i < disp_ratio: continue

        for side in (1, -1):
            sw = sweep[side]
            if sw is None or i <= sw["bar"]: continue
            if require_bias and bias != 0 and np.sign(bias) != side: continue
            if win and not any(a <= hour[i] < b for a, b in win): continue

            # ------------------ THE REVERSAL TRIGGER --------------------------
            ref_mss = sw["ref"]
            ok = False
            ref_used = np.nan
            if trigger in ("mss", "cisd_mss"):
                if np.isfinite(ref_mss):
                    ok = (c[i] > ref_mss and c[i] > o[i]) if side == 1 \
                         else (c[i] < ref_mss and c[i] < o[i])
                    ref_used = ref_mss
            if trigger in ("cisd", "cisd_mss"):
                j = sw["bar"]
                opp = (lambda k: c[k] < o[k]) if side == 1 else (lambda k: c[k] > o[k])
                if not opp(j): j -= 1
                leg = []
                while j >= 0 and opp(j) and len(leg) < max_leg:
                    leg.append(j); j -= 1
                if leg:
                    r = max(h[k] for k in leg) if side == 1 else min(l[k] for k in leg)
                    c_ok = (c[i] > r and c[i] > o[i]) if side == 1 \
                           else (c[i] < r and c[i] < o[i])
                    if trigger == "cisd":
                        ok = c_ok; ref_used = r
                    else:
                        ok = ok and c_ok      # both required
            if trigger == "reclaim":
                lv = sw["lvl"]
                ok = (c[i] > lv and c[i] > o[i]) if side == 1 \
                     else (c[i] < lv and c[i] < o[i])
                ref_used = lv
            if not ok:
                continue
            if require_stl and not np.isfinite(stl[side]): continue

            found = None
            for k in range(sw["bar"] + 2, i + 1):
                if side == 1 and l[k] > h[k-2]: g = (h[k-2], l[k])
                elif side == -1 and h[k] < l[k-2]: g = (h[k], l[k-2])
                else: continue
                if g[1] > g[0]: found = g; break
            if found is None: continue

            out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                            ce=(found[0] + found[1]) / 2, sweep_px=sw["px"],
                            sweep_bar=sw["bar"], pool=sw["pool"], stl=stl[side],
                            pdh=pdh, pdl=pdl, ah=ah, al=al, bias=bias,
                            ref=ref_used))
            sweep[side] = None; stl[side] = np.nan
    return out
