"""Three models from the reference set that this project never touched.

Chosen after a full inventory of the 30 models in SrsBlack `31-models/`: all three are
`ICT Confidence: high`, all three carry a Formula/Math block precise enough to code
without judgement, and none overlaps the Unicorn / 2022 / MMXM work already done.

VENOM  `31-models/venom-model.md`, timeframes M1/M5/M15.
    "Pre-cash-open range - high and low formed during 08:00-09:30 NY (before US equities
     cash open). Sweep one bound. False breakout. Reversal back through the pre-open range
     with displacement. Target - opposite side of the pre-open range, then HTF DOL.
     Window: ~90 minutes from 09:30 -> 11:00 NY captures most of the play."
    This matters here because it is INDEX-NATIVE: it anchors on the US equities cash open.
    Everything tested so far anchored on the Asian range, which is a forex reference that
    was being applied to indices.

NDOG   `31-models/ndog.md`
    "prior_close = close at 17:00 NY of prior day; tdo = open at 00:00 NY of current day;
     ndog_zone = [min, max]".  CE (50% of the zone) is the reactive line -
    consequent-encroachment.md: "the institutional reference line price respects even
    after the gap itself has been traded through."

NWOG   `31-models/nwog.md`
    Friday NY close -> Sunday/Monday open. "larger and more reliable as fill-targets
    than NDOGs because of the longer weekend window."

EET = New York + 7 throughout.
"""
import numpy as np
import pandas as pd

VENOM_PRE = (15.0, 16.5)     # 08:00-09:30 NY
VENOM_PLAY = (16.5, 18.0)    # 09:30-11:00 NY
NDOG_CLOSE_H = 0             # 17:00 NY = 00:00 EET
NDOG_OPEN_H = 7              # 00:00 NY = 07:00 EET


# ---------------------------------------------------------------- VENOM
def venom_range(df):
    a = df[(df.index.hour + df.index.minute / 60 >= VENOM_PRE[0]) &
           (df.index.hour + df.index.minute / 60 < VENOM_PRE[1])]
    g = a.groupby(a.index.normalize())
    r = pd.DataFrame({"ph": g.h_b.max(), "pl": g.l_b.min()})
    r["psize"] = r.ph - r.pl
    return r


def venom(df, bars, pr, wick_frac=0.6, reclaim_bars=2, disp_ratio=0.5):
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    day = idx.normalize()
    P = pr.reindex(day)
    ph, pl, psz = P.ph.values, P.pl.values, P.psize.values
    hf = idx.hour.values + idx.minute.values / 60.0
    out, state, pend = [], {}, {}
    for i in range(3, len(c)):
        if not (VENOM_PLAY[0] <= hf[i] < VENOM_PLAY[1]): continue
        if not (np.isfinite(ph[i]) and np.isfinite(pl[i])) or psz[i] <= 0: continue
        d = day[i]; rng = max(h[i] - l[i], 1e-12)
        st = state.get(d)
        if st is None:
            p = pend.get(d)
            if p is None:
                if h[i] > ph[i]: pend[d] = (-1, i, ph[i], h[i])
                elif l[i] < pl[i]: pend[d] = (1, i, pl[i], l[i])
            else:
                side, b0, lv, ext = p
                ext = max(ext, h[i]) if side == -1 else min(ext, l[i])
                pend[d] = (side, b0, lv, ext)
                if i - b0 > reclaim_bars: pend.pop(d, None)
                else:
                    back = (c[i] < lv) if side == -1 else (c[i] > lv)
                    wick = ((h[i] - c[i]) if side == -1 else (c[i] - l[i])) / rng
                    if back and wick >= wick_frac:
                        state[d] = dict(side=side, px=ext, bar=i); pend.pop(d, None)
            continue
        side = st["side"]
        if i <= st["bar"] or side == 0: continue
        if abs(c[i] - o[i]) / rng < disp_ratio: continue
        if side == 1 and not (c[i] > o[i] and c[i] > pl[i]): continue
        if side == -1 and not (c[i] < o[i] and c[i] < ph[i]): continue
        found = None
        for k in range(st["bar"] + 2, i + 1):
            if side == 1 and l[k] > h[k-2]: g = (h[k-2], l[k])
            elif side == -1 and h[k] < l[k-2]: g = (h[k], l[k-2])
            else: continue
            if g[1] > g[0]: found = g; break
        if found is None: continue
        out.append(dict(bar=i, side=side, ce=(found[0] + found[1]) / 2,
                        sweep_px=st["px"], tgt1=(ph[i] if side == 1 else pl[i]),
                        tgt2=(ph[i] + psz[i]) if side == 1 else (pl[i] - psz[i])))
        state[d] = dict(side=0, px=np.nan, bar=i)
    return out


