"""NULL MAP: unconditional 1:1 entries. What a coin flip looks like after spread."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from engine.barrier import run

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}
WIDTHS = [5, 10, 15, 20, 30, 50]
STRIDE = 10

rows = []
for p in PIP:
    df = pd.read_parquet(DATA / f"{p}.parquet")
    idx = np.arange(0, len(df) - 1441, STRIDE)
    for w in WIDTHS:
        for is_long in (True, False):
            o, h = run(df, PIP[p], w, is_long, idx)
            win, loss, to = (o == 1).sum(), (o == -1).sum(), (o == 0).sum()
            dec = win + loss
            rows.append(dict(pair=p, width=w, side="long" if is_long else "short",
                             n=len(idx), decided=dec, timeout=to,
                             wr=win / dec if dec else np.nan,
                             med_bars=int(np.median(h))))
            print(f"{p} {w:>2}p {'L' if is_long else 'S'} "
                  f"wr={win/dec:.4f} n={dec:,} timeout={to/len(idx):.1%}", flush=True)

r = pd.DataFrame(rows)
r.to_csv(r"C:\personal\ICT_v7\reports\baseline_null.csv", index=False)
print("\n=== NULL WIN RATE @ 1:1 (both sides pooled) ===")
g = r.groupby(["pair", "width"]).apply(
    lambda x: pd.Series({"wr": (x.wr * x.decided).sum() / x.decided.sum(),
                         "n": x.decided.sum()}), include_groups=False)
print(g.to_string())
