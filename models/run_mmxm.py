"""MMXM experiment, run exactly as models/PREREG_MMXM.md specifies.

  stage 1  216-config grid, US100 IN-SAMPLE ONLY
  stage 2  the IS pick, confirmed once on US100 out-of-sample
  stage 3  the frozen config applied UNCHANGED to US500 and US30 (corroboration)
  stage 4  the same frozen config on six FX majors (transfer test)
"""
import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
SEL = "USATECH"                                   # the selection instrument

BASE = dict(n=5, poi_mode="fvg", sweep_pool="swing", body_liquidity=False,
            require_bias=True, require_discount=True, max_gap=40, ob_zone="body")

DETECTORS = {
    "D1_base":      {},
    "D2_noPOI":     dict(poi_mode="any"),                       # H3 ablation
    "D3_erlPOI":    dict(poi_mode="erl"),
    "D4_bodies":    dict(body_liquidity=True),                  # H4
    "D5_equal":     dict(sweep_pool="equal"),
    "D6_noDisc":    dict(require_discount=False),
    "D7_obRange":   dict(ob_zone="range"),
    "D8_disp":      dict(disp_ratio=0.5, require_fvg=True),
}
ENTRIES = ["mt", "edge", "cisd"]
TARGETS = [("rr2", dict(target="fixed", rr=2.0)),
           ("rr3", dict(target="fixed", rr=3.0)),
           ("erl", dict(target="erl", min_rr=1.5))]
KZS = ["ALL", "LDN", "IDX"]


def det_kw(name):
    d = dict(BASE); d.update(DETECTORS[name]); return d


def grid():
    rows = []
    for dname, entry, (tname, tkw), kz in itertools.product(
            DETECTORS, ENTRIES, TARGETS, KZS):
        exe = dict(entry=entry, kz=kz, **tkw)
        t = mmxm_lab.evaluate(SEL, det_kw(dname), exe, period="IS")
        s = mmxm_bt.stats(t, f"{dname} {entry} {tname} {kz}")
        if s is None or s["n"] < 25:
            continue
        s.update(det=dname, entry=entry, target=tname, kz=kz)
        rows.append(s)
    return pd.DataFrame(rows).sort_values("PF", ascending=False)


if __name__ == "__main__":
    print(f"stage 1 - {len(DETECTORS)*len(ENTRIES)*len(TARGETS)*len(KZS)} configs, "
          f"{SEL} IN-SAMPLE ONLY\n")
    g = grid()
    g.to_csv(REP / "mmxm_IS.csv", index=False)
    cols = ["arm", "n", "wr", "ER", "PF", "totR", "maxDD", "med_risk", "med_hold"]
    print(g[cols].head(20).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nconfigs scored: {len(g)}   PF>1.0: {(g.PF>1).sum()}   "
          f"PF>1.1: {(g.PF>1.1).sum()}   median PF {g.PF.median():.3f}")
    print("\nby detector variant (best PF in each):")
    print(g.groupby("det").PF.max().sort_values(ascending=False).to_string())
