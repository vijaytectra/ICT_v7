"""Test each loss-reduction rule separately, IS first. Same protocol as before."""
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
    m5end = pd.Series(False, index=df.index)                    # M5 close bars, for LR1
    m5end.loc[m5end.index.minute % 5 == 4] = True
    h1 = df.c_b.resample("60min").last()                        # LR3 HTF bias, closed bars only
    ema = h1.ewm(span=20, adjust=False).mean()
    bias = np.sign(h1 - ema).shift(1).reindex(df.index, method="ffill").fillna(0).values
    PRE[p] = (df, b, sg, m5end.values, bias)

ARMS = [("BASE (final config)", {}),
        ("LR1 failed-breaker early exit", dict(lr1=True)),
        ("LR2 displacement score >= 8",   dict(lr2=8)),
        ("LR2 displacement score >= 9",   dict(lr2=9)),
        ("LR2 displacement score >= 10",  dict(lr2=10)),
        ("LR3 HTF (H1) bias must agree",  dict(lr3=True)),
        ("LR4 50% at 1R, SL to BE",       dict(lr4=0.5)),
        ("LR4 33% at 1R, SL to BE",       dict(lr4=0.33)),
        ("LR1+LR4",                       dict(lr1=True, lr4=0.5)),
        ("LR2>=9 + LR4",                  dict(lr2=9, lr4=0.5)),
        ("LR1+LR2>=9+LR4",                dict(lr1=True, lr2=9, lr4=0.5))]

rows = []
for label, kw in ARMS:
    allt = []
    for p, (df, b, sg, m5, bias) in PRE.items():
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), m5_close_idx=m5, htf_bias=bias, **kw)
        if len(t): allt.append(t)
    if not allt: continue
    t = pd.concat(allt)
    s = summarise(t[t.t <= IS_END], label)
    if s: rows.append(s)
r = pd.DataFrame(rows)
base = r.iloc[0]; r["d_ER"] = r.ER - base.ER; r["d_PF"] = r.PF - base.PF
pd.set_option("display.width", 250)
print("=== LOSS-REDUCTION RULES — IN-SAMPLE ONLY, 0.7p commission ===\n")
print(r[["arm","trades","wr","ER","PF","totR","stopped","inval","be","tp","d_ER","d_PF"]]
      .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
r.to_csv(r"C:\personal\ICT_v7\reports\lr_IS.csv", index=False)
