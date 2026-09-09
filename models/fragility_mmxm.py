"""Two last things the pre-registration owes an answer to.

  1  FRAGILITY of the one surviving config.  An 11% win rate means a handful of
     outsized winners carry everything; a jackknife says how many.
  2  ABLATIONS H2/H3/H4, at one fixed execution so the comparison is clean.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.run_mmxm import BASE

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
DET = dict(BASE); DET["require_discount"] = False
EXE = dict(entry="mt", target="erl", min_rr=1.5, kz="LDN")


def pf(v):
    g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    t = mmxm_lab.pooled(mmxm_lab.INDICES, DET, EXE)
    v = t.netR.values
    print("=== FRAGILITY of the surviving config (pooled indices) ===\n")
    print(f"  trades {len(v)}   win rate {(v>0).mean():.3f}   PF {pf(v):.3f}   "
          f"total {v.sum():+.1f}R   mean planned R:R {t.rr.mean():.1f}")
    print(f"  median hold {t.bars.median():.0f} M1 bars "
          f"({t.bars.median()/60:.1f} h)   max {t.bars.max()/60:.1f} h")
    order = np.argsort(-v)
    print(f"\n  five largest winners: {', '.join(f'{v[i]:+.1f}R' for i in order[:5])}")
    for k in (1, 2, 3, 5):
        w = np.delete(v, order[:k])
        print(f"  drop the {k} best trade(s) -> PF {pf(w):.3f}   total {w.sum():+.1f}R")
    print(f"\n  top 5 trades are {v[order[:5]].sum()/v[v>0].sum()*100:.0f}% of all "
          f"gross profit; they are {5/len(v)*100:.1f}% of trades")
    pe, ci = mmxm_bt.bootstrap(t)
    print(f"  P(edge > 0) = {pe:.3f}   95% CI on E[R] = [{ci[0]:+.3f}, {ci[1]:+.3f}]")

    print("\n=== ABLATIONS, pooled indices, execution fixed at "
          "entry=mean-threshold / target=2R / killzone=NY AM ===\n")
    FIX = dict(entry="mt", target="fixed", rr=2.0, kz="IDX")
    arms = [
        ("H3  POI = HTF FVG (internal range liq.)", dict(BASE)),
        ("H3  POI = none  (control)              ", {**BASE, "poi_mode": "any"}),
        ("H3  POI = external range liq. taken    ", {**BASE, "poi_mode": "erl"}),
        ("H4  pool measured off WICKS            ", dict(BASE)),
        ("H4  pool measured off BODIES           ", {**BASE, "body_liquidity": True}),
        ("H2  CISD trigger, OB = candle bodies   ", dict(BASE)),
        ("H2  CISD trigger, OB = full range      ", {**BASE, "ob_zone": "range"}),
        ("H2  CISD + displacement + FVG required ", {**BASE, "disp_ratio": 0.5,
                                                     "require_fvg": True}),
        ("    discount / premium gate OFF        ", {**BASE, "require_discount": False}),
        ("    HTF order-flow gate OFF            ", {**BASE, "require_bias": False}),
        ("    pool = relative equal highs/lows   ", {**BASE, "sweep_pool": "equal"}),
        ("    no pool requirement at all         ", {**BASE, "sweep_pool": "none"}),
    ]
    rows = []
    for name, d in arms:
        a = mmxm_lab.pooled(mmxm_lab.INDICES, d, FIX)
        i_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, FIX, period="IS")
        o_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, FIX, period="OOS")
        if not len(a):
            continue
        rows.append(dict(arm=name, n=len(a), wr=float((a.netR > 0).mean()),
                         ER=float(a.netR.mean()), PF=pf(a.netR.values),
                         totR=float(a.netR.sum()),
                         is_PF=pf(i_t.netR.values) if len(i_t) else np.nan,
                         oos_PF=pf(o_t.netR.values) if len(o_t) else np.nan))
    r = pd.DataFrame(rows)
    r.to_csv(REP / "mmxm_ablation.csv", index=False)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
