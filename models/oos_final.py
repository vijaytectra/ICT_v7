"""Stage 3: ONE pass on reserved data. All 54 combos, so the IS->OOS relationship is
visible rather than a single cherry-picked config."""
import sys, pathlib, itertools, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v2 import detect
from models.bt2 import run, summarise
from models.unicorn_bt import PIP, resample

DATA = pathlib.Path(r"C:\personal\ICT_v7\data"); IS_END = pd.Timestamp("2025-06-30")
COMM, TF = 0.7, "5min"
base = {p: (lambda df: (df, resample(df, TF)))(pd.read_parquet(DATA/f"{p}.parquet")) for p in PIP}
cache = {}
def sig(dk):
    k = tuple(sorted(dk.items()))
    if k not in cache:
        cache[k] = {p: (df, b, detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values,
                                      atr, **dk)) for p, (df, (b, atr)) in base.items()}
    return cache[k]

rows = []
for gap, ratio, kz, rr in itertools.product([30, 60], [0.0, 0.5, 0.7], ["LDN","NY","LDN+NY",None], [1.0,1.5,2.0]):
    D = dict(n=3, max_gap=gap, disp_ratio=ratio, use_body=False)
    allt = []
    for p, (df, b, sg) in sig(D).items():
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), rr=rr, kz=kz, comm_pips=COMM)
        if len(t): allt.append(t)
    if not allt: continue
    t = pd.concat(allt).sort_values("t")
    i = summarise(t[t.t <= IS_END]); o = summarise(t[t.t > IS_END])
    if not i or not o or i["trades"] < 40: continue
    rows.append(dict(arm=f"gap{gap} r{ratio} kz{kz or '-'} rr{rr}", gap=gap, ratio=ratio,
        kz=kz or "-", rr=rr,
        IS_n=i["trades"], IS_wr=i["wr"], IS_ER=i["ER"], IS_PF=i["PF"],
        OOS_n=o["trades"], OOS_wr=o["wr"], OOS_wl=o["wl"], OOS_ER=o["ER"], OOS_PF=o["PF"]))

r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\final_IS_OOS.csv", index=False)
pd.set_option("display.width", 250)
print(f"=== STAGE 3: HOLD-OUT 2025-07-01 -> 2026-09-04, all {len(r)} combos, {COMM}p commission ===\n")
print("--- ranked by IN-SAMPLE E[R] (the pick you would actually have made) ---")
s = r.sort_values("IS_ER", ascending=False)
print(s[["arm","IS_n","IS_wr","IS_ER","IS_PF","OOS_n","OOS_wr","OOS_ER","OOS_PF"]]
      .head(12).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print(f"\nIS->OOS correlation   E[R]: {r.IS_ER.corr(r.OOS_ER):+.3f}    win rate: {r.IS_wr.corr(r.OOS_wr):+.3f}")
print(f"combos positive in IS: {(r.IS_ER>0).sum()}/{len(r)}   positive in OOS: {(r.OOS_ER>0).sum()}/{len(r)}")
print(f"positive in BOTH: {((r.IS_ER>0)&(r.OOS_ER>0)).sum()}/{len(r)}")
top = s.iloc[0]
print(f"\nIS-BEST config -> {top.arm}")
print(f"   IS : n={int(top.IS_n)} WR {top.IS_wr:.4f} E[R] {top.IS_ER:+.4f} PF {top.IS_PF:.2f}")
print(f"   OOS: n={int(top.OOS_n)} WR {top.OOS_wr:.4f} E[R] {top.OOS_ER:+.4f} PF {top.OOS_PF:.2f}")
b1 = r[r.rr == 1.0].sort_values("IS_wr", ascending=False).iloc[0]
print(f"\nIS-BEST at rr=1.0 (the 70% target) -> {b1.arm}")
print(f"   IS : n={int(b1.IS_n)} WR {b1.IS_wr:.4f} PF {b1.IS_PF:.2f}")
print(f"   OOS: n={int(b1.OOS_n)} WR {b1.OOS_wr:.4f} Wilson-low {b1.OOS_wl:.4f} PF {b1.OOS_PF:.2f}")
print(f"\nOOS win rate >= 0.70 anywhere: {(r.OOS_wr>=0.70).sum()}   OOS Wilson-low > 0.50: {(r.OOS_wl>0.50).sum()}")
