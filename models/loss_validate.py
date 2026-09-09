"""Validate every loss-reduction candidate on the 2015-2023 holdout.

Five cohorts came back negative on 2024-2026, and five monotone gradients came back
positive.  Both kinds are hypotheses, not findings: the scan looked at 13 features, so
a few extreme cohorts are guaranteed by chance alone.

Each candidate is:
  1  restated as a filter applied BEFORE entry;
  2  measured on 2024-2026 (where it was found - so this number is optimistic);
  3  measured on 2015-2023, nine years the model has never seen;
  4  judged on the holdout only.

A filter earns its place only if it improves BOTH periods.  Anything that improves
2024-2026 and not the holdout is the LR3 signature and is rejected.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import loss_analysis as A

f = lambda x: f"{x:.3f}"

# every candidate, as a callable filter on the featured trade frame
FILTERS = {
    "BASE (locked)":                lambda d: np.ones(len(d), bool),
    "skip Monday":                  lambda d: d.dow != 0,
    "asia range < 3.4 ATR":         lambda d: d.asia_w_atr < 3.39,
    "asia range < 2.45 ATR":        lambda d: d.asia_w_atr < 2.449,
    "displacement >= 0.8":          lambda d: d.disp >= 0.8,
    "FVG >= 0.27 ATR":              lambda d: d.fvg_atr >= 0.265,
    "FVG >= 0.51 ATR":              lambda d: d.fvg_atr >= 0.509,
    "entry_pos < 0.15":             lambda d: d.entry_pos < 0.15,
    "raid depth < 0.11":            lambda d: d.depth < 0.106,
    "skip stop 5.9-15.8u":          lambda d: ~d.R_pips.between(5.9, 15.75),
    "skip rr 4-5":                  lambda d: ~d.rr.between(4.0, 5.0),
    "skip disp 0.7-0.8":            lambda d: ~d.disp.between(0.7, 0.8),
    "lag > 2 bars":                 lambda d: d.lag > 2,
    "bias must DISagree":           lambda d: d.bias_agree == 0,
    "no short-term low":            lambda d: d.has_stl == 0,
}


def stat(d, label):
    if len(d) < 20:
        return None
    v = d.netR.values
    gl = -v[v < 0].sum()
    eq = v.cumsum()
    return dict(filter=label, n=len(v), WR=float((d.out == 1).mean()),
                ER=float(v.mean()), PF=float(v[v > 0].sum() / gl) if gl else np.inf,
                totR=float(v.sum()), maxDD=float((eq - np.maximum.accumulate(eq)).min()))


if __name__ == "__main__":
    live = A.live()
    hold = A.hold()
    print(f"live 2024-2026: {len(live)} trades   holdout 2015-2023: {len(hold)} trades")
    print("(the holdout is indices only, so its base rate differs - compare the DELTA)\n")

    rows = []
    bl = stat(live, "x"); bh = stat(hold, "x")
    for name, fn in FILTERS.items():
        sl = stat(live[fn(live)], name)
        sh = stat(hold[fn(hold)], name)
        if sl is None or sh is None:
            continue
        rows.append(dict(filter=name,
                         live_n=sl["n"], live_PF=sl["PF"], live_ER=sl["ER"],
                         live_totR=sl["totR"],
                         hold_n=sh["n"], hold_PF=sh["PF"], hold_ER=sh["ER"],
                         hold_totR=sh["totR"],
                         d_live=sl["PF"] - bl["PF"], d_hold=sh["PF"] - bh["PF"],
                         kept_live=sl["n"] / bl["n"], kept_hold=sh["n"] / bh["n"]))
    r = pd.DataFrame(rows)
    r.to_csv(r"C:\personal\ICT_v7\reports\loss_filters.csv", index=False)

    print("=" * 118)
    print("EVERY CANDIDATE, BOTH PERIODS.  d_live / d_hold = PF change vs the locked base")
    print("=" * 118)
    print(r[["filter", "live_n", "live_PF", "live_totR", "d_live",
             "hold_n", "hold_PF", "hold_totR", "d_hold", "kept_hold"]]
          .to_string(index=False, float_format=f))

    print("\n" + "=" * 118)
    print("VERDICT — a filter must improve BOTH periods")
    print("=" * 118)
    ok = r[(r.d_live > 0) & (r.d_hold > 0) & (r.filter != "BASE (locked)")]
    bad = r[(r.d_live > 0) & (r.d_hold <= 0)]
    print(f"\n  SURVIVED both:  {len(ok)}")
    if len(ok):
        print(ok[["filter", "live_PF", "d_live", "hold_PF", "d_hold", "kept_hold"]]
              .to_string(index=False, float_format=f))
    print(f"\n  helped 2024-26 but FAILED the holdout (the LR3 signature):  {len(bad)}")
    if len(bad):
        print(bad[["filter", "d_live", "d_hold"]]
              .to_string(index=False, float_format=f))
