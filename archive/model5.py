"""ICT Price Action Model 5 - Day Trading, transcribed from ICT's own trade plan.

Source: `chart_content/013 - ICT Charter Price Action Model 5 - Trade Plan.en.vtt`,
his words, not a summary. None of the three reference repositories carries this model.

    "ICT price action model number five day trade plan, 40 to 50 pips per trade."

  PREPARATION
    "determine the IPDA data range of the last 20 days ... we don't count Sundays,
     so we're going to be noting the highest high and the lowest low in the past 20
     trading days and this is going to be your CURRENT DEALING RANGE."
    "inside this dealing range we will look for the next draw on liquidity - where is
     price likely to trade to next, above a previous day's high or below a previous
     day's low, MINIMUM OF 40 PIPS."

  OPPORTUNITY
    "identify the previous day low or an intraweek low when the bias is bearish;
     the previous day high or an intraweek high when the bias is bullish."

  TRADE PLANNING
    "we will SHORT PREMIUM fair value gap and BUY DISCOUNT fair value gap setups."
    "when we are bearish we will frame a short entry when the price has moved up into
     a 15-MINUTE PREMIUM fair value gap PD array that converges with a standard
     deviation of NO MORE THAN THREE standard deviations, during LONDON OPEN or
     NEW YORK OPEN."  (bullish mirrors, into a 15-minute discount FVG)
    "whether you use the Central Bank Dealers Range, the Asian range or flout."

Two things every earlier version of this project had wrong and this fixes:
  * Premium/discount was measured against a rolling 60-bar window. ICT measures it
    against the 20-trading-day IPDA dealing range, Sundays excluded. Different object.
  * There was no cap on how far the entry sits from the session range. ICT caps it at
    three standard deviations of the Asian range / CBDR.

EET = New York + 7.  London open KZ 09:00-12:00 EET, NY open KZ 14:00-17:00 EET.
"""
import numpy as np
import pandas as pd

LDN_OPEN = (9, 12)
NY_OPEN = (14, 17)
ASIA = (3, 7)          # 20:00-00:00 NY, the killzone anchor


def ipda_range(df, days=20):
    """The dealing range: highest high / lowest low of the last `days` trading days,
    Sundays excluded. Shifted so a bar never sees its own day."""
    d = df.resample("1D").agg({"h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    d = d[d.index.dayofweek != 6]                       # "we don't count Sundays"
    out = pd.DataFrame({
        "ih": d.h_b.rolling(days).max(),
        "il": d.l_b.rolling(days).min(),
        "pdh": d.h_b, "pdl": d.l_b, "pdc": d.c_b,
    }).shift(1)
    out["equil"] = (out.ih + out.il) / 2   # .eq collides with DataFrame.eq                   # premium above, discount below
    return out


def asian_stats(df):
    a = df[(df.index.hour >= ASIA[0]) & (df.index.hour < ASIA[1])]
    g = a.groupby(a.index.normalize())
    r = pd.DataFrame({"ah": g.h_b.max(), "al": g.l_b.min()})
    r["amid"] = (r.ah + r.al) / 2
    r["asd"] = r.ah - r.al                              # one "standard deviation" unit
    return r


def detect(df, bars, ipda, asia, pip, min_draw_pips=40.0, max_sd=3.0,
           sessions=("LDN", "NY"), disp_ratio=0.0, require_pd=True):
    """M15 FVG entries, gated exactly as the trade plan states."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    day = idx.normalize()
    I = ipda.reindex(day); A = asia.reindex(day)
    ih, il, eq = I.ih.values, I.il.values, I.equil.values
    pdh, pdl = I.pdh.values, I.pdl.values
    amid, asd = A.amid.values, A.asd.values
    hr = idx.hour.values
    win = []
    if "LDN" in sessions: win.append(LDN_OPEN)
    if "NY" in sessions: win.append(NY_OPEN)

    out = []
    for i in range(3, len(c)):
        if not any(a <= hr[i] < b for a, b in win): continue
        if not (np.isfinite(ih[i]) and np.isfinite(il[i]) and ih[i] > il[i]): continue
        if not (np.isfinite(amid[i]) and asd[i] > 0): continue
        if hr[i] < ASIA[1]: continue                     # Asian range must have closed
        rng = max(h[i] - l[i], 1e-12)
        if disp_ratio and abs(c[i] - o[i]) / rng < disp_ratio: continue

        # the M15 fair value gap completing on this bar
        for side in (1, -1):
            if side == 1 and not (l[i] > h[i-2]): continue
            if side == -1 and not (h[i] < l[i-2]): continue
            g_lo, g_hi = (h[i-2], l[i]) if side == 1 else (h[i], l[i-2])
            if g_hi <= g_lo: continue
            ce = (g_lo + g_hi) / 2

            # "buy DISCOUNT fair value gap, short PREMIUM fair value gap"
            if require_pd:
                if side == 1 and ce > eq[i]: continue
                if side == -1 and ce < eq[i]: continue
            # "converges with a standard deviation of no more than three"
            if abs(ce - amid[i]) > max_sd * asd[i]: continue

            # the draw: previous day high (bullish) / low (bearish), min distance
            draw = pdh[i] if side == 1 else pdl[i]
            if not np.isfinite(draw): continue
            if (draw - ce) * side < min_draw_pips * pip: continue

            out.append(dict(bar=i, side=side, zone_lo=g_lo, zone_hi=g_hi, ce=ce,
                            draw=draw, eq=eq[i], ih=ih[i], il=il[i],
                            amid=amid[i], asd=asd[i]))
    return out
