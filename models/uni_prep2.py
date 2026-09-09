"""Detector variants the index config never tried, all taken from the sources.

  pool='equal'   draw-on-liquidity.md and liquidity-sweep.md both define the pool as
                 RELATIVE EQUAL highs/lows - two swings within tolerance - not any minor
                 swing.  SETUP_INDEX froze pool='swing', which raids every swing there is.
  nested=True    SrsBlack 08-breaker-blocks: the gap must sit INSIDE the breaker body, not
                 merely intersect it.
"""
import pathlib, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_v5 import detect
from models import ict_system
from models.uni_prep import resample, DATA, IDX, PERIODS

BASE = dict(n=5, max_gap=60, disp_ratio=0.5, reclaim_bars=0, wick_frac=0.0)
VARIANTS = {
    "equal":        dict(pool="equal"),
    "equal_nested": dict(pool="equal", nested=True),
    "swing_nested": dict(pool="swing", nested=True),
}

if __name__ == "__main__":
    out = {}
    for name, over in VARIANTS.items():
        for per, suf in PERIODS.items():
            for sym in IDX:
                df = pd.read_parquet(DATA / f"{sym}{suf}.parquet")
                b, atr = resample(df)
                sg = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values,
                            atr, **{**BASE, **over})
                out[(name, per, sym)] = dict(bars=b.index, sigs=sg,
                                             ctx=ict_system.daily_context(df),
                                             asia=ict_system.session_pools(df))
                print(f"{name:14s} {per} {sym}: {len(sg)} signals", flush=True)
    with open(r"C:\personal\ICT_v7\reports\uni_cache2.pkl", "wb") as f:
        pickle.dump(out, f)
    print("done")
