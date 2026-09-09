"""LR3 combinations on IS, then ONE hold-out pass."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v2 import detect
from models.bt3 import run, summarise
from models.unicorn_bt import PIP, resample
DATA = pathlib.Path(r"C:\personal\ICT_v7\data"); IS_END = pd.Timestamp("2025-06-30"); TF = "5min"
D = dict(n=3, max_gap=60, disp_ratio=0.5, use_body=False)
PRE = {}
for p in PIP:
    df = pd.read_parquet(DATA/f"{p}.parquet"); b, atr = resample(df, TF)
    sg = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values, atr, **D)
    h1 = df.c_b.resample("60min").last(); ema = h1.ewm(span=20, adjust=False).mean()
    bias = np.sign(h1 - ema).shift(1).reindex(df.index, method="ffill").fillna(0).values
    PRE[p] = (df, b, sg, bias)

ARMS = [("BASE", {}), ("LR3", dict(lr3=True)),
        ("LR3 + LR2>=9", dict(lr3=True, lr2=9)),
        ("LR3 + LR2>=10", dict(lr3=True, lr2=10)),
        ("LR3 + kz LDN+NY", dict(lr3=True, kz="LDN+NY")),
        ("LR3 + kz LDN+NY + LR2>=9", dict(lr3=True, kz="LDN+NY", lr2=9)),
        ("LR3 + rr3", dict(lr3=True, rr=3.0)),
        ("LR3 + rr1.5", dict(lr3=True, rr=1.5))]
rows = []
for label, kw in ARMS:
    allt = []
    for p, (df, b, sg, bias) in PRE.items():
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), htf_bias=bias, **kw)
        if len(t): t["pair"] = p; allt.append(t)
    t = pd.concat(allt).sort_values("t")
    i = summarise(t[t.t <= IS_END]); o = summarise(t[t.t > IS_END])
    if not i or not o: continue
    rows.append(dict(arm=label, IS_n=i["trades"], IS_wr=i["wr"], IS_ER=i["ER"], IS_PF=i["PF"],
                     OOS_n=o["trades"], OOS_wr=o["wr"], OOS_wl=o["wl"], OOS_ER=o["ER"], OOS_PF=o["PF"],
                     ALL_n=len(t), ALL_wr=summarise(t)["wr"], ALL_ER=summarise(t)["ER"],
                     ALL_PF=summarise(t)["PF"], ALL_totR=summarise(t)["totR"]))
r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\lr_final.csv", index=False)
pd.set_option("display.width", 260)
print("=== LR3 COMBINATIONS: in-sample pick, then hold-out ===\n")
print(r[["arm","IS_n","IS_wr","IS_ER","IS_PF","OOS_n","OOS_wr","OOS_ER","OOS_PF","ALL_n","ALL_wr","ALL_PF","ALL_totR"]]
      .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
b = r.sort_values("IS_ER", ascending=False).iloc[0]
print(f"\nIS-best arm: {b.arm}")
print(f"  IS  n={int(b.IS_n)} WR {b.IS_wr:.4f} E[R] {b.IS_ER:+.4f} PF {b.IS_PF:.2f}")
print(f"  OOS n={int(b.OOS_n)} WR {b.OOS_wr:.4f} E[R] {b.OOS_ER:+.4f} PF {b.OOS_PF:.2f}")
print(f"  ALL n={int(b.ALL_n)} WR {b.ALL_wr:.4f} E[R] {b.ALL_ER:+.4f} PF {b.ALL_PF:.2f} totR {b.ALL_totR:+.1f}")
