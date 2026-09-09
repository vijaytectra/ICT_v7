"""Pinned result for the LOCKED Asian-range model.  Re-pinned 2026-09-07.

Any change to the model, the execution layer, the cost model or the data that moves a single
number below makes this test FAIL - which is the point.

Two deliberate changes were absorbed on 2026-09-06/07 and the numbers re-pinned afterwards:

  COST UNITS.  `COST` used to charge a flat 1.5 index points / 0.8 pips to every instrument,
  which is a different cost on each one because the quote units are not comparable - USA500
  paid 2.91x its own spread while USA30 paid 0.59x.  It is now
  `SPREAD_MULT * median_spread(sym)`.

  DOL REACHABILITY.  The draw-on-liquidity target must have been crossed on a close at least
  `min_target_x` times in the last `x_lookback` structure bars.  See DOL_REACHABILITY.md;
  permutation p = 0.0002 on the development set and 0.0000 on validation.

Together they took arm A from PF 1.294 to 1.539 with the out-of-sample half (1.572) now ahead
of the in-sample half (1.515), P(edge>0) from 98.3% to 99.8%, and the confidence interval on
expectancy clear of zero.  ARM B (shorts only) is now WORSE than arm A - 1.333 against 1.539 -
so the shorts-only split should not be traded.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

TOL = 1e-4

# ------------------------------------------------------- THE PINNED RESULT (frozen)
ARM_A = dict(n=268, wr=0.335821, ER=0.389989, PF=1.538895, totR=104.517024,
             maxDD=-19.919494, lose_streak=10, avg_rr=3.689298, med_stop=10.200000,
             med_hold=21, P_edge=0.998375, ci_lo=0.132195, ci_hi=0.660282)
ARM_A_ISOOS = dict(is_n=152, is_PF=1.514862, oos_n=116, oos_PF=1.571885)

# ARM B moved to the v3 detector (reclaim trigger + London-killzone raid) 2026-09-06
ARM_B = dict(n=283, wr=0.293286, ER=0.255686, PF=1.332910, totR=72.359058,
             maxDD=-29.563973, lose_streak=11, avg_rr=4.118532, med_stop=9.800000,
             med_hold=48, P_edge=0.976125, ci_lo=0.002841, ci_hi=0.518050)
ARM_B_ISOOS = dict(is_n=162, is_PF=1.316943, oos_n=121, oos_PF=1.354691)
PER_SYM_B = {"AUDUSD": 12, "EURUSD": 26, "GBPUSD": 34, "USA30": 49, "USA500": 55,
             "USATECH": 54, "USDCAD": 8, "USDCHF": 15, "USDJPY": 30}

PER_SYM = {"AUDUSD": 9, "EURUSD": 27, "GBPUSD": 23, "USA30": 73, "USA500": 62,
           "USATECH": 42, "USDCAD": 7, "USDCHF": 13, "USDJPY": 12}

# max_rr must remain a REGION, not a point.  If any of these drifts below 1.15 the
# parameter has become fitted and the lock must be reviewed.
MAX_RR_REGION = {6.0: 1.4982, 8.0: 1.5651, 10.0: 1.5389, 12.0: 1.5714, 15.0: 1.6264}

# the skip-Monday rule, and the cohort it removes
MONDAY = dict(n=56, PF=0.471, floor=1.15)


def _cmp(got, want, label, tol=TOL):
    fails = []
    for k, v in want.items():
        g = got.get(k)
        if g is None:
            fails.append(f"{label}.{k} missing"); continue
        if isinstance(v, int) and not isinstance(v, bool):
            if g != v:
                fails.append(f"{label}.{k}: {g} != pinned {v}")
        elif abs(g - v) > tol:
            fails.append(f"{label}.{k}: {g:.6f} != pinned {v:.6f}")
    return fails


def test_arm_a():
    t = L.portfolio()
    f = _cmp(L.summarise(t), ARM_A, "ARM_A")
    got = dict(zip(*np.unique(t.sym, return_counts=True)))
    for s, n in PER_SYM.items():
        if int(got.get(s, 0)) != n:
            f.append(f"ARM_A per-sym {s}: {got.get(s,0)} != pinned {n}")
    i, o = t[t.t < L.IS_END], t[t.t >= L.IS_END]
    f += _cmp(dict(is_n=len(i), is_PF=L.pf(i.netR.values),
                   oos_n=len(o), oos_PF=L.pf(o.netR.values)),
              ARM_A_ISOOS, "ARM_A")
    return f


def test_arm_b():
    t = L.portfolio(shorts_only=True)
    f = _cmp(L.summarise(t), ARM_B, "ARM_B")
    got = dict(zip(*np.unique(t.sym, return_counts=True)))
    for s, n in PER_SYM_B.items():
        if int(got.get(s, 0)) != n:
            f.append(f"ARM_B per-sym {s}: {got.get(s,0)} != pinned {n}")
    # Arm B must be running the v3 detector, Arm A must NOT be
    if L.DETECT_B.get("trigger") != "reclaim" or L.DETECT_B.get("raid_kz") != (9, 12):
        f.append("ARM_B detector config drifted from reclaim / raid_kz (9,12)")
    if "trigger" in L.DETECT:
        f.append("ARM_A detector must stay on ict_system.detect (no trigger key)")
    i, o = t[t.t < L.IS_END], t[t.t >= L.IS_END]
    f += _cmp(dict(is_n=len(i), is_PF=L.pf(i.netR.values),
                   oos_n=len(o), oos_PF=L.pf(o.netR.values)),
              ARM_B_ISOOS, "ARM_B")
    return f


def test_max_rr_is_a_region():
    """A real parameter has a neighbourhood.  If only max_rr=10 works, it is fitted."""
    f = []
    for m, want in MAX_RR_REGION.items():
        got = L.pf(L.portfolio(max_rr=m).netR.values)
        if abs(got - want) > 1e-3:
            f.append(f"max_rr={m}: PF {got:.4f} != pinned {want:.4f}")
        if got < MONDAY["floor"]:
            f.append(f"max_rr={m}: PF {got:.3f} fell below {MONDAY['floor']} "
                     f"- lock must be reviewed")
    return f


def test_skip_monday():
    """The rule must actually bite, and the cohort it removes must still be the loser.
    If Monday ever stops being negative the rule has no reason to exist."""
    f = []
    kept = L.portfolio()
    if (kept.t.dt.dayofweek == 0).any():
        f.append("Monday fills present in the locked trade set - filter not applied")
    allt = L.portfolio(skip_dow=())
    mon = allt[allt.t.dt.dayofweek == 0]
    if len(mon) != MONDAY["n"]:
        f.append(f"Monday cohort is {len(mon)} trades, pinned {MONDAY['n']}")
    got = L.pf(mon.netR.values)
    if abs(got - MONDAY["PF"]) > 1e-3:
        f.append(f"Monday PF {got:.4f} != pinned {MONDAY['PF']:.4f}")
    if got >= 1.0:
        f.append(f"Monday is no longer a losing cohort (PF {got:.3f}) "
                 f"- the skip-Monday rule must be reviewed")
    if len(kept) + len(mon) != len(allt):
        f.append("trade counts do not reconcile")
    return f


def test_asian_range_causality(sym="USATECH"):
    """The property the 1.43 look-ahead violated: the Asian range may not be touched
    until its session has closed.

      (a) the RAID bar must sit at hour >= 09:00 EET.  (The SIGNAL bar may be later,
          including past midnight - the raid-to-displacement window is 40 M15 bars =
          10 hours, so that is inside spec, not a violation.)
      (b) any finite Asian level a signal carries must be the COMPLETED range of a
          session on or before that signal's own date - never a future one.

    Combined with the prefix-invariance test below, this is airtight against
    look-ahead.
    """
    df = L.load(sym)
    bars, atr = L.resample(df)
    ctx = ict_system.daily_context(df)
    asia = ict_system.session_pools(df)
    sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
    lut_h = {d: v for d, v in asia.ah.items()}
    lut_l = {d: v for d, v in asia.al.items()}
    f = []
    for s in sigs:
        tr = bars.index[s["sweep_bar"]]
        t = bars.index[s["bar"]]
        if tr.hour < ict_system.ASIA_EET[1]:
            f.append(f"{tr}: raid at hour {tr.hour}, before the Asian session closed")
        for got, lut, nm in ((s["ah"], lut_h, "ah"), (s["al"], lut_l, "al")):
            if not np.isfinite(got):
                continue                      # stale/absent reference - see note below
            src = [d for d, v in lut.items()
                   if d <= t.normalize() and np.isfinite(v) and np.isclose(v, got)]
            if not src:
                f.append(f"{t}: {nm}={got} matches no completed session on or "
                         f"before this date")
    return f[:5]


def test_prefix_invariance(sym="USATECH", cut=0.6):
    """A signal emitted at bar i must not change when later bars are appended."""
    df = L.load(sym)
    dfp = df.iloc[:int(len(df) * cut)]

    def go(d):
        b, a = L.resample(d)
        return b, ict_system.detect(d, b, a, ict_system.daily_context(d),
                                    ict_system.session_pools(d), **L.DETECT)

    bp, sp = go(dfp)
    bf, sf = go(df)
    keyf = {(bf.index[s["bar"]], s["side"]): s for s in sf}
    f, checked = [], 0
    for s in sp:
        t = bp.index[s["bar"]]
        if t > bp.index[-1] - pd.Timedelta("2D"):
            continue
        checked += 1
        if (t, s["side"]) not in keyf:
            f.append(f"{t}: signal vanishes when data is appended"); continue
        g = keyf[(t, s["side"])]
        for fld in ("sweep_px", "zone_lo", "zone_hi", "ce"):
            if not np.isclose(s[fld], g[fld], atol=1e-9):
                f.append(f"{t} {fld}: prefix {s[fld]} != full {g[fld]}")
    if checked == 0:
        f.append("prefix run produced no comparable signals")
    return f[:5], checked


if __name__ == "__main__":
    allf = []
    for name, fn in (("ARM A  both sides, pinned result", test_arm_a),
                     ("ARM B  shorts only, pinned result", test_arm_b),
                     ("max_rr is a region, not a point", test_max_rr_is_a_region),
                     ("skip-Monday rule bites, cohort still negative",
                      test_skip_monday),
                     ("Asian-range causality (no look-ahead)",
                      test_asian_range_causality)):
        f = fn()
        allf += f
        print(f"{'PASS' if not f else 'FAIL'}  {name}")
        for x in f:
            print(f"        - {x}")
    f, ch = test_prefix_invariance()
    allf += f
    print(f"{'PASS' if not f else 'FAIL'}  prefix invariance / causality "
          f"({ch} signals compared)")
    for x in f:
        print(f"        - {x}")
    print("\n" + ("LOCK HOLDS" if not allf else f"LOCK BROKEN - {len(allf)} failure(s)"))
    sys.exit(1 if allf else 0)
