"""ONE pass on reserved data. Candidates were chosen in-sample only."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from census.features import build
from engine.barrier import sequential
from census.search2 import wilson

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
OOS_START = "2025-07-01"

cand = pd.read_csv(r"C:\personal\ICT_v7\reports\search_IS_seq.csv")
cand = cand[cand.hyp != "ALL_BARS(null)"].nlargest(15, "wr")

res = []
cache = {}
for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    oc = pd.read_parquet(DATA / f"{p}_outcomes.parquet")
    ft = build(df, PIP[p]).loc[oc.index]
    is_m = oc.index <= "2025-06-30"
    cache[p] = (ft, oc, is_m)

for _, c in cand.iterrows():
    ft, oc, is_m = cache[c.pair]
    name = c.hyp
    if name.startswith("hour_"):
        mask_all = (ft.hour == int(name[5:])).values
    elif name.startswith("dow_"):
        mask_all = (ft.dow == int(name[4:])).values
    else:
        feat, b = name.rsplit("_q", 1)
        # quantile edges fitted on IN-SAMPLE only, then applied forward
        edges = pd.qcut(ft[feat][is_m], 5, retbins=True, duplicates="drop")[1]
        edges[0], edges[-1] = -np.inf, np.inf
        mask_all = (pd.cut(ft[feat], edges, labels=False) == int(b)).values
    oos_m = (oc.index >= OOS_START).values
    sig = np.ascontiguousarray((mask_all & oos_m).astype(np.bool_))
    out = np.ascontiguousarray(oc[f"o_{c.width}{c.side}"].values.astype(np.int8))
    hld = np.ascontiguousarray(oc[f"h_{c.width}{c.side}"].values.astype(np.int64))
    r, _ = sequential(sig, out, hld)
    dec = int((r != 0).sum()); k = int((r == 1).sum())
    lo, hi = wilson(k, dec) if dec else (np.nan, np.nan)
    res.append(dict(pair=c.pair, width=c.width, side=c.side, hyp=name,
                    IS_wr=c.wr, IS_n=c.trades, OOS_n=dec,
                    OOS_wr=k/dec if dec else np.nan, OOS_wl=lo, OOS_wh=hi,
                    decay=(k/dec - c.wr) if dec else np.nan,
                    OOS_PF=k/max(dec-k,1) if dec else np.nan))

o = pd.DataFrame(res)
o.to_csv(r"C:\personal\ICT_v7\reports\oos_test.csv", index=False)
print("=== HOLD-OUT TEST  2025-07-01 -> 2026-09-04 (never used in search) ===\n")
print(o.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print(f"\ncandidates tested            : {len(o)}")
print(f"OOS win rate >= 0.70         : {(o.OOS_wr>=0.70).sum()}")
print(f"OOS win rate >= 0.55         : {(o.OOS_wr>=0.55).sum()}")
print(f"OOS win rate >  0.50         : {(o.OOS_wr>0.50).sum()}")
print(f"OOS Wilson lower bound > 0.50: {(o.OOS_wl>0.50).sum()}")
print(f"mean IS win rate {o.IS_wr.mean():.4f}  ->  mean OOS win rate {o.OOS_wr.mean():.4f}   (decay {o.decay.mean():+.4f})")
