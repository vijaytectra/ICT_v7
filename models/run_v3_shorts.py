"""Full examination of the one arm where the reclaim+London rule survived validation:
SHORTS ONLY.  Selected on indices 2015-2023; applied unchanged everywhere here."""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models.v3lab import IDX, port, st

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"
FX = [s for s in L.ALL if s not in IDX]
LOCK = dict(trigger="mss"); NEW = dict(trigger="reclaim", raid_kz=(9, 12))

if __name__ == "__main__":
    print("=" * 132)
    print("ARM B (shorts only) — locked trigger vs reclaim+London, every slice")
    print("=" * 132)
    rows = []
    for nm, syms, hold, mo in (("indices DEV 15-23", IDX, True, 108),
                               ("indices VAL 24-26", IDX, False, 32),
                               ("FX      VAL 24-26", FX, False, 32),
                               ("all 9   VAL 24-26", L.ALL, False, 32)):
        for lab, det in (("locked", LOCK), ("reclaim+LDN", NEW)):
            rows.append(st(port(syms, hold, shorts=True, **det), f"{nm}  {lab}", mo))
    r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\v3_shorts.csv", index=False)
    print(r.to_string(index=False, float_format=f))

    print("\nPER INSTRUMENT, shorts, 2024-2026")
    rows = []
    for s in L.ALL:
        for lab, det in (("locked", LOCK), ("reclaim+LDN", NEW)):
            d = port([s], False, shorts=True, **det)
            rows.append(dict(sym=s, arm=lab, n=len(d),
                             PF=L.pf(d.netR.values) if len(d) else np.nan,
                             totR=d.netR.sum() if len(d) else np.nan))
    print(pd.DataFrame(rows).pivot(index="sym", columns="arm",
                                   values=["n", "PF", "totR"]).to_string(float_format=f))

    print("\nPER YEAR, shorts, indices DEV 2015-2023")
    for lab, det in (("locked", LOCK), ("reclaim+LDN", NEW)):
        d = port(IDX, True, shorts=True, **det).set_index("t")
        y = d.netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
        y["PF"] = d.netR.groupby(pd.Grouper(freq="YE")).apply(lambda v: L.pf(v.values))
        y.index = y.index.year
        print(f"\n  {lab}"); print(y.to_string(float_format=f))
        print(f"  positive years {(y['sum'] > 0).sum()} of {len(y)}")
