"""Marginal-contribution ablation. BASE + exactly one rule change per arm, IS only.
Every arm pays the same 0.7 pip commission on top of the spread already in the fills."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v2 import detect
from models.bt2 import run, summarise
from models.unicorn_bt import PIP, resample

DATA = pathlib.Path(r"C:\personal\ICT_v7\data"); IS_END = pd.Timestamp("2025-06-30")
COMM = 0.7; TF = "5min"
DET = dict(n=3, max_gap=30, disp_atr=0.0, disp_ratio=0.0, leg_atr=0.0, use_body=False)
BT  = dict(entry_mode="edge", stop_mode="sweep", rr=1.0, kz=None, pd_gate=None, ote=False)

ARMS = [
    ("BASE (sweep+MSS+breaker+FVG overlap)", {}, {}),
    ("R3  sweep->MSS window 60 bars",     dict(max_gap=60), {}),
    ("R4  leg displacement >= 1.0 ATR",   dict(leg_atr=1.0), {}),
    ("R4  leg displacement >= 2.0 ATR",   dict(leg_atr=2.0), {}),
    ("R4  leg displacement >= 3.0 ATR",   dict(leg_atr=3.0), {}),
    ("R4  MSS candle body/range >= 0.5",  dict(disp_ratio=0.5), {}),
    ("R4  MSS candle body/range >= 0.7",  dict(disp_ratio=0.7), {}),
    ("R7  breaker = BODY not wicks",      dict(use_body=True), {}),
    ("--  swing lookback n=5",            dict(n=5), {}),
    ("R9  entry at CE not zone edge",     {}, dict(entry_mode="ce")),
    ("R15 stop at zone far edge",         {}, dict(stop_mode="zone")),
    ("R15 stop at MSS origin",            {}, dict(stop_mode="mss")),
    ("R16 target 2R",                     {}, dict(rr=2.0)),
    ("R16 target 3R",                     {}, dict(rr=3.0)),
    ("R12 London killzone only",          {}, dict(kz="LDN")),
    ("R12 NY killzone only",              {}, dict(kz="NY")),
    ("R10 discount/premium gate 0.50",    {}, dict(pd_gate=0.50)),
    ("R10 deep discount gate 0.35",       {}, dict(pd_gate=0.35)),
    ("R11 OTE 62-79% only",               {}, dict(ote=True)),
]

cache = {}
def signals(dk):
    key = tuple(sorted(dk.items()))
    if key not in cache:
        out = {}
        for p in PIP:
            df = pd.read_parquet(DATA / f"{p}.parquet"); b, atr = resample(df, TF)
            out[p] = (df, b, detect(b.o_b.values, b.h_b.values, b.l_b.values,
                                    b.c_b.values, atr, **dk))
        cache[key] = out
    return cache[key]

rows = []
for label, dk, bk in ARMS:
    D = {**DET, **dk}; B = {**BT, **bk}
    allt = []
    for p, (df, b, sg) in signals(D).items():
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), comm_pips=COMM, **B)
        if len(t): allt.append(t)
    if not allt: rows.append(dict(arm=label, trades=0)); continue
    t = pd.concat(allt); t = t[t.t <= IS_END]
    s = summarise(t, label)
    if s: rows.append(s)

r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\ablation.csv", index=False)
base = r[r.arm.str.startswith("BASE")].iloc[0]
r["d_wr"] = r.wr - base.wr; r["d_ER"] = r.ER - base.ER
pd.set_option("display.width", 250)
print(f"=== ABLATION — IN-SAMPLE ONLY, 5min, 3 pairs, {COMM}p commission included ===")
print("(each arm = BASE + exactly ONE rule change)\n")
print(r[["arm","trades","wr","wl","wh","ER","PF","totR","med_R_pips","d_wr","d_ER"]]
      .to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print(f"\nBASE: {int(base.trades)} trades, WR {base.wr:.4f}, E[R] {base.ER:+.4f}, PF {base.PF:.2f}")
w = r[(r.d_ER > 0) & (r.trades >= 60)].sort_values("d_ER", ascending=False)
print(f"\narms that IMPROVE E[R] with >=60 trades: {len(w)} of {len(r)-1}")
print(w[["arm","trades","wr","ER","PF","d_ER"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
