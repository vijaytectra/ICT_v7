"""Precompute 1:1 barrier outcome for EVERY bar, once, per (pair,width,side).
Outcomes are feature-independent -> every later hypothesis is a free groupby."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from engine.barrier import run

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
WIDTHS = [10, 20, 30]

for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    idx = np.arange(0, len(df) - 1441)
    out = {}
    for w in WIDTHS:
        for is_long in (True, False):
            o, h = run(df, PIP[p], w, is_long, idx)
            s = "L" if is_long else "S"
            out[f"o_{w}{s}"] = o
            out[f"h_{w}{s}"] = h
            print(f"{p} {w}p {s}: wr={(o==1).sum()/max((o!=0).sum(),1):.4f}", flush=True)
    pd.DataFrame(out, index=df.index[idx]).to_parquet(DATA / f"{p}_outcomes.parquet")
    print(f"  saved {p} outcomes {len(idx):,} bars", flush=True)
