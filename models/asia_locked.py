"""LOCKED CONFIGURATION — ICT 2022 Asian-range model.

This file is the single source of truth for the setup.  Nothing here may be changed
without re-running tests/test_asia_locked.py, which pins the measured result.  If a
change moves any pinned number, the test fails and the change is rejected.

Locked 2026-09-06.  Rationale and full evidence: ASIA_MODEL_REPORT.md.

Two arms are locked, and they are tracked separately forward:
  ARM A  both sides   - the pre-registered model.  PF 1.19, P(edge>0) 0.937.
  ARM B  shorts only  - post-hoc split, but the only result in this project whose
                        confidence interval excludes zero: PF 1.34 pooled over
                        11.7 years, permutation p = 0.006.
Arm B is NOT a replacement for arm A; the forward test decides between them.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_v3, ict_bt, ict_system

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")

# ----------------------------------------------------------------- the instruments
UNIT = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "AUDUSD": 1e-4, "USDCAD": 1e-4,
        "USDCHF": 1e-4, "USDJPY": 1e-2,
        "USATECH": 1.0, "USA500": 1.0, "USA30": 1.0}
INDICES = ["USATECH", "USA500", "USA30"]
FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD"]
ALL = INDICES + FX

# ---------------------------------------------------------------------------- COST
# BUG FIXED 2026-09-06.  This used to be a flat 1.5 index points for every index and
# 0.8 pips for every FX pair, charged on top of the bid/ask already inside the fills.
# A flat number in an instrument's own quote units is not a cost - it is a different
# cost for every instrument, because the units are not comparable:
#
#     instrument   own median spread   flat charge   ratio
#     USATECH             1.504            1.50       1.00x
#     USA500              0.516            1.50       2.91x   <- charged nearly 3 spreads
#     USA30               2.534            1.50       0.59x   <- charged half a spread
#     EURUSD              0.300            0.80       2.67x   <- same problem
#     USDCAD              1.200            0.80       0.67x
#
# USA500 was being taxed 2.9 spreads on a median stop of 4.4 points, so the CRI gate
# threw away 72% of its setups (1636 valid signals -> 464) and the survivors paid up to
# a third of their risk in fees.  That, not a weak edge, is why USA500 read PF 0.63-0.98
# on 28 trades while USA30 read 1.18 on 223.  With the units fixed it is an ordinary
# instrument: 215 DEV trades at PF 1.16.
#
# The charge is now a multiple of the instrument's OWN median spread, which is the only
# unit in which "cost beyond the spread" means the same thing everywhere.  SPREAD_MULT
# represents slippage on the roughly 60% of exits that are market stop-outs, plus
# commission; IC Markets charges no commission on these CFDs (verified in the tester).
# ---- BROKER-VERIFIED COST, 2026-09-06 -------------------------------------------
# The multiplier below used to be a placeholder.  It no longer needs to be: the actual
# account is IC Markets Raw Spread, and its published schedule is
#
#     FX       USD 3.50 per lot PER SIDE  =  USD 7.00 per lot round trip
#     Indices  NO COMMISSION - spread only  (US30 1.411 pt, US500 0.492, USTEC 1.807)
#
# The broker's own symbol dump confirms the three indices share one quote unit
# (digits 2, tick_size 0.01, tick_value 0.01), which is exactly why charging a flat
# "1.5 points" to all three was wrong: it is 1.06 spreads on US30 and 3.05 on US500.
#
# Commission is quoted in ACCOUNT CURRENCY per lot, so it is a DIFFERENT number of pips
# on every pair - it has to be divided by that pair's pip value, not assumed to be 0.7
# everywhere.  For a 100k lot:  XXXUSD -> USD 10/pip;  USDXXX -> 10 / rate.
COMMISSION_USD_RT = 7.0            # per standard lot, round trip, FX only
SLIP_MULT = 0.5                    # slippage allowance, in multiples of the OWN spread

_spread = {}
_pipval = {}


def median_spread(sym, hist=False):
    """Median close-ask minus close-bid, expressed in PIPS - the same unit ict_bt.run
    divides the cost by.  Reading it in price units silently charges an FX pair a
    thousandth of its real spread."""
    key = (sym, hist)
    if key not in _spread:
        d = pd.read_parquet(DATA / f"{sym}{'_H' if hist else ''}.parquet",
                            columns=["c_b", "c_a"])
        _spread[key] = float((d.c_a - d.c_b).median()) / UNIT[sym]
    return _spread[key]


def pip_value_usd(sym):
    """USD value of one pip on one standard lot."""
    if sym in INDICES:
        return np.nan                      # commission-free, so never needed
    if sym not in _pipval:
        d = pd.read_parquet(DATA / f"{sym}.parquet", columns=["c_b"])
        rate = float(d.c_b.median())
        # pip value in the QUOTE currency = pip size x contract size = UNIT * 1e5.
        # XXXUSD quotes in USD already; USDXXX must be divided by the rate.
        _pipval[sym] = (UNIT[sym] * 1e5 if sym.endswith("USD")
                        else UNIT[sym] * 1e5 / rate)
    return _pipval[sym]


def commission_pips(sym):
    """The broker's commission, converted into that instrument's own pips."""
    if sym in INDICES:
        return 0.0                         # IC Markets charges none on index CFDs
    return COMMISSION_USD_RT / pip_value_usd(sym)


def cost_for(sym, hist=False):
    """Broker commission (measured) + a slippage allowance (declared, not measured)."""
    return commission_pips(sym) + SLIP_MULT * median_spread(sym, hist)


# kept so the pre-fix numbers can still be reproduced; do not use for new work
COST_FLAT = {**{s: 1.5 for s in INDICES}, **{s: 0.8 for s in FX}}

IS_END = pd.Timestamp("2025-07-01")

# ------------------------------------------------------------------- LOCKED PARAMS
TF = "15min"                       # structure timeframe; execution is M1

DETECT = dict(
    n=5,                           # confirmed swing needs 5 bars either side
    max_gap=40,                    # raid -> displacement window, in M15 bars
    disp_ratio=0.5,                # displacement body / (high - low)
    pools=("asia",),               # TIME-DEFINED pool only.  PDH/PDL measured 0.726
    require_stl=False,             # short-term-low discriminator: 1.05 vs 1.19
    require_bias=False,            # HTF daily bias: 1.04 vs 1.19
    require_trend=False,           # trending-profile gate: 1.00 vs 1.19
    kz=None,                       # killzone window: 1.11 vs 1.19
)

EXECUTE = dict(
    entry="ce",                    # limit at the FVG's consequent encroachment
    stop_buf=0.0,                  # stop AT the raid extreme, no buffer
    target="dol",                  # draw on liquidity, never a fixed R
    min_rr=2.0,                    # skip if the pool is closer than 2R.  Never resize
    max_rr=10.0,                   # and skip if it is FURTHER than 10R.  A 20R planned
                                   # target on a 5-pip stop is the Screen-2 degenerate
                                   # setup seen from the other end: the pool is not a
                                   # real objective, the stop is just too tight.
                                   # Stable across 8-15 (see the lock test).
    cri_max=0.20,                  # brodenbeck v4 Screen 2: cost / structural risk
    window_min=360,                # limit order valid 6 h, then cancel
    max_hold=1440,                 # 24 h fallback exit (variant A0 - lowest drawdown)

    # ---------------------------------------------- DOL REACHABILITY (added 2026-09-07)
    # The target must have been CROSSED (on a close) at least twice in the last 96 M15
    # bars.  Full evidence in DOL_REACHABILITY.md.  Selected on the three US indices
    # 2015-2023, then read once on all nine instruments 2024-2026, then confirmed on the
    # broker's own USTEC ticks in MT5 (PF 1.403 -> 1.545, drawdown -17.9R -> -10.7R, and
    # every one of the five years positive for the first time).
    #
    # This is the only filter in the project whose permutation test says it SELECTS:
    # p = 0.0002 on DEV and 0.0000 on VAL, where the R:R gate, SMT divergence and the
    # exit rules all scored around 0.25 and were merely dropping trades.  Neighbourhoods
    # are regions: lookback 24-384 bars and threshold 1-6 are all positive on both halves.
    min_target_x=2,
    x_lookback=96,
)

# ---------------------------------------------------------------- SKIP MONDAY (v2)
# Added to the lock 2026-09-06 after a causal loss-cohort scan.  Monday is the ONLY
# negative day of the week, in BOTH periods, independently:
#     2024-2026   n=76  PF 0.708  -19.0R    permutation p = 0.0315
#     2015-2023   n=81  PF 0.513  -36.3R    permutation p = 0.0047
# Every other day is positive in both.  P(the same day is worst of five in two
# independent periods) = 1/25.
#
# Mechanism, written in the sources before the data was looked at: Monday is the WEEKLY
# ACCUMULATION phase (SrsBlack weekly-range-profiles.md, monday-wednesday-range.md;
# market-maker-manipulation-template.md puts the weekly extreme on Tue/Wed and holds
# into Thursday).  Running a DAILY manipulation model on the day that is itself the
# weekly accumulation is doctrinally backwards.  Mechanically it is strongest on the
# indices, whose Monday follows a ~65-hour weekend with no cash session behind it.
#
# Applied to the FILL day, so it is decidable live: do not take an entry that fills on
# a Monday.  13 features were scanned and 10 of 14 candidate filters FAILED the
# holdout; this is the one that survived with a mechanism.  See ASIA_LOCKED.md.
SKIP_DOW = (0,)                    # 0 = Monday

# --------------------------------------------------- ARM B DETECTOR (v3, 2026-09-06)
# Arm B alone uses a different reversal trigger and a raid time window.  Arm A is
# unchanged and still runs ict_system.detect.
#
#   trigger='reclaim'  confirmation is price closing back through the RAIDED ASIAN
#                      BOUND itself, not through the swing high current at the raid.
#                      SrsBlack market-maker-trap.md variant 2: a break below
#                      consolidation that reverses IS the accumulation event;
#                      liquidity-sweep.md: "close to it without sustaining the break".
#                      A full MSS fires late - the shape of the two biggest failure
#                      modes in LOSS_FORENSICS.md.
#   raid_kz=(9, 12)    the raid must land in the LONDON killzone, 09:00-12:00 EET
#                      (02:00-05:00 NY).  The Asian range is the accumulation for the
#                      LONDON manipulation (intraday-amd.md); a raid at 20:00 EET is
#                      not a Judas swing.  Arm A accepts any hour after 09:00.
#
# SELECTED on US indices 2015-2023 only, then applied UNCHANGED to 2024-2026 and to the
# six FX majors.  Total R improved in all four slices; profit factor fell in all four.
# On ARM A the same change FAILED validation (1.294 -> 1.050) and was rejected: longs
# are the losing side (PF 0.906 over 11.7 years), so a looser trigger dilutes them.
# Full evidence in V3_RECLAIM_RESULT.md.
DETECT_B = {**DETECT, "trigger": "reclaim", "raid_kz": (9, 12)}

# arm B filter
SHORTS_ONLY = False

# ---------------------------------------------------------- KNOWN, FROZEN BEHAVIOUR
# Documented rather than "fixed", because it is inside the measured result and
# changing it would invalidate the pinned numbers.
#
# The raid-to-displacement window is 40 M15 bars = 10 hours, so a raid late in one
# session can produce its signal after midnight, before the NEXT session's Asian range
# has closed.  ict_system.detect only refreshes `ah`/`al` at hour >= 09:00 EET, so such
# a signal carries the last completed session's levels - and carries NaN when the last
# completed "session" was a weekend with no 02:00-09:00 data.  When they are NaN the
# draw-on-liquidity target falls back to PDH/PDL alone.  This is causal (nothing future
# is read; the prefix-invariance test proves it) and it is part of the locked
# behaviour.  Do not silently change it.


# ------------------------------------------------------------------------- pipeline
_cache = {}


def load(sym):
    if sym not in _cache:
        _cache[sym] = pd.read_parquet(DATA / f"{sym}.parquet")
    return _cache[sym]


def resample(df, tf=TF):
    b = df[["o_b", "h_b", "l_b", "c_b"]].resample(tf).agg(
        {"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    return b, tr.rolling(14).mean().values


def trades(sym, shorts_only=SHORTS_ONLY, cost=None, skip_dow=SKIP_DOW,
           **over):
    """The locked model on one instrument.  `over` is for the robustness sweeps only
    (cost multiples, R:R gate); it must never be used to pick a better number."""
    df = load(sym)
    bars, atr = resample(df)
    ctx = ict_system.daily_context(df)
    asia = ict_system.session_pools(df)
    if shorts_only:
        sigs = asia_v3.detect(df, bars, atr, ctx, asia, **DETECT_B)
    else:
        sigs = ict_system.detect(df, bars, atr, ctx, asia, **DETECT)
    kw = dict(EXECUTE)
    kw["cost"] = cost_for(sym) if cost is None else cost
    kw.update(over)
    kw.setdefault("stf_close", bars.c_b.values)
    t = ict_bt.run(df, sigs, bars.index, UNIT[sym], pd.Timedelta(TF), **kw)
    if len(t) and skip_dow:
        t = t[~t.t.dt.dayofweek.isin(skip_dow)].reset_index(drop=True)
    if len(t) and shorts_only:
        t = t[t.side == -1].reset_index(drop=True)
    return t


def portfolio(syms=ALL, shorts_only=SHORTS_ONLY, **kw):
    """kw passes through to trades(), including skip_dow= for the lock test."""
    out = []
    for s in syms:
        t = trades(s, shorts_only, **kw)
        if len(t):
            t = t.copy(); t["sym"] = s
            out.append(t)
    return (pd.concat(out).sort_values("t").reset_index(drop=True) if out
            else pd.DataFrame())


# --------------------------------------------------------------------------- stats
def pf(v):
    v = np.asarray(v)
    g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


def bootstrap(v, iters=8000, seed=11):
    v = np.asarray(v)
    if len(v) < 10:
        return np.nan, (np.nan, np.nan)
    r = np.random.default_rng(seed)
    m = v[r.integers(0, len(v), (iters, len(v)))].mean(1)
    return float((m > 0).mean()), (float(np.percentile(m, 2.5)),
                                   float(np.percentile(m, 97.5)))


def summarise(t, label=""):
    if t is None or len(t) == 0:
        return None
    v = t.netR.values
    eq = t.netR.cumsum()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0
        mx = max(mx, s)
    p, ci = bootstrap(v)
    return dict(arm=label, n=len(t), wr=float((t.out == 1).mean()),
                ER=float(v.mean()), PF=pf(v), totR=float(v.sum()),
                maxDD=float((eq - eq.cummax()).min()), lose_streak=mx,
                avg_rr=float(t.rr.mean()), med_stop=float(t.R_pips.median()),
                med_hold=int(t.bars.median()), P_edge=p,
                ci_lo=ci[0], ci_hi=ci[1])
