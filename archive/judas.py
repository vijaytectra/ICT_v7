"""London Judas Swing - the setup my earlier "Asian range" model was a corrupted version of.

Read in full from SrsBlack `14-asian-range/`, `13-judas-swing/`, `04-time-cycles/`,
`15-sessions/` before writing a line of this. Every earlier version in this project got
the following five things wrong, and all five come from that one folder:

  1. THE WINDOW.  asian-range.md: "most commonly the Asian killzone 20:00 -> 00:00 NY",
     alternative "18:00 prev -> 03:00 NY".  = EET 03:00-07:00 or EET 01:00-10:00.
     The old model used EET 02:00-09:00, which is neither.
  2. WHEN THE RAID HAPPENS.  asian-range-sweep.md: "at the start of the London session -
     typically inside the London Open killzone (02:00-05:00 NY) and frequently inside the
     02:50-03:10 macro window."  = EET 09:00-12:00, macro EET 09:50-10:10.
     The old model accepted a raid at any hour of the day.
  3. WHAT A RAID IS.  "Price wicks above asian_range_high. The candle (or one of the next
     1-2 candles) closes back below. Long upper wick relative to candle range."
     The old model required only that price traded through.
  4. HOW LONG THE REVERSAL MAY TAKE.  judas-swing.md: "A reversal WITHIN THE SAME KILLZONE."
     The old model allowed 40 M15 bars - ten hours.
  5. THE TARGET LADDER.  asian-range-projections.md: ICT "counts the high of the Asian range
     as level one of four to fill", then range multiples; and states a hard ceiling -
     "Asian range can go up one or two standard deviations". So: opposite bound, then 1x
     and 2x the range. No half-steps.

Plus the stand-down rule, judas-swing-failure.md: "by 30-45 minutes into the killzone, if
the price is still extending in the initial direction without any meaningful pullback or
displacement reversal, treat the Judas hypothesis as failed."
"""
import numpy as np
import pandas as pd

# EET = New York + 7
ASIA_KZ   = (3, 7)      # 20:00-00:00 NY  - canonical killzone anchor
ASIA_FULL = (1, 10)     # 18:00 prev-03:00 NY - full session anchor
LDN_KZ    = (9, 12)     # 02:00-05:00 NY  - London open killzone
LDN_MACRO = (9.83, 10.17)   # 02:50-03:10 NY


def asian_range(df, anchor="kz"):
    """Asian high/low per day. Only usable after the window closes."""
    lo_h, hi_h = ASIA_KZ if anchor == "kz" else ASIA_FULL
    a = df[(df.index.hour >= lo_h) & (df.index.hour < hi_h)]
    g = a.groupby(a.index.normalize())
    out = pd.DataFrame({"ah": g.h_b.max(), "al": g.l_b.min()})
    out["arange"] = out.ah - out.al   # .size collides with DataFrame.size
    out["ready"] = hi_h                       # the hour from which it may be read
    return out


def detect(df, bars, atr, ar, tf_min=15, wick_frac=0.6, reclaim_bars=2,
           macro_only=False, disp_ratio=0.5, min_range=0.0, max_range=np.inf):
    """One Judas setup per side per day, at most. Everything is knowable at `bar`."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    day = idx.normalize()
    A = ar.reindex(day)
    ah, al, asz = A.ah.values, A.al.values, A.arange.values
    hourf = idx.hour.values + idx.minute.values / 60.0

    kz_lo, kz_hi = (LDN_MACRO if macro_only else LDN_KZ)
    out = []
    state = {}          # day -> dict(side, sweep_px, sweep_bar, done)
    pend = {}           # day -> (side, bar, level, extreme)

    for i in range(3, N):
        d = day[i]
        hf = hourf[i]
        if not (kz_lo <= hf < kz_hi):
            continue
        if not (np.isfinite(ah[i]) and np.isfinite(al[i])) or asz[i] <= 0:
            continue
        if not (min_range <= asz[i] <= max_range):
            continue
        rng_i = max(h[i] - l[i], 1e-12)

        st = state.get(d)
        # ---------- 2+3 : the raid, inside the London killzone ----------------
        if st is None:
            p = pend.get(d)
            if p is None:
                if h[i] > ah[i]:   pend[d] = (-1, i, ah[i], h[i])
                elif l[i] < al[i]: pend[d] = (1, i, al[i], l[i])
            else:
                side, b0, lv, ext = p
                if side == -1 and h[i] > ext: ext = h[i]
                if side == 1 and l[i] < ext:  ext = l[i]
                pend[d] = (side, b0, lv, ext)
                if i - b0 > reclaim_bars:                 # no close back -> not a sweep
                    pend.pop(d, None)
                else:
                    back = (c[i] < lv) if side == -1 else (c[i] > lv)
                    wick = ((h[i] - c[i]) if side == -1 else (c[i] - l[i])) / rng_i
                    if back and wick >= wick_frac:
                        state[d] = dict(side=side, px=ext, bar=i, sh=np.nan, sl=np.nan)
                        pend.pop(d, None)
            continue

        # ---------- 4 : the reversal, inside the SAME killzone -----------------
        side = st["side"]
        if i <= st["bar"]: continue
        body = abs(c[i] - o[i])
        if body / rng_i < disp_ratio: continue
        # displacement away from the raided bound
        if side == 1 and not (c[i] > o[i] and c[i] > al[i]): continue
        if side == -1 and not (c[i] < o[i] and c[i] < ah[i]): continue

        found = None
        for k in range(st["bar"] + 2, i + 1):
            if side == 1 and l[k] > h[k-2]:  g = (h[k-2], l[k])
            elif side == -1 and h[k] < l[k-2]: g = (h[k], l[k-2])
            else: continue
            if g[1] > g[0]: found = g; break
        if found is None: continue

        out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                        ce=(found[0] + found[1]) / 2,
                        sweep_px=st["px"], sweep_bar=st["bar"],
                        ah=ah[i], al=al[i], asize=asz[i],
                        kz_end_bar=None, day=d))
        state[d] = dict(side=side, px=st["px"], bar=st["bar"], done=True)
        state[d]["done"] = True
        # one setup per side per day
        state[d] = dict(side=0, px=np.nan, bar=i, done=True)
    return out


def targets(s, side, level):
    """asian-range-projections.md: the opposite bound is level 1 of 4; further levels are
    whole multiples of the Asian range. ICT states a hard 1-2 SD ceiling, no half-steps."""
    ah, al, sz = s["ah"], s["al"], s["asize"]
    if side == 1:
        base = ah
        return base if level == 1 else base + (level - 1) * sz
    base = al
    return base if level == 1 else base - (level - 1) * sz
