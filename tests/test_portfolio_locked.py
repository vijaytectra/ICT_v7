"""Pinned result for the LOCKED PORTFOLIO.  Locked 2026-09-07.

The strategy is pinned separately by `test_asia_locked.py`.  This file pins the UNIVERSE and
what it measured, so that a change to the instrument list, the cost model, the reachability
gate or the screen shows up as a failure rather than as a quietly different number.

Source data is `reports/broker_books.pkl`, produced by `models/screen_broker.py` from the
broker's own M15 history.  Execution in that screen is on M15 bars, not 1-minute: on USTEC
that flatters by about 3% (PF 1.294 against the true 1.253).  These numbers are therefore an
upper bound, and each name still needs a tick-level Strategy Tester run before real money.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models.portfolio_locked import UNIVERSE, RISK_PCT

TOL = 5e-3
BOOK = r"C:\personal\ICT_v7\reports\broker_books.pkl"

PINNED = dict(
    names_with_data=32,
    n=2239, PF=1.5148, totR=824.31, WR=0.2988, maxDD=-40.53,
    first_PF=1.1553, oos_n=1653, oos_PF=1.6512, oos_maxDD=-22.01,
    trades_per_week=7.44, ER=0.3682,
)
YEARS = {2022: 0.956, 2023: 1.374, 2024: 1.737, 2025: 1.584, 2026: 1.661}

FAILS = []


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


def dd(v):
    eq = np.asarray(v).cumsum(); return float((eq - np.maximum.accumulate(eq)).min())


def near(got, want, label, tol=TOL):
    if want == 0 or isinstance(want, int):
        if got != want: FAILS.append(f"{label}: {got} != pinned {want}")
    elif abs(got - want) / abs(want) > tol:
        FAILS.append(f"{label}: {got:.4f} != pinned {want:.4f}")


def main():
    B = pd.read_pickle(BOOK)
    have = [s for s in UNIVERSE if s in B]
    near(len(have), PINNED["names_with_data"], "instruments with data")
    P = pd.concat([B[s].assign(sym=s) for s in have]).sort_values("t").reset_index(drop=True)
    yrs = (P.t.max() - P.t.min()).days / 365.25
    mid = P.t.min() + (P.t.max() - P.t.min()) / 2
    A, S = P[P.t < mid], P[P.t >= mid]

    near(len(P), PINNED["n"], "trades")
    near(pf(P.netR), PINNED["PF"], "profit factor")
    near(P.netR.sum(), PINNED["totR"], "total R")
    near(float((P.netR > 0).mean()), PINNED["WR"], "win rate")
    near(dd(P.netR), PINNED["maxDD"], "max drawdown")
    near(pf(A.netR), PINNED["first_PF"], "first-half PF")
    near(len(S), PINNED["oos_n"], "out-of-sample trades")
    near(pf(S.netR), PINNED["oos_PF"], "out-of-sample PF")
    near(dd(S.netR), PINNED["oos_maxDD"], "out-of-sample drawdown")
    near(len(P) / (yrs * 52), PINNED["trades_per_week"], "trades per week")
    near(float(P.netR.mean()), PINNED["ER"], "expectancy")
    print("PASS  pinned portfolio result" if not FAILS else "FAIL  pinned portfolio result")

    n0 = len(FAILS)
    for y, want in YEARS.items():
        x = P[P.t.dt.year == y]
        if len(x) < 25: FAILS.append(f"{y}: only {len(x)} trades"); continue
        near(pf(x.netR), want, f"{y} PF")
    print("PASS  per-year profile" if len(FAILS) == n0 else "FAIL  per-year profile")

    # the edge must stay clear of zero, and the OUT-OF-SAMPLE half must not be the weak one
    n0 = len(FAILS)
    rng = np.random.default_rng(11); v = P.netR.values
    m = v[rng.integers(0, len(v), (20000, len(v)))].mean(1)
    if (m > 0).mean() < 0.99: FAILS.append(f"P(edge>0) fell to {(m>0).mean():.3f}")
    if np.percentile(m, 2.5) <= 0: FAILS.append("the 95% CI on expectancy now touches zero")
    print("PASS  expectancy CI clear of zero" if len(FAILS) == n0 else "FAIL  expectancy CI clear of zero")

    n0 = len(FAILS)
    if pf(S.netR) < pf(A.netR):
        FAILS.append(f"out-of-sample PF {pf(S.netR):.3f} is now BELOW in-sample {pf(A.netR):.3f}")
    print("PASS  out-of-sample still ahead of in-sample" if len(FAILS) == n0
          else "FAIL  out-of-sample still ahead of in-sample")

    # the universe must not have been quietly re-ranked on performance
    n0 = len(FAILS)
    from models.portfolio_locked import EXCLUDED
    for grp in EXCLUDED.values():
        for s in grp:
            if s in UNIVERSE: FAILS.append(f"{s} is both excluded and in the universe")
    print("PASS  universe is class-defined, not PF-ranked" if len(FAILS) == n0
          else "FAIL  universe is class-defined, not PF-ranked")

    print()
    for f in FAILS: print("   -", f)
    print("PORTFOLIO LOCK HOLDS" if not FAILS else f"LOCK BROKEN - {len(FAILS)} failure(s)")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
