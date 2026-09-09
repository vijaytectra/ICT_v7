"""Control: is the new execution harness itself pessimistic?

Feed the ALREADY-VALIDATED Unicorn index config (SETUP_INDEX.md: PF 1.21 on
US100/500/30) through models/mmxm_bt.py.  If the harness reproduces roughly 1.21, then
the MMXM's sub-1.0 numbers are a property of the MMXM, not of the backtester.  Without
this control a negative result is not believable.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.unicorn_v5 import detect as udetect

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")

# SETUP_INDEX.md, verbatim: M15 structure, swing n=5, plain sweep (no reclaim test),
# 60-bar window, displacement body >= 0.5, breaker = bearish OB at the swing high,
# FVG overlapping it, entry at the breaker MEAN THRESHOLD, 6 h validity, stop at the
# swept extreme, 2R target, London + index-AM killzones.
UKW = dict(n=5, max_gap=60, disp_ratio=0.5, reclaim_bars=0, wick_frac=0.0,
           pool="swing", ob_back=30)
UEXE = dict(entry="mt", target="fixed", rr=2.0, kz="IDX", window_min=360)


def pf(v):
    g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    print("=== CONTROL: the validated Unicorn index config, run through mmxm_bt ===")
    print("    SETUP_INDEX.md reports PF 1.21 (n=413) from the bt3 code path\n")
    allt = []
    for s in mmxm_lab.INDICES:
        df, bars, atr, _, _ = mmxm_lab.prep(s, "15min", "4h")
        sg = udetect(bars.o_b.values, bars.h_b.values, bars.l_b.values,
                     bars.c_b.values, atr, **UKW)
        for x in sg:                       # entry at the BREAKER mean threshold
            x["zone_lo"], x["zone_hi"] = x["brk_lo"], x["brk_hi"]
            x["cisd"] = x["mt"]; x["poi_lo"] = np.nan
            x["erl_hi"] = x["erl_lo"] = np.nan
        t = mmxm_bt.run(df, sg, bars.index, mmxm_lab.UNIT[s],
                        pd.Timedelta("15min"), **UEXE)
        if len(t):
            t = t.copy(); t["sym"] = s; allt.append(t)
            print(f"  {s:8s} n={len(t):4d}  WR {(t.netR>0).mean():.3f}  "
                  f"PF {pf(t.netR.values):.3f}  totR {t.netR.sum():+7.1f}")
    a = pd.concat(allt).sort_values("t")
    is_t = a[a.t < mmxm_lab.IS_END]; oos_t = a[a.t >= mmxm_lab.IS_END]
    pe, ci = mmxm_bt.bootstrap(a)
    print(f"\n  POOLED    n={len(a):4d}  WR {(a.netR>0).mean():.3f}  "
          f"PF {pf(a.netR.values):.3f}  totR {a.netR.sum():+7.1f}")
    print(f"  IS PF {pf(is_t.netR.values):.3f} (n={len(is_t)})  ->  "
          f"OOS PF {pf(oos_t.netR.values):.3f} (n={len(oos_t)})")
    print(f"  P(edge > 0) {pe:.3f}   95% CI on E[R] [{ci[0]:+.3f}, {ci[1]:+.3f}]")
    a.to_csv(REP / "mmxm_control_unicorn.csv", index=False)
