"""Systematic in-sample search, day-MATCHED null.

For each hypothesis, on every day it fires we compare its mean R against the
mean R of *all* bars on that same day. That removes the day-weighting artifact:
a bucket that only fires on quiet days is no longer credited for it.
OOS (after IS_END) is never read here.
"""
import sys, pathlib, numpy as np, pandas as pd
from scipy import stats as st
sys.path.insert(0, r"C:\personal\ICT_v7")
from census.features import build

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
WIDTHS = [10, 20, 30]
IS_END = "2025-06-30"
NQ, MIN_DAYS, MIN_N = 5, 60, 400

rows = []
for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    oc = pd.read_parquet(DATA / f"{p}_outcomes.parquet")
    ft = build(df, PIP[p]).loc[oc.index]
    m = oc.index <= IS_END
    ft, oc = ft[m], oc[m]
    day = pd.Series(oc.index.normalize(), index=oc.index)
    cols = [c for c in ft.columns if c not in ("hour", "dow")]

    for w in WIDTHS:
        for s in ("L", "S"):
            R = oc[f"o_{w}{s}"].astype(float)
            day_null = R.groupby(day).mean()               # per-day baseline
            null_wr = (R == 1).sum() / max((R != 0).sum(), 1)
            null_ER = R.mean()

            def score(mask, name):
                r = R[mask]
                if len(r) < MIN_N: return
                d = day[mask]
                g = r.groupby(d).mean()
                g = g[g.index.isin(day_null.index)]
                if len(g) < MIN_DAYS: return
                diff = g - day_null.reindex(g.index)       # day-matched lift
                se = diff.std(ddof=1) / np.sqrt(len(diff))
                dec = (r != 0).sum()
                rows.append(dict(pair=p, width=w, side=s, hyp=name, n=len(r),
                    days=len(g), wr=(r == 1).sum()/max(dec,1), null_wr=null_wr,
                    ER=r.mean(), null_ER=null_ER, lift=diff.mean(),
                    t=diff.mean()/se if se > 0 else 0.0))

            for c in cols:
                v = ft[c]
                try: q = pd.qcut(v, NQ, labels=False, duplicates="drop")
                except Exception: continue
                for b in np.unique(q.dropna()):
                    score((q == b).values, f"{c}_q{int(b)}")
            for hh in range(24): score((ft.hour == hh).values, f"hour_{hh:02d}")
            for dd in range(5):  score((ft.dow == dd).values, f"dow_{dd}")

r = pd.DataFrame(rows)
r["p"] = 2 * (1 - st.norm.cdf(r.t.abs()))
r.to_csv(r"C:\personal\ICT_v7\reports\search_IS.csv", index=False)

print(f"hypotheses tested : {len(r):,}")
print(f"pooled NULL win rate @1:1 : {r.null_wr.mean():.4f}")
print(f"\n=== WIN-RATE DISTRIBUTION across all {len(r):,} hypotheses ===")
print(r.wr.describe(percentiles=[.5,.9,.99,.999]).to_string())
print(f"\n  WR >= 0.70 : {(r.wr>=0.70).sum()}")
print(f"  WR >= 0.60 : {(r.wr>=0.60).sum()}")
print(f"  WR >= 0.55 : {(r.wr>=0.55).sum()}")
print(f"  WR >= 0.52 : {(r.wr>=0.52).sum()}")
print(f"\n=== TOP 12 BY WIN RATE ===")
print(r.nlargest(12,"wr")[["pair","width","side","hyp","n","days","wr","null_wr","lift","t","p"]].to_string(index=False))
print(f"\n=== TOP 12 BY DAY-MATCHED t-STAT ===")
print(r.nlargest(12,"t")[["pair","width","side","hyp","n","days","wr","null_wr","lift","t","p"]].to_string(index=False))
bonf = 0.05/len(r)
print(f"\nBonferroni threshold p < {bonf:.2e}  -> survivors: {(r.p<bonf).sum()}")
print(f"max |t| observed: {r.t.abs().max():.2f}   (expected max |t| from pure noise on {len(r):,} tests ~ {st.norm.ppf(1-0.5/len(r)):.2f})")
