"""The ICT 2022 model as the corpus actually specifies it, gated end to end.

Built from all three references after a full read, not from the Unicorn page alone.

THE SPINE - SrsBlack 31-models/ict-core-patterns.md:
    "condition -> stage -> execution ... the condition is the higher timeframe
     directional bias ... No HTF bias, no pattern."
    "If I don't see price doing these three things, I don't do anything.
     If it doesn't look this clear to me in price, I do not trade. Period."

THE SEQUENCE - SrsBlack 31-models/ict-2022-model.md, verbatim order:
    1. HTF bias clear (D/W align)
    2. Killzone window active
    3. Liquidity sweep of a KNOWN POOL (Asian range, PDH/PDL, session high/low)
    4. Displacement in the bias direction with an FVG
    5. Entry on FVG retest at CE
    6. SL beyond the swept extreme
    7. Targets via HTF draw on liquidity

WHAT EVERY EARLIER VERSION IN THIS PROJECT GOT WRONG, and this one fixes:
  * The pool.  v2-v5 swept a 3-bar swing low - minor structure, inducement. The model
    names TIME-DEFINED pools: the Asian range, the previous day's high/low, the prior
    session extreme. Those are where stops actually rest.
  * HTF bias was treated as an optional confluence. The corpus makes it gate zero.
  * Market profile was never tested. ideal-swing-conditions.md: reject a market with
    "little to no movement over the last three months" - consolidation is "a lack of
    institutional interest".
  * The short-term-low discriminator was never implemented. ict-core-patterns.md:
    "there is no short-term low in between. If there isn't, it's NOT AS HIGH PROBABILITY."
  * Targets were a fixed R. draw-on-liquidity.md requires an identifiable unswept pool
    that aligns with HTF bias, and targets-and-exits.md gates the trade on rr_planned.
"""
import numpy as np
import pandas as pd

# EET = New York + 7.
KILLZONES = {
    "LDN":  [(9, 12)],            # London open      02:00-05:00 NY
    "NYAM": [(14, 17)],           # NY AM forex      07:00-10:00 NY
    "IDXAM": [(15, 18)],          # NY AM indices    08:30-11:00 NY
    "LDN+NYAM": [(9, 12), (14, 17)],
    "LDN+IDXAM": [(9, 12), (15, 18)],
}
ASIA_EET = (2, 9)                 # Asian range 19:00-02:00 NY


def swings(h, l, n):
    """Confirmed swing points, marked at the bar they become knowable (pivot + n)."""
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        if h[i-n:i+n+1].argmax() == n: hi[i+n] = True; hp[i+n] = h[i]
        if l[i-n:i+n+1].argmin() == n: lo[i+n] = True; lp[i+n] = l[i]
    return hi, hp, lo, lp


