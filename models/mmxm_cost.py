"""The decisive re-test for MMXM: cost, properly swept, and per instrument.

MMXM died on cost the first time - PF 1.215 spread-only, breakeven at ~0.75 pip,
OOS 0.978 at the charged 0.7.  With skip-Monday and shorts-only applied it now shows
PF 1.168 at full charge, so the cost curve has to be re-measured honestly.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as AL
from models import mmxm2_lab, mmxm_bt
from models.mmxm_final import DET, EXE, IDX, FX

pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"


def book(syms, mult=1.0, period=None, floor=True):
    out = []
    for s in syms:
        e = dict(EXE)
        e["cost"] = (1.5 if s in IDX else 0.8) * mult
        if not floor or e["cost"] == 0:
            e.pop("max_cost_frac", None)
        t = mmxm2_lab.evaluate(s, DET, e, period=period)
        if not len(t):
            continue
        t = t[(t.t.dt.dayofweek != 0) & (t.side == -1)]
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


if __name__ == "__main__":
    print("=" * 108)
    print("COST SWEEP — MMXM shorts, skip Monday.  base = FX 0.8 pip / index 1.5 pt")
    print("=" * 108)
    print(f"{'mult':>6}{'cost FX':>9}{'n':>7}{'WR':>7}{'PF':>8}{'totR':>10}"
          f"{'maxDD':>9}{'R/DD':>7}{'IS PF':>8}{'OOS PF':>8}{'P(edge)':>9}")
    for m in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        d = book(mmxm2_lab.INDICES + FX, m)
        if len(d) < 25:
            continue
        i = book(mmxm2_lab.INDICES + FX, m, "IS"); o = book(mmxm2_lab.INDICES + FX, m, "OOS")
        v = d.netR.values; eq = v.cumsum()
        dd = (eq - np.maximum.accumulate(eq)).min()
        p, _ = mmxm_bt.bootstrap(d)
        print(f"{m:>6.2f}{0.8*m:>9.2f}{len(v):>7}{(v>0).mean():>7.3f}{AL.pf(v):>8.3f}"
              f"{v.sum():>+10.1f}{dd:>9.1f}{v.sum()/abs(dd):>7.2f}"
              f"{AL.pf(i.netR.values):>8.3f}{AL.pf(o.netR.values):>8.3f}{p:>9.3f}")

    print("\n" + "=" * 108)
    print("PER INSTRUMENT at full charge")
    print("=" * 108)
    rows = []
    for s in mmxm2_lab.INDICES + FX:
        d = book([s]); i = book([s], period="IS"); o = book([s], period="OOS")
        if not len(d):
            continue
        rows.append(dict(sym=s, n=len(d), WR=float((d.netR > 0).mean()),
                         PF=AL.pf(d.netR.values), totR=d.netR.sum(),
                         med_risk=d.R_units.median(),
                         is_PF=AL.pf(i.netR.values) if len(i) else np.nan,
                         oos_PF=AL.pf(o.netR.values) if len(o) else np.nan))
    r = pd.DataFrame(rows).sort_values("PF", ascending=False)
    r.to_csv(r"C:\personal\ICT_v7\reports\mmxm_final_per_sym.csv", index=False)
    print(r.to_string(index=False, float_format=f))
    print(f"\n  profitable: {(r.PF>1).sum()} of {len(r)}   "
          f"OOS profitable: {(r.oos_PF>1).sum()} of {len(r)}")

    print("\n" + "=" * 108)
    print("YEARLY, all 9, full charge")
    print("=" * 108)
    d = book(mmxm2_lab.INDICES + FX).set_index("t")
    y = d.netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
    y["PF"] = d.netR.groupby(pd.Grouper(freq="YE")).apply(lambda v: AL.pf(v.values))
    y.index = y.index.year
    print(y.to_string(float_format=f))
