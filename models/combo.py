"""Stage 2: combine only the rules the ablation showed help. IS ONLY."""
import sys, pathlib, itertools, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v2 import detect
from models.bt2 import run, summarise
from models.unicorn_bt import PIP, resample

DATA = pathlib.Path(r"C:\personal\ICT_v7\data"); IS_END = pd.Timestamp("2025-06-30")
COMM, TF = 0.7, "5min"
cache = {}
def sig(dk):
    k = tuple(sorted(dk.items()))
    if k not in cache:
        cache[k] = {p: (lambda df, ba: (df, ba[0], detect(ba[0].o_b.values, ba[0].h_b.values,
                        ba[0].l_b.values, ba[0].c_b.values, ba[1], **dk)))(
                        pd.read_parquet(DATA/f"{p}.parquet"),
                        resample(pd.read_parquet(DATA/f"{p}.parquet"), TF)) for p in PIP}
    return cache[k]

rows = []
for gap, ratio, kz, rr in itertools.product([30, 60], [0.0, 0.5, 0.7], ["LDN", "NY", "LDN+NY", None], [1.0, 1.5, 2.0]):
    D = dict(n=3, max_gap=gap, disp_ratio=ratio, use_body=False)
    allt = []
    for p, (df, b, sg) in sig(D).items():
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), rr=rr, kz=kz, comm_pips=COMM)
        if len(t): allt.append(t)
    if not allt: continue
    t = pd.concat(allt); t = t[t.t <= IS_END]
    s = summarise(t, f"gap{gap} ratio{ratio} kz{kz or '-'} rr{rr}")
    if s and s["trades"] >= 40:
        s.update(gap=gap, ratio=ratio, kz=kz or "-", rr=rr); rows.append(s)

r = pd.DataFrame(rows).sort_values("ER", ascending=False)
r.to_csv(r"C:\personal\ICT_v7\reports\combo_IS.csv", index=False)
pd.set_option("display.width", 250)
print(f"=== STAGE 2 COMBINATIONS — IN-SAMPLE ONLY, {COMM}p commission, min 40 trades ===")
print(f"combinations evaluated: {len(r)}\n")
print(r[["arm","trades","wr","wl","wh","ER","PF","totR","med_R_pips","med_hold"]]
      .head(15).to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print(f"\ncombos with positive E[R]: {(r.ER>0).sum()} of {len(r)}")
print(f"combos with Wilson lower > 0.50: {(r.wl>0.50).sum()}")
print(f"best IS: {r.iloc[0].arm}  ->  WR {r.iloc[0].wr:.4f}  E[R] {r.iloc[0].ER:+.4f}  PF {r.iloc[0].PF:.2f}  n={int(r.iloc[0].trades)}")