def daily_context(df):
    """GATE 1 (bias) and GATE 2 (profile), both from completed daily candles only.

    Bias  - top-down-analysis.md tier 3: "institutional order flow on the daily is the
            most important one to know"; structure read as the direction of the most
            recent break of a confirmed daily swing.
    Profile - ideal-swing-conditions.md: reject consolidation, "a lack of institutional
            interest"; accept trending or freshly out of consolidation.
    Both are shifted one day so a bar never sees its own day.
    """
    d = df.resample("1D").agg({"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    hi, hp, lo, lp = swings(d.h_b.values, d.l_b.values, 2)
    c = d.c_b.values
    bias = np.zeros(len(d))
    last_hi = last_lo = np.nan; cur = 0
    for i in range(len(d)):
        if hi[i]: last_hi = hp[i]
        if lo[i]: last_lo = lp[i]
        if np.isfinite(last_hi) and c[i] > last_hi: cur = 1
        elif np.isfinite(last_lo) and c[i] < last_lo: cur = -1
        bias[i] = cur
    rng = (d.h_b - d.l_b).rolling(20).mean()
    move = (d.c_b - d.c_b.shift(20)).abs()
    profile = (move / (rng * 20) > 0.18).astype(int)      # directional travel vs churn
    out = pd.DataFrame({"bias": bias, "trending": profile.values,
                        "pdh": d.h_b.values, "pdl": d.l_b.values}, index=d.index).shift(1)
    return out


def session_pools(df):
    """GATE 3's pools: the Asian range extremes, carried forward through the day.
    2022-model wording: 'a known pool (Asian range, PDH/PDL, session high/low)'."""
    a = df.between_time(f"{ASIA_EET[0]:02d}:00", f"{ASIA_EET[1]:02d}:00")
    g = a.groupby(a.index.normalize())
    return pd.DataFrame({"ah": g.h_b.max(), "al": g.l_b.min()})


def detect(df, bars, atr, ctx, asia, n=5, max_gap=40, disp_ratio=0.5,
           pools=("asia", "pdhl"), require_stl=True, require_bias=True,
           require_trend=True, kz="LDN+NYAM"):
    """Returns fully-gated setups. Every value is knowable at `bar`."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n)
    day = idx.normalize()
    C = ctx.reindex(day).values                      # bias, trending, pdh, pdl
    A = asia.reindex(day).values                     # ah, al
    hour = idx.hour
    win = KILLZONES[kz] if kz else None

    out = []
    sh = sl = np.nan
    sweep = {1: None, -1: None}          # side -> dict(bar, px, pool, ob)
    stl = {1: np.nan, -1: np.nan}        # short-term low/high seen since the sweep

    for i in range(n + 4, N):
        if hi[i]: sh = hp[i]
        if lo[i]: sl = lp[i]
        bias, trending, pdh, pdl = C[i]
        # CAUSALITY: the Asian range is only knowable once the Asian session has CLOSED.
        # A bar inside 02:00-09:00 EET must not see its own session's extremes.
        if hour[i] >= ASIA_EET[1]:
            ah, al = A[i]
        else:
            ah = al = np.nan

        for s in (1, -1):
            if sweep[s] and i - sweep[s]["bar"] > max_gap: sweep[s] = None; stl[s] = np.nan

        # ---- GATE 1 + 2 : condition -------------------------------------------------
        if require_bias and not np.isfinite(bias): continue
        if require_trend and trending != 1: continue

        # ---- GATE 3 : raid of a KNOWN pool, against the bias ------------------------
        lows, highs = [], []
        if "asia" in pools:
            if np.isfinite(al): lows.append(("asia", al))
            if np.isfinite(ah): highs.append(("asia", ah))
        if "pdhl" in pools:
            if np.isfinite(pdl): lows.append(("pdl", pdl))
            if np.isfinite(pdh): highs.append(("pdh", pdh))
        for name, lv in lows:                                   # sell-side raid -> long
            if l[i] < lv <= (l[i-1] if i else lv) and (not require_bias or bias >= 0):
                if sweep[1] is None or l[i] < sweep[1]["px"]:
                    sweep[1] = dict(bar=i, px=l[i], pool=name, ref=sh); stl[1] = np.nan
        for name, lv in highs:                                  # buy-side raid -> short
            if h[i] > lv >= (h[i-1] if i else lv) and (not require_bias or bias <= 0):
                if sweep[-1] is None or h[i] > sweep[-1]["px"]:
                    sweep[-1] = dict(bar=i, px=h[i], pool=name, ref=sl); stl[-1] = np.nan

        # ---- the short-term-low discriminator ---------------------------------------
        if sweep[1] and lo[i] and i - n > sweep[1]["bar"]: stl[1] = lp[i]
        if sweep[-1] and hi[i] and i - n > sweep[-1]["bar"]: stl[-1] = hp[i]

        if np.isnan(atr[i]) or atr[i] <= 0: continue
        rng_i = max(h[i] - l[i], 1e-12)
        if abs(c[i] - o[i]) / rng_i < disp_ratio: continue

        for side in (1, -1):
            sw = sweep[side]
            if sw is None or i <= sw["bar"]: continue
            if require_bias and bias != 0 and np.sign(bias) != side: continue
            if win and not any(a <= hour[i] < b for a, b in win): continue   # GATE 4 time
            ref = sw["ref"]
            if not np.isfinite(ref): continue
            # ---- GATE 5 : displacement closing through structure --------------------
            if side == 1 and not (c[i] > ref and c[i] > o[i]): continue
            if side == -1 and not (c[i] < ref and c[i] < o[i]): continue
            # ---- the discriminator --------------------------------------------------
            if require_stl and not np.isfinite(stl[side]): continue

            # ---- GATE 6 : the FVGs the displacement left -----------------------------
            # SrsBlack fvg-classification-2025.md distinguishes them, and the distinction
            # is an entry rule: an FVG rebalanced within 1-3 bars is "immediate" and is
            # "a reading signal, NOT entry"; one unfilled for 5+ bars is "delayed" and is
            # the one you "plan and wait for". Emit all of them with age and mitigation
            # so the execution layer can choose.
            gaps = []
            for k in range(sw["bar"] + 2, i + 1):
                if side == 1 and l[k] > h[k-2]: g = (h[k-2], l[k])
                elif side == -1 and h[k] < l[k-2]: g = (h[k], l[k-2])
                else: continue
                if g[1] <= g[0]: continue
                # SrsBlack fvg-mitigation.md: once price returns to the gap it is
                # "structurally consumed and stops acting as a fresh entry zone"; the
                # 2025 framing marks that at CE.  inversion-fvg.md: a close beyond the
                # far edge flips the gap polarity, so it becomes resistance for a long.
                # All three are measured between formation (k) and the signal bar (i),
                # so they are knowable when the order is placed.
                ce_g = (g[0] + g[1]) / 2
                touch = mit_ce = inv = False
                for j in range(k + 1, i + 1):
                    if side == 1:
                        if l[j] <= g[1]: touch = True
                        if l[j] <= ce_g: mit_ce = True
                        if c[j] < g[0]:  inv = True
                    else:
                        if h[j] >= g[0]: touch = True
                        if h[j] >= ce_g: mit_ce = True
                        if c[j] > g[1]:  inv = True
                gaps.append(dict(lo=g[0], hi=g[1], bar=k, age=i - k,
                                 mitigated=touch, mit_ce=mit_ce, inverted=inv))
            if not gaps: continue
            found = (gaps[0]["lo"], gaps[0]["hi"])

            out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                            ce=(found[0] + found[1]) / 2, sweep_px=sw["px"],
                            sweep_bar=sw["bar"], pool=sw["pool"], stl=stl[side],
                            pdh=pdh, pdl=pdl, ah=ah, al=al, bias=bias, gaps=gaps,
                            ref=ref))
            sweep[side] = None; stl[side] = np.nan
    return out
