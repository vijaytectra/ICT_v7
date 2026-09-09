"""Full validation of the single config selected in-sample."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v2 import detect
from models.bt2 import run, summarise
from models.unicorn_bt import PIP, resample
DATA = pathlib.Path(r"C:\personal\ICT_v7\data"); IS_END = pd.Timestamp("2025-06-30"); TF="5min"
D = dict(n=3, max_gap=60, disp_ratio=0.5, use_body=False)
B = dict(entry_mode="edge", stop_mode="sweep", rr=2.0, kz="LDN", pd_gate=None, ote=False)

def trades(comm):
    a = []
    for p in PIP:
        df = pd.read_parquet(DATA/f"{p}.parquet"); b, atr = resample(df, TF)
        sg = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values, atr, **D)
        t = run(df, sg, b.index, PIP[p], pd.Timedelta(TF), comm_pips=comm, **B)
        if len(t): t["pair"] = p; a.append(t)
    return pd.concat(a).sort_values("t").reset_index(drop=True)

t = trades(0.7)
print("=== FINAL CONFIG: 5m Unicorn | swing n=3 | sweep->MSS <=60 bars | MSS body/range>=0.5")
print("    | entry = zone edge | stop = swept extreme | target = 2R | London KZ (09-12 EET) ===\n")
s = summarise(t); print(f"ALL  n={s['trades']}  WR {s['wr']:.4f}  E[R] {s['ER']:+.4f}  PF {s['PF']:.2f}  totR {s['totR']:+.1f}")
print(f"     median stop {s['med_R_pips']:.1f} pips | median hold {s['med_hold']} min | timeouts {s['timeouts']}")
print(f"     {len(t)/32:.1f} trades/month\n")
print("--- QUARTER BY QUARTER ---")
t["q"] = t.t.dt.to_period("Q"); cum = 0
print(f"{'quarter':>9}{'n':>5}{'WR':>8}{'R':>8}{'cumR':>9}")
for q, g in t.groupby("q"):
    cum += g.netR.sum()
    print(f"{str(q):>9}{len(g):>5}{(g.out==1).mean():>8.3f}{g.netR.sum():>+8.1f}{cum:>+9.1f}")
print("\n--- PER PAIR ---")
for p in PIP:
    g = t[t.pair == p]
    if len(g): print(f"{p}: n={len(g):>3} WR {(g.out==1).mean():.3f} E[R] {g.netR.mean():+.3f} "
                     f"PF {g.netR[g.netR>0].sum()/max(-g.netR[g.netR<0].sum(),1e-9):.2f} totR {g.netR.sum():+.1f}")
print("\n--- COST SENSITIVITY ---")
print(f"{'comm':>7}{'E[R]':>9}{'PF':>7}{'totR':>9}")
for c in (0.0, 0.4, 0.7, 1.0, 1.5, 2.0):
    x = trades(c); g = x.netR[x.netR>0].sum(); b_ = -x.netR[x.netR<0].sum()
    print(f"{c:>6.1f}p{x.netR.mean():>+9.4f}{g/b_:>7.2f}{x.netR.sum():>+9.1f}")
eq = t.netR.cumsum(); dd = (eq - eq.cummax())
print(f"\n--- RISK ---\nmax drawdown {dd.min():.1f}R | longest losing streak "
      f"{max((len(list(g)) for k,g in __import__('itertools').groupby(t.out==-1) if k), default=0)}")
rng = np.random.default_rng(0); v = t.netR.values
bs = np.array([v[rng.integers(0,len(v),len(v))].mean() for _ in range(20000)])
print(f"bootstrap E[R] 95% CI [{np.percentile(bs,2.5):+.4f}, {np.percentile(bs,97.5):+.4f}]  P(edge>0) = {(bs>0).mean():.1%}")
t.drop(columns=["q"]).to_csv(r"C:\personal\ICT_v7\reports\final_trades.csv", index=False)
