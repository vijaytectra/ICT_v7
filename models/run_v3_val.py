"""Validation ladder for the dev-market pick: reclaim trigger + London-killzone raid.

Selected on US indices 2015-2023 ONLY.  Applied here UNCHANGED to:
  1  US indices 2024-2026   (the period the lock was built on)
  2  the six FX majors      (a different market entirely)
  3  every instrument one at a time
Nothing is re-tuned.  If it only works where it was found, it is noise.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models.v3lab import IDX, port, st

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"
FX = [s for s in L.ALL if s not in IDX]
LOCK = dict(trigger="mss")
NEW = dict(trigger="reclaim", raid_kz=(9, 12))

if __name__ == "__main__":
    rows = []
    for nm, syms, hold, mo in (("indices DEV 2015-23", IDX, True, 108),
                               ("indices VAL 2024-26", IDX, False, 32),
                               ("FX      VAL 2024-26", FX, False, 32),
                               ("all 9   VAL 2024-26", L.ALL, False, 32)):
        for lab, det in (("locked mss", LOCK), ("reclaim+LDN", NEW)):
            rows.append(st(port(syms, hold, **det), f"{nm}  {lab}", mo))
    print("=" * 130)
    print("VALIDATION LADDER — the rule was chosen on indices 2015-2023 and is applied "
          "unchanged everywhere else")
    print("=" * 130)
    r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\v3_val.csv", index=False)
    print(r.to_string(index=False, float_format=f))

    print("\n" + "=" * 130)
    print("PER INSTRUMENT, 2024-2026")
    print("=" * 130)
    rows = []
    for s in L.ALL:
        for lab, det in (("locked", LOCK), ("reclaim+LDN", NEW)):
            d = port([s], False, **det)
            rows.append(dict(sym=s, arm=lab, n=len(d),
                             WR=float((d.out == 1).mean()) if len(d) else np.nan,
                             PF=L.pf(d.netR.values) if len(d) else np.nan,
                             totR=d.netR.sum() if len(d) else np.nan))
    p = pd.DataFrame(rows).pivot(index="sym", columns="arm",
                                 values=["n", "PF", "totR"])
    print(p.to_string(float_format=f))

    print("\n" + "=" * 130)
    print("SHORTS ONLY (arm B)")
    print("=" * 130)
    rows = []
    for nm, syms, hold, mo in (("indices DEV 2015-23", IDX, True, 108),
                               ("all 9   VAL 2024-26", L.ALL, False, 32)):
        for lab, det in (("locked mss", LOCK), ("reclaim+LDN", NEW)):
            rows.append(st(port(syms, hold, shorts=True, **det), f"{nm}  {lab}", mo))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))
