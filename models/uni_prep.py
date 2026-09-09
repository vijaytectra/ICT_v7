"""Cache the frozen index-Unicorn signals so the execution lab can be swept quickly."""
import pathlib, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v5 import detect
from models import ict_system

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
CACHE = pathlib.Path(r"C:\personal\ICT_v7\reports\uni_cache.pkl")
IDX = ["USATECH", "USA500", "USA30"]
PERIODS = {"DEV": "_H", "VAL": ""}          # DEV 2015-2023, VAL 2024-2026

# FROZEN detector - SETUP_INDEX.md, not to be searched over
CFG = dict(n=5, max_gap=60, disp_ratio=0.5, pool="swing", reclaim_bars=0, wick_frac=0.0)
TF = "15min"


def resample(df, tf=TF):
    b = df[["o_b", "h_b", "l_b", "c_b"]].resample(tf).agg(
        {"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    return b, tr.rolling(14).mean().values


def build():
    out = {}
    for per, suf in PERIODS.items():
        for sym in IDX:
            df = pd.read_parquet(DATA / f"{sym}{suf}.parquet")
            b, atr = resample(df)
            sg = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values, atr, **CFG)
            out[(per, sym)] = dict(bars=b.index, sigs=sg,
                                   ctx=ict_system.daily_context(df),
                                   asia=ict_system.session_pools(df))
            print(f"{per} {sym}: {len(sg)} signals, {len(b)} M15 bars", flush=True)
    with open(CACHE, "wb") as f: pickle.dump(out, f)
    return out


if __name__ == "__main__":
    build()
