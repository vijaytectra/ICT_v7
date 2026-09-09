"""MMXM, one last pre-declared test — not a new search.

MMXM was measured to exhaustion earlier: 216 + 21 + 144 = 381 configurations, zero
survivors, IS->OOS rank correlation -0.26 / -0.656 / -0.19.  Its best arm was the fully
UNGATED one (Asian-range sweep -> CISD -> opposite-bound target) at PF 1.215 on FX
spread-only, which broke even at about 0.75 pip and was OOS 0.978 at the 0.7 pip this
project charges.

Three things were established AFTER that work, on independent evidence, and none of them
was ever applied to MMXM:

  1  SKIP MONDAY.  The only negative day of the week, in both periods independently
     (PF 0.708 / 0.513, permutation p = 0.032 / 0.005).
  2  SHORTS ONLY.  Longs are the losing side - PF 0.906 and -32.6 R over 11.7 years.
     Every MMXM test was run on both sides pooled.
  3  The reclaim/London finding on Arm B, which doubled trades and raised total R in
     four independent slices.

This runs ONE configuration: MMXM v2's own best detector, unchanged, plus rules 1 and 2.
Nothing is tuned.  Real cost is charged.  Both periods.  If it does not clear both, MMXM
is closed permanently.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as AL
from models import mmxm2_lab, mmxm_bt

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"
IDX, FX = mmxm2_lab.INDICES, mmxm2_lab.FX
COST = {**{s: 1.5 for s in IDX}, **{s: 0.8 for s in FX}}

# MMXM v2's best arm, verbatim: every doctrinal gate OFF
DET = dict(n=5, target_mode="accum", max_hold_bars=60, require_smt=False,
           require_contraction=False, require_judas=False, require_bias=False)
EXE = dict(entry="mt", kz="ALL", target="pool", min_rr=1.0, max_cost_frac=0.20)


def book(syms, period=None, shorts=False, skip_mon=True, cost=True):
    out = []
    for s in syms:
        e = dict(EXE)
        e["cost"] = COST[s] if cost else 0.0
        t = mmxm2_lab.evaluate(s, DET, e, period=period)
        if not len(t):
            continue
        if skip_mon:
            t = t[t.t.dt.dayofweek != 0]
        if shorts:
            t = t[t.side == -1]
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def st(d, l):
    if d is None or len(d) < 25:
        return dict(arm=l, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = mmxm_bt.bootstrap(d)
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    return dict(arm=l, n=len(v), WR=float((v > 0).mean()), ER=v.mean(),
                PF=AL.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(),
                RdD=v.sum() / abs((eq - np.maximum.accumulate(eq)).min()),
                streak=mx, P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    print("=" * 128)
    print("MMXM — the three post-hoc findings applied.  ONE configuration, real cost.")
    print("=" * 128)
    rows = []
    for lab, kw in (("as measured before  (both sides, Mon incl.)",
                     dict(shorts=False, skip_mon=False)),
                    ("+ skip Monday", dict(shorts=False, skip_mon=True)),
                    ("+ shorts only", dict(shorts=True, skip_mon=False)),
                    ("+ skip Monday + shorts only", dict(shorts=True, skip_mon=True))):
        rows.append(st(book(mmxm2_lab.INDICES + FX, **kw), f"all 9   {lab}"))
        rows.append(st(book(IDX, **kw), f"indices {lab}"))
        rows.append(st(book(FX, **kw), f"FX      {lab}"))
    r = pd.DataFrame(rows)
    r.to_csv(r"C:\personal\ICT_v7\reports\mmxm_final.csv", index=False)
    print(r.to_string(index=False, float_format=f))

    print("\nIN-SAMPLE -> OUT-OF-SAMPLE, the full rule set")
    rows = []
    for nm, syms in (("all 9", mmxm2_lab.INDICES + FX), ("indices", IDX), ("FX", FX)):
        for per in ("IS", "OOS"):
            rows.append(st(book(syms, period=per, shorts=True, skip_mon=True),
                           f"{nm} {per}"))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\nCOST SENSITIVITY, all 9, skip Monday + shorts only")
    for c in (0.0, 0.5, 1.0, 1.5):
        d = book(mmxm2_lab.INDICES + FX, shorts=True, skip_mon=True, cost=(c > 0))
        if c > 0:
            d = book(mmxm2_lab.INDICES + FX, shorts=True, skip_mon=True)
        print(f"  cost x{c:.1f}: n={len(d)} PF={AL.pf(d.netR.values):.3f} "
              f"totR={d.netR.sum():+.1f}" + ("   <- the charged case" if c == 1.0 else ""))
