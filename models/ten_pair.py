"""If only 8-10 instruments can be traded, what is honestly expected?

The temptation is to hand over the ten best rows of the screen.  That is exactly the
mistake [[breadth-not-selection]] measured: first-half to second-half profit-factor rank
correlation is rho = +0.184, p = 0.25, and a random pick of the same size beats the
"best" pick 50.4% of the time.  Ranking on past profit factor is noise.

So the question is answered two ways:

  1  RANDOM SUBSETS.  Draw 10,000 random subsets of size k from the tradeable core and
     report the distribution of trades-per-week and profit factor.  That is the honest
     expectation for "pick any ten".
  2  THE TOP-K BY PAST PF.  Report it too, clearly labelled, so the size of the
     selection premium is visible rather than hidden.

The gap between the two is the amount of the "top ten" number that is not real.
"""
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")

pd.set_option("display.width", 210)
SCREEN = r"C:\personal\ICT_v7\reports\broker_screen.csv"
BOOKS = r"C:\personal\ICT_v7\reports\broker_books.pkl"

# excluded on structural grounds, exactly as PORTFOLIO.md defines the universe
DROP_SUB = ("HKD", "CNH", "DKK", "SGD", "SEK", "NOK", "TRY", "MXN", "ZAR", "PLN", "HUF")
METALS = ("XAU", "XAG", "XTI", "XPT", "XPD", "BTC", "ETH")


def tradeable(d):
    keep = []
    for s in d.sym:
        if any(x in s for x in METALS):
            continue
        if any(x in s for x in DROP_SUB):
            continue
        keep.append(s)
    return [s for s in keep]


def pf(v):
    v = np.asarray(v)
    g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.nan


if __name__ == "__main__":
    scr = pd.read_csv(SCREEN)
    with open(BOOKS, "rb") as fh:
        books = pickle.load(fh)
    core = tradeable(scr)
    scr = scr[scr.sym.isin(core)].copy()
    scr["per_wk"] = scr.n / (scr.yrs * 52.0)
    scr = scr.sort_values("per_wk", ascending=False)
    print(f"tradeable core after the structural exclusions: {len(scr)} instruments")
    print(f"pooled trades/week if all are run: {scr.per_wk.sum():.2f}\n")
    print("PER INSTRUMENT, sorted by TRADE RATE (not by profit factor)")
    print(scr[["sym", "n", "yrs", "per_wk", "WR", "PF", "PF_1st", "PF_2nd"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # pooled R series per instrument, for honest subset pooling
    ser = {}
    for s in scr.sym:
        b = books.get(s)
        if b is None or not len(b):
            continue
        ser[s] = np.asarray(b.netR.values if hasattr(b, "netR") else b)
    names = [s for s in scr.sym if s in ser]
    print(f"\nR-series available for {len(names)} of {len(scr)}")

    rng = np.random.default_rng(11)
    print("\n" + "=" * 104)
    print("RANDOM SUBSETS — the honest expectation for 'pick any k'")
    print("=" * 104)
    print(f"{'k':>4}{'trades/wk median':>19}{'PF median':>12}{'PF 10th pct':>14}"
          f"{'PF 90th pct':>14}{'P(PF<1.2)':>12}")
    for k in (5, 8, 10, 15, 20, len(names)):
        k = min(k, len(names))
        pfs, rates = [], []
        for _ in range(4000):
            pick = rng.choice(names, size=k, replace=False)
            v = np.concatenate([ser[s] for s in pick])
            pfs.append(pf(v))
            rates.append(float(scr.set_index("sym").loc[list(pick), "per_wk"].sum()))
        pfs = np.array(pfs); rates = np.array(rates)
        print(f"{k:>4}{np.median(rates):>19.2f}{np.nanmedian(pfs):>12.3f}"
              f"{np.nanpercentile(pfs,10):>14.3f}{np.nanpercentile(pfs,90):>14.3f}"
              f"{float(np.nanmean(pfs<1.2)):>12.3f}")

    print("\n" + "=" * 104)
    print("TOP-K BY PAST PF — the selection premium, shown so it is not mistaken for edge")
    print("=" * 104)
    byp = scr.sort_values("PF", ascending=False)
    for k in (5, 8, 10, 15):
        pick = list(byp.sym.head(k))
        pick = [s for s in pick if s in ser]
        v = np.concatenate([ser[s] for s in pick])
        rate = byp.set_index("sym").loc[pick, "per_wk"].sum()
        print(f"  top {k:>2}: {rate:5.2f} trades/wk   PF {pf(v):.3f}   "
              f"{'  '.join(pick[:8])}")
