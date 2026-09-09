import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models.protocol import book, loyo, walk_forward, per_period, IDX
from models import asia_locked as L
pd.set_option("display.width", 210); f = lambda x: f"{x:.3f}"

# indices span 12 years across the two files -> the longest continuous record
A = pd.concat([book(IDX, True, False), book(IDX, False, False)]).sort_values("t")
B = pd.concat([book(IDX, True, True),  book(IDX, False, True)]).sort_values("t")
A.to_csv(r"C:\personal\ICT_v7\reports\proto_A_12y.csv", index=False)
B.to_csv(r"C:\personal\ICT_v7\reports\proto_B_12y.csv", index=False)

print("=" * 112)
print("TEST 2 — LEAVE-ONE-YEAR-OUT, US indices 2015-2026 (12 years, frozen rules)")
print("=" * 112)
for nm, d in (("ARM A", A), ("ARM B", B)):
    r, pf_all = loyo(d, nm)
    print(f"\n  {nm}: full record n={len(d)} PF={pf_all:.3f} totR={d.netR.sum():+.1f}")
    print(r.to_string(index=False, float_format=f))
    print(f"    positive years {(r.totR_year>0).sum()} of {len(r)}   "
          f"PF_without range {r.PF_without.min():.3f} - {r.PF_without.max():.3f}")

print("\n" + "=" * 112)
print("TEST 3 — WALK-FORWARD, rolling 6-month windows, rules frozen throughout")
print("=" * 112)
for nm, d in (("ARM A", A), ("ARM B", B)):
    r = walk_forward(d, nm)
    r.index = r.index.to_period("M")
    print(f"\n  {nm}")
    print(r[["n", "WR", "PF", "totR"]].to_string(float_format=f))
    ok = r[r.n >= 10]
    print(f"    windows with n>=10: {len(ok)}   PF>1.0 in {(ok.PF>1).sum()} "
          f"({(ok.PF>1).mean()*100:.0f}%)   median window PF {ok.PF.median():.3f}")