# ---------------------------------------------------------------- NDOG / NWOG
def gap_levels(df, kind="ndog"):
    """Returns per-day (or per-week) gap zone and its consequent encroachment."""
    if kind == "ndog":
        cl = df[df.index.hour == NDOG_CLOSE_H].groupby(df[df.index.hour == NDOG_CLOSE_H]
                 .index.normalize()).c_b.last()
        op = df[df.index.hour == NDOG_OPEN_H].groupby(df[df.index.hour == NDOG_OPEN_H]
                 .index.normalize()).o_b.first()
        z = pd.DataFrame({"a": cl, "b": op}).dropna()
        z["ready_h"] = NDOG_OPEN_H + 1
    else:
        wk = df.index.to_period("W")
        last = df.groupby(wk).c_b.last()
        first = df.groupby(wk).o_b.first()
        start = df.groupby(wk).apply(lambda x: x.index[0].normalize(), include_groups=False)
        z = pd.DataFrame({"a": last.shift().values, "b": first.values},
                         index=pd.DatetimeIndex(start.values)).dropna()
        z["ready_h"] = 2
    z["lo"] = z[["a", "b"]].min(axis=1); z["hi"] = z[["a", "b"]].max(axis=1)
    z["ce"] = (z.lo + z.hi) / 2
    z["size"] = z.hi - z.lo
    return z[["lo", "hi", "ce", "size", "ready_h"]]


def gap_touch(df, bars, z, kind="ndog", carry_days=1, disp_ratio=0.5, min_size=0.0):
    """Trade the reaction at the gap's CE. Entry limit at CE, direction from which side
    price approaches it, stop beyond the far edge of the gap zone."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    day = idx.normalize()
    Z = z.reindex(day, method="ffill")
    lo_, hi_, ce_, sz_, rd_ = Z.lo.values, Z.hi.values, Z.ce.values, Z["size"].values, Z.ready_h.values
    hr = idx.hour.values
    age = (day - pd.DatetimeIndex(Z.index)).days if hasattr(Z.index, "days") else None
    out, used = [], set()
    for i in range(3, len(c)):
        if not np.isfinite(ce_[i]) or sz_[i] <= min_size: continue
        if hr[i] < rd_[i]: continue
        key = (day[i], round(float(ce_[i]), 6))
        if key in used: continue
        if abs(c[i] - o[i]) / max(h[i] - l[i], 1e-12) < disp_ratio: continue
        # approach from above -> short at CE ; from below -> long at CE
        if l[i] <= ce_[i] <= h[i]:
            side = 1 if c[i] > ce_[i] else -1
            stop = lo_[i] if side == 1 else hi_[i]
            if (ce_[i] - stop) * side <= 0: continue
            out.append(dict(bar=i, side=side, ce=float(ce_[i]), sweep_px=float(stop),
                            tgt1=float(hi_[i] if side == 1 else lo_[i]),
                            tgt2=float(hi_[i] + sz_[i]) if side == 1 else float(lo_[i] - sz_[i])))
            used.add(key)
    return out
