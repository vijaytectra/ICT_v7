"""Systematic in-sample search on NON-OVERLAPPING trades.

Each hypothesis is executed the way an EA would: one position at a time.
That makes every recorded trade an independent observation, so the win rate
and its Wilson interval mean what they say.
"""
import sys, pathlib, numpy as np, pandas as pd
from scipy import stats as st
sys.path.insert(0, r"C:\personal\ICT_v7")
from census.features import build
from engine.barrier import sequential

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
WIDTHS, IS_END, NQ, MIN_TRADES = [10, 20, 30], "2025-06-30", 5, 100

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return c - h, c + h

rows = []
for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    oc = pd.read_parquet(DATA / f"{p}_outcomes.parquet")
    ft = build(df, PIP[p]).loc[oc.index]
    m = oc.index <= IS_END
    ft, oc = ft[m], oc[m]

    for w in WIDTHS:
        for s in ("L", "S"):
            out = np.ascontiguousarray(oc[f"o_{w}{s}"].values.astype(np.int8))
            hld = np.ascontiguousarray(oc[f"h_{w}{s}"].values.astype(np.int64))

            def score(mask, name):
                sig = np.ascontiguousarray(mask.astype(np.bool_))
                r, _ = sequential(sig, out, hld)
                dec = int((r != 0).sum())
                if dec < MIN_TRADES: return
                k = int((r == 1).sum())
                lo, hi = wilson(k, dec)
                rows.append(dict(pair=p, width=w, side=s, hyp=name,
                    trades=dec, timeouts=int((r == 0).sum()), wr=k/dec,
                    wl=lo, wh=hi, ER=(2*k-dec)/dec, PF=k/max(dec-k, 1)))

            score(np.ones(len(ft), bool), "ALL_BARS(null)")
            for c in [c for c in ft.columns if c not in ("hour", "dow")]:
                try: q = pd.qcut(ft[c], NQ, labels=False, duplicates="drop")
                except Exception: continue
                for b in np.unique(q.dropna()):
                    score((q == b).values, f"{c}_q{int(b)}")
            for hh in range(24): score((ft.hour == hh).values, f"hour_{hh:02d}")
            for dd in range(5):  score((ft.dow == dd).values, f"dow_{dd}")

r = pd.DataFrame(rows)
r.to_csv(r"C:\personal\ICT_v7\reports\search_IS_seq.csv", index=False)
null = r[r.hyp == "ALL_BARS(null)"]
r = r[r.hyp != "ALL_BARS(null)"]

print(f"hypotheses tested : {len(r):,}   (independent, non-overlapping trades)")
print(f"\n=== NULL (take every bar) ===")
print(null[["pair","width","side","trades","wr","wl","wh"]].to_string(index=False))
print(f"\n=== WIN-RATE DISTRIBUTION over {len(r):,} hypotheses ===")
print(r.wr.describe(percentiles=[.5,.9,.99]).to_string())
for th in (.70, .60, .55, .52):
    sub = r[r.wr >= th]
    print(f"  WR >= {th:.2f} : {len(sub):>4}   of which Wilson-low > 0.50 : {(sub.wl>0.50).sum()}")
print(f"\n=== TOP 15 BY WIN RATE (min {MIN_TRADES} trades) ===")
print(r.nlargest(15,"wr")[["pair","width","side","hyp","trades","wr","wl","wh","PF"]].to_string(index=False))
print(f"\n=== SURVIVORS: Wilson 95% lower bound above 50% ===")
sv = r[r.wl > 0.50].sort_values("wl", ascending=False)
print(f"{len(sv)} of {len(r):,}")
print(sv.head(20)[["pair","width","side","hyp","trades","wr","wl","wh","PF"]].to_string(index=False))
