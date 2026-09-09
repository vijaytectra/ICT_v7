"""DAY-TRADING BOX: tight stops, max 4h hold. The box the operator actually wants."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from engine.barrier import run

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PIP = {"EURUSD":1e-4,"GBPUSD":1e-4,"USDJPY":1e-2}
WIDTHS = [5, 8, 12]
MAXBARS = 240                      # 4 hours — hard day-trade ceiling

for p in PIP:
    df = pd.read_parquet(DATA/f"{p}.parquet")
    idx = np.arange(0, len(df)-MAXBARS-1)
    out = {}
    for w in WIDTHS:
        for L in (True, False):
            o,h = run(df, PIP[p], w, L, idx, max_bars=MAXBARS)
            s = "L" if L else "S"
            out[f"o_{w}{s}"], out[f"h_{w}{s}"] = o, h
            dec=(o!=0).sum()
            print(f"{p} {w}p {s}: null_wr={(o==1).sum()/dec:.4f} "
                  f"unresolved_in_4h={(o==0).mean():.1%} med_hold={int(np.median(h[o!=0]))}m", flush=True)
    pd.DataFrame(out, index=df.index[idx]).to_parquet(DATA/f"{p}_dt.parquet")
