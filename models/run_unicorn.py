import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn import detect
from models.unicorn_bt import PIP, resample, backtest, wilson

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
IS_END = pd.Timestamp("2025-06-30")
rows = []
for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    for tf in ("5min", "15min", "60min"):
        b, atr = resample(df, tf)
        for n in (3, 5):
            sg = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values,
                        atr, n=n, disp_k=1.0)
            for em in ("edge", "ce"):
                tr = backtest(df, sg, b.index, PIP[p], pd.Timedelta(tf), entry_mode=em)
                if len(tr) == 0: continue
                for split, m in (("IS", tr.t <= IS_END), ("OOS", tr.t > IS_END)):
                    t = tr[m]
                    if len(t) == 0: continue
                    k = int((t.out == 1).sum()); nn = len(t)      # timeouts counted, not dropped
                    to = int((t.out == 0).sum())
                    wl, wh = wilson(k, nn)
                    rows.append(dict(pair=p, tf=tf, n=n, entry=em, split=split,
                        signals=len(t), trades=nn, timeout=to,
                        wr=k/nn, wl=wl, wh=wh, PF=k/max(nn-k,1),
                        med_R_pips=float(t.R_pips.median()),
                        med_hold_min=int(t.bars.median())))
r = pd.DataFrame(rows)
r.to_csv(r"C:\personal\ICT_v7\reports\unicorn.csv", index=False)
pd.set_option("display.width", 200)
print("=== ICT UNICORN MODEL — 1:1 RR, structure stop, real bid/ask fills ===\n")
print(r.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
i = r[r.split == "IS"]; o = r[r.split == "OOS"]
print(f"\nconfigs run: {len(i)}   total IS trades {i.trades.sum():,}   OOS trades {o.trades.sum():,}")
print(f"POOLED IS  win rate: {(i.wr*i.trades).sum()/i.trades.sum():.4f}")
print(f"POOLED OOS win rate: {(o.wr*o.trades).sum()/o.trades.sum():.4f}")
print(f"IS  configs with WR>=0.70: {(i.wr>=.70).sum()}   >=0.55: {(i.wr>=.55).sum()}   Wilson-low>0.50: {(i.wl>.50).sum()}")
print(f"OOS configs with WR>=0.70: {(o.wr>=.70).sum()}   >=0.55: {(o.wr>=.55).sum()}   Wilson-low>0.50: {(o.wl>.50).sum()}")
