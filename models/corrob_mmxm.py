"""Stages 2-4: the pre-registered keep rule applied to every config that cleared
in-sample.

  keep  <=  US100 IS PF > 1.10  AND  US100 OOS PF > 1.05
            AND >= 2 of 3 indices PF > 1.0 over the full period

Everything that clears IS is carried through, and the whole table is printed, so the
selection is visible instead of hidden.  This is the v4 corroboration design: nine
configs cleared both halves of US100 there and eight of them died when applied
unchanged to US500 and US30.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.run_mmxm import DETECTORS, SEL, TARGETS, det_kw

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")
TKW = dict(TARGETS)
MIN_N_IS = 80


def exe_of(row):
    return dict(entry=row.entry, kz=row.kz, **TKW[row.target])


def pf(t):
    if t is None or len(t) == 0:
        return np.nan
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    g = pd.read_csv(REP / "mmxm_IS.csv")
    cand = g[(g.PF > 1.10) & (g.n >= MIN_N_IS)].copy()
    print(f"{len(cand)} configs clear IS PF>1.10 with n>={MIN_N_IS} on {SEL}\n")

    rows = []
    for _, r in cand.iterrows():
        d, e = det_kw(r.det), exe_of(r)
        oos = mmxm_lab.evaluate(SEL, d, e, period="OOS")
        rec = dict(arm=r.arm, det=r.det, entry=r.entry, target=r.target, kz=r.kz,
                   is_n=int(r.n), is_PF=float(r.PF),
                   oos_n=len(oos), oos_PF=pf(oos))
        pos = 0
        for s in mmxm_lab.INDICES:
            t = mmxm_lab.evaluate(s, d, e)
            v = pf(t)
            rec[f"{s}_n"] = len(t); rec[f"{s}_PF"] = v
            if np.isfinite(v) and v > 1.0:
                pos += 1
        rec["idx_pos"] = pos
        rec["keep"] = bool(rec["oos_PF"] > 1.05 and pos >= 2)
        rows.append(rec)

    res = pd.DataFrame(rows).sort_values(["keep", "oos_PF"], ascending=False)
    res.to_csv(REP / "mmxm_corrob.csv", index=False)
    cols = ["arm", "is_n", "is_PF", "oos_n", "oos_PF",
            "USATECH_PF", "USA500_PF", "USA30_PF", "idx_pos", "keep"]
    print(res[cols].to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nSURVIVORS: {int(res.keep.sum())} of {len(res)}")
