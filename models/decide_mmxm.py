"""The decisive test, run after the pre-registered screen returned zero survivors.

Selecting on one instrument can be unlucky.  The question that separates "unlucky
pick" from "no edge" is whether in-sample rank carries ANY information about
out-of-sample rank.  So: score all 216 configs on the POOLED indices in-sample, score
the same 216 out-of-sample, and correlate.

  edge present  -> IS PF and OOS PF are positively correlated and the top of the IS
                   list stays above 1.0 out of sample
  noise only    -> the correlation is ~0 and the IS leaders regress to the pooled mean

The Unicorn measured on this identical data and split is the control: its OOS PF on
these three indices was 1.25, HIGHER than its IS 1.18.  So a collapse here is a
property of this model, not of the out-of-sample period.
"""
import itertools
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.run_mmxm import DETECTORS, ENTRIES, KZS, TARGETS, det_kw

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")


def pf(t):
    if t is None or len(t) == 0:
        return np.nan
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    rows = []
    for dname, entry, (tname, tkw), kz in itertools.product(
            DETECTORS, ENTRIES, TARGETS, KZS):
        d, e = det_kw(dname), dict(entry=entry, kz=kz, **tkw)
        i_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, e, period="IS")
        o_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, e, period="OOS")
        if len(i_t) < 60 or len(o_t) < 40:
            continue
        rows.append(dict(arm=f"{dname} {entry} {tname} {kz}", det=dname, entry=entry,
                         target=tname, kz=kz, is_n=len(i_t), is_PF=pf(i_t),
                         oos_n=len(o_t), oos_PF=pf(o_t),
                         is_ER=float(i_t.netR.mean()), oos_ER=float(o_t.netR.mean()),
                         full_totR=float(i_t.netR.sum() + o_t.netR.sum())))
    r = pd.DataFrame(rows)
    r["decay"] = r.oos_PF - r.is_PF
    r = r.sort_values("is_PF", ascending=False)
    r.to_csv(REP / "mmxm_pooled_ISOOS.csv", index=False)

    print(f"{len(r)} configs scored on the POOLED three indices\n")
    print("--- ranked by IN-SAMPLE PF (the choice a searcher would make) ---")
    print(r.head(12)[["arm", "is_n", "is_PF", "oos_n", "oos_PF", "decay"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    ok = r.dropna(subset=["is_PF", "oos_PF"])
    print(f"\nIS PF  : median {ok.is_PF.median():.3f}   max {ok.is_PF.max():.3f}   "
          f">1.0: {(ok.is_PF>1).sum()}/{len(ok)}")
    print(f"OOS PF : median {ok.oos_PF.median():.3f}   max {ok.oos_PF.max():.3f}   "
          f">1.0: {(ok.oos_PF>1).sum()}/{len(ok)}")
    print(f"\nPearson  r(IS PF, OOS PF) = {ok.is_PF.corr(ok.oos_PF):+.3f}")
    print(f"Spearman r(IS PF, OOS PF) = {ok.is_PF.corr(ok.oos_PF, method='spearman'):+.3f}")
    top = ok.nlargest(10, "is_PF")
    print(f"\ntop-10 by IS PF -> their mean OOS PF = {top.oos_PF.mean():.3f} "
          f"(all-config mean OOS PF = {ok.oos_PF.mean():.3f})")
    print(f"mean decay across all configs = {ok.decay.mean():+.3f}")

    print("\n--- both halves above 1.0 (the only configs that could be real) ---")
    both = ok[(ok.is_PF > 1.0) & (ok.oos_PF > 1.0)]
    if len(both):
        print(both[["arm", "is_n", "is_PF", "oos_n", "oos_PF", "full_totR"]]
              .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    else:
        print("  none")
