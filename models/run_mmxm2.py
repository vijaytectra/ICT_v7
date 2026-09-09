"""MMXM v2 experiment.

Pre-registered before running, same protocol as v1:
  - IS 2024-01 -> 2025-06, OOS 2025-07 -> end.  OOS looked at once per config.
  - the detector grid IS the ablation: every gate on/off, so the effect of each of
    the four v1 omissions is measured directly.
  - real cost charged (index 1.5 pt, FX 0.8 pip) on top of the spread, plus
    brodenbeck v4 Screen 2's structural risk floor (cost/risk <= 20%).
  - keep rule: US100 IS PF>1.10 AND OOS PF>1.05 AND >=2 of 3 indices PF>1.0.
  - the decisive statistic is the IS->OOS rank correlation on the pooled indices.

Grid: 16 detector variants (smt x contraction x judas x bias) x 9 execution
variants (entry x target) = 144 configs.
"""
import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm2, mmxm2_lab, mmxm_bt

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
IDX, FX = mmxm2_lab.INDICES, mmxm2_lab.FX
import os
# cost regime is a command-line switch so v2 can be compared like-for-like with v1
# and with the Unicorn control, both of which were measured SPREAD-ONLY.
# SETUP_INDEX.md: the Unicorn itself is PF 1.13 at zero extra cost, 1.03 at 1 point,
# 0.94 at 2 - so judging any index model at 1.5 points kills the known-good one too.
SCALE = float(os.environ.get("MMXM_COST", "0"))
COST = {**{s: 1.5 * SCALE for s in IDX}, **{s: 0.8 * SCALE for s in FX}}
BASE = dict(n=5, target_mode="accum", max_hold_bars=60)

ENTRIES = ["mt", "edge", "cisd"]
TARGETS = [("pool", dict(target="pool", min_rr=1.0)),
           ("rr2", dict(target="fixed", rr=2.0)),
           ("rr3", dict(target="fixed", rr=3.0))]


def det_of(smt, contr, judas, bias):
    return {**BASE, "require_smt": smt, "require_contraction": contr,
            "require_judas": judas, "require_bias": bias}


def name_of(smt, contr, judas, bias):
    return ("smt" if smt else "---") + "/" + ("con" if contr else "---") + "/" + \
           ("jud" if judas else "---") + "/" + ("bias" if bias else "----")


def go(syms, d, e, period=None):
    return mmxm2_lab.pooled(syms, d, {**e, "max_cost_frac": 0.20 if SCALE else None},
                            period=period, cost=COST)


if __name__ == "__main__":
    rows = []
    for smt, contr, judas, bias in itertools.product([True, False], repeat=4):
        d = det_of(smt, contr, judas, bias)
        for entry, (tn, tkw) in itertools.product(ENTRIES, TARGETS):
            e = dict(entry=entry, kz="ALL", **tkw)
            i_t = go(IDX, d, e, "IS"); o_t = go(IDX, d, e, "OOS")
            if len(i_t) < 40 or len(o_t) < 25:
                continue
            full = go(IDX, d, e)
            rec = dict(arm=f"{name_of(smt,contr,judas,bias)} {entry:4s} {tn}",
                       smt=smt, contr=contr, judas=judas, bias=bias,
                       entry=entry, target=tn,
                       n=len(full), wr=float((full.netR > 0).mean()),
                       PF=mmxm2_lab.pf(full), totR=float(full.netR.sum()),
                       is_n=len(i_t), is_PF=mmxm2_lab.pf(i_t),
                       oos_n=len(o_t), oos_PF=mmxm2_lab.pf(o_t))
            p = 0
            for s in IDX:
                v = mmxm2_lab.pf(go([s], d, e))
                rec[f"{s}_PF"] = v
                if np.isfinite(v) and v > 1.0:
                    p += 1
            rec["idx_pos"] = p
            rec["keep"] = bool(rec["is_PF"] > 1.10 and rec["oos_PF"] > 1.05 and p >= 2)
            rows.append(rec)

    r = pd.DataFrame(rows)
    r.to_csv(REP / f"mmxm2_grid_cost{SCALE:g}.csv", index=False)
    f = lambda x: f"{x:.3f}"
    print(f"{len(r)} configs scored, pooled US100 + US500 + US30, real cost charged\n")
    print("--- TOP 20 by FULL-period PF ---")
    print(r.nlargest(20, "PF")[["arm", "n", "wr", "PF", "totR", "is_PF", "oos_PF",
                                "idx_pos", "keep"]]
          .to_string(index=False, float_format=f))
    print(f"\nmedian PF {r.PF.median():.3f}   PF>1.0: {(r.PF>1).sum()}/{len(r)}")
    print(f"OOS PF>1.0: {(r.oos_PF>1).sum()}/{len(r)}   "
          f"median OOS {r.oos_PF.median():.3f}")
    print(f"Spearman r(IS PF, OOS PF) = "
          f"{r.is_PF.corr(r.oos_PF, method='spearman'):+.3f}")
    print(f"Pearson  r(IS PF, OOS PF) = {r.is_PF.corr(r.oos_PF):+.3f}")
    print(f"\nSURVIVORS of the keep rule: {int(r.keep.sum())} of {len(r)}")
    if r.keep.any():
        print(r[r.keep][["arm", "n", "wr", "PF", "is_PF", "oos_PF", "USATECH_PF",
                         "USA500_PF", "USA30_PF"]]
              .to_string(index=False, float_format=f))

    print("\n--- GATE ABLATION: mean PF with the gate ON vs OFF ---")
    for g in ("smt", "contr", "judas", "bias"):
        on, off = r[r[g]], r[~r[g]]
        print(f"  {g:6s} ON  PF {on.PF.mean():.3f} (OOS {on.oos_PF.mean():.3f}, "
              f"n_cfg {len(on)})   OFF PF {off.PF.mean():.3f} "
              f"(OOS {off.oos_PF.mean():.3f}, n_cfg {len(off)})   "
              f"delta {on.PF.mean()-off.PF.mean():+.3f}")
