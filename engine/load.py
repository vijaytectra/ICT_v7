"""CSV (Dukascopy bid/ask 1m) -> single merged parquet per pair."""
import pandas as pd, numpy as np, pathlib

SRC = pathlib.Path(r"C:\Users\Vijayakumar R\Documents")
OUT = pathlib.Path(r"C:\personal\ICT_v7\data")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}

def _read(p, side):
    f = SRC / f"{p}_1 Min_{side}_2024.01.01_2026.09.05.csv"
    d = pd.read_csv(f, header=0, names=["t", "o", "h", "l", "c", "v"],
                    parse_dates=["t"], date_format="%Y.%m.%d %H:%M:%S")
    return d.set_index("t")

def build(p):
    b, a = _read(p, "Bid"), _read(p, "Ask")
    df = b.join(a, how="inner", lsuffix="_b", rsuffix="_a")
    # drop flat no-quote bars (weekend / dead ticks) and inverted spreads
    df = df[(df.v_b > 0) | (df.v_a > 0)]
    df = df[df.c_a >= df.c_b]
    df["spread"] = (df.c_a - df.c_b) / PIP[p]
    df = df[df.spread < 20]                      # kill quote glitches
    df.index.name = "t"
    df.to_parquet(OUT / f"{p}.parquet")
    print(f"{p:7s} rows={len(df):>9,} {df.index.min()} -> {df.index.max()} "
          f"median_spread={df.spread.median():.2f}pip")

if __name__ == "__main__":
    for p in PAIRS:
        build(p)
