"""Single entry point for Unicorn work.  Everything compares against ONE baseline.

The Unicorn has been rebuilt five times in this project and each rebuild produced a number
that later turned out to be measured differently from the last.  This file exists so that
cannot happen again: it fixes the detector config, the cost model, the split, and the
baseline, so any optimisation is scored against the same thing.

THE SPLIT.  DEV is the three US index CFDs 2015-2023 (nine years, `*_H.parquet`).  VAL is the
same three 2024-2026.  Search on DEV.  Read VAL once, at the end.

THE COST.  0.4 x each instrument's OWN median spread.  A flat number in each instrument's own
quote units is not one cost but three - USA500 was paying 2.91 spreads while USA30 paid 0.59.
That bug is what made every earlier Unicorn number wrong; see the memory note on it.

WHAT IS ALREADY MEASURED AND MUST NOT BE RE-RUN AS IF NEW
---------------------------------------------------------
  216 configs of the v2/v3/v4 detector on six FX majors     none above PF 1.0
  60 configs on US100, the 9 survivors applied to US500/30  8 of 9 failed, incl. the top four
  fixed targets 1R to 6R                                    all negative expectancy on DEV
  stop at the breaker body / FVG far edge / MSS origin      x 3 targets x 5 CRI, best DEV 0.861
  CRI gate, 8 thresholds 0.03 to 0.30                       best DEV 1.019
  five killzone windows                                     best DEV 1.503 at n=101
  premium/discount halves, and the 62-79% OTE band          1.016, and OTE hurts BOTH halves
  relative-equal-highs pools instead of any swing           0.964
  nested-FVG strictness (gap inside the breaker body)       1.024
  top-down H4 PD-array nesting with H4 bias                 keeps 3% of signals, 42 trades/9yr
  the DOL target + R:R gate (the big one)                   DEV 1.481 / VAL 1.866 at min_rr 2.0
  the reachability gate on that target                      HURTS: DEV 1.481 -> 1.007
  M5 / M30 / H1 structure                                   not tested on Unicorn (only Asia)

WHY THE DOL ARM IS NOT ACCEPTED DESPITE 1.481 / 1.866
-----------------------------------------------------
  positive years on DEV                4 of 9
  drop 2023 alone (6 trades, +35.1R)   DEV 1.481 -> 1.166
  leave-one-out                        without USA30, VAL falls to 1.111
  bootstrap on DEV                     P(edge>0) 89.5%, 95% CI [-0.151, +1.076]
That is the bar any optimisation has to clear: a positive-year count, a concentration check,
leave-one-out, and a confidence interval clear of zero - on DEV, with VAL read once.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import unicorn_lab
from models.uni_arms import _C, frame, _bars_close, IDX

SPREAD_MULT = 0.4
_sp = {}


def cost_for(per, sym):
    k = (per, sym)
    if k not in _sp:
        suf = "_H" if per == "DEV" else ""
        d = pd.read_parquet(rf"C:\personal\ICT_v7\data\{sym}{suf}.parquet",
                            columns=["c_b", "c_a"])
        _sp[k] = SPREAD_MULT * float((d.c_a - d.c_b).median())
    return _sp[k]


def book(per, **kw):
    """Run one arm on all three indices for one period."""
    out = []
    for s in IDX:
        c = _C[(per, s)]
        t = unicorn_lab.run(frame(per, s), c["sigs"], c["bars"], 1.0, pd.Timedelta("15min"),
                            ctx=c["ctx"], asia=c["asia"], cost=cost_for(per, s),
                            stf_close=_bars_close(per, s), **kw)
        if len(t): out.append(t.assign(sym=s))
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


# the two arms worth comparing everything against
BASELINE = dict(target="fixed", rr_fixed=2.0, kz="IDX")                      # SETUP_INDEX
BEST_SO_FAR = dict(target="asia+pdhl+range", kz="IDX", min_rr=2.0)           # the DOL arm


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


def dd(v):
    eq = np.asarray(v).cumsum(); return float((eq - np.maximum.accumulate(eq)).min())


def report(label, **kw):
    """The four checks any candidate must survive, printed together."""
    D, V = book("DEV", **kw), book("VAL", **kw)
    if not len(D) or not len(V):
        print(f"{label:34s} no trades"); return None
    rng = np.random.default_rng(11); v = D.netR.values
    m = v[rng.integers(0, len(v), (20000, len(v)))].mean(1)
    yr = D.groupby(D.t.dt.year).netR.sum()
    drop = D[D.t.dt.year != yr.idxmax()]
    loo = min(pf(D[D.sym != s].netR) for s in IDX if (D.sym != s).sum() > 20)
    print(f"{label:34s} DEV n={len(D):4d} PF={pf(D.netR):5.3f} | VAL n={len(V):4d} PF={pf(V.netR):5.3f}"
          f" | yrs+ {int((yr>0).sum())}/{yr.size} | no-best-yr {pf(drop.netR):5.3f}"
          f" | LOO {loo:5.3f} | P(edge) {100*(m>0).mean():4.1f}%")
    return D, V
