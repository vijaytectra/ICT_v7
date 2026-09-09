"""AMENDMENT to models/PREREG_MMXM.md — experiment 2, declared before it was run.

Experiment 1 tested the MMXM with a swing-pivot pool and no structural risk floor.
Two things were wrong with that, and both are established by results this project
produced BEFORE the MMXM existed, not by looking at MMXM output:

  1  THE POOL.  ict-2022-model.md step 3 names TIME-DEFINED pools - "Asian range,
     PDH/PDL, session high/low".  A 3-5 bar swing pivot is inducement, not resting
     liquidity.  Measured earlier in this project across nine instruments:
     Asian range PF 1.19, both pools 1.02, previous-day high/low 0.76.
     Experiment 1 used the pool already known to be the weak one.

  2  THE RISK FLOOR.  brodenbeck v4 Screen 2, cost / structural risk <= 20%.  Without
     it the population fills with setups whose entry sits on the sweep extreme:
     sub-pip stops, planned R:R in the hundreds, ~2% win rate.  Experiment 1's
     surviving config had mean planned R:R 13.5 and an 11% win rate - exactly that
     pathology.  It had no floor.

Changes: sweep_pool='asia' added to the detector; max_cost_frac=0.20 added to the
executor; realistic cost now charged on top of the spread (FX 0.8 pip, index 1.5 pt),
which is STRICTER than experiment 1's spread-only accounting.

Grid: pool {asia, swing} x entry {mt, edge} x target {2R, 3R, ERL} x killzone
{index-AM, London} = 24 configs.  All 24 are printed.  Keep rule unchanged.
"""
import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.run_mmxm import BASE

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
COST = {**{s: 1.5 for s in mmxm_lab.INDICES}, **{s: 0.8 for s in mmxm_lab.FX}}

TARGETS = [("rr2", dict(target="fixed", rr=2.0)),
           ("rr3", dict(target="fixed", rr=3.0)),
           ("erl", dict(target="erl", min_rr=2.0))]


def pf(t):
    if t is None or len(t) == 0:
        return np.nan
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    return float(g / b) if b > 0 else np.inf


def pooled(syms, d, e, period=None):
    out = []
    for s in syms:
        t = mmxm_lab.evaluate(s, d, {**e, "cost": COST[s], "max_cost_frac": 0.20},
                              period=period)
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t") if out else pd.DataFrame()


if __name__ == "__main__":
    rows = []
    for pool, entry, (tname, tkw), kz in itertools.product(
            ["asia", "swing"], ["mt", "edge"], TARGETS, ["IDX", "LDN"]):
        d = {**BASE, "sweep_pool": pool}
        e = dict(entry=entry, kz=kz, **tkw)
        full = pooled(mmxm_lab.INDICES, d, e)
        if len(full) < 40:
            continue
        rec = dict(arm=f"{pool:5s} {entry:4s} {tname} {kz}", pool=pool, entry=entry,
                   target=tname, kz=kz, n=len(full), PF=pf(full),
                   wr=float((full.netR > 0).mean()), totR=float(full.netR.sum()),
                   is_PF=pf(pooled(mmxm_lab.INDICES, d, e, "IS")),
                   oos_PF=pf(pooled(mmxm_lab.INDICES, d, e, "OOS")))
        p = 0
        for s in mmxm_lab.INDICES:
            v = pf(pooled([s], d, e))
            rec[f"{s}_PF"] = v
            if np.isfinite(v) and v > 1.0:
                p += 1
        rec["idx_pos"] = p
        rec["keep"] = bool(rec["is_PF"] > 1.10 and rec["oos_PF"] > 1.05 and p >= 2)
        rows.append(rec)

    r = pd.DataFrame(rows).sort_values("PF", ascending=False)
    r.to_csv(REP / "mmxm_amend.csv", index=False)
    print("=== EXPERIMENT 2: Asian-range pool + structural risk floor, "
          "real cost charged ===")
    print("    pooled US100 + US500 + US30\n")
    print(r[["arm", "n", "wr", "PF", "totR", "is_PF", "oos_PF",
             "USATECH_PF", "USA500_PF", "USA30_PF", "idx_pos", "keep"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nSURVIVORS: {int(r.keep.sum())} of {len(r)}   "
          f"median PF {r.PF.median():.3f}   "
          f"Spearman r(IS,OOS) = {r.is_PF.corr(r.oos_PF, method='spearman'):+.3f}")
