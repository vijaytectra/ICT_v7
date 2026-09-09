"""Screen every instrument the broker will actually let us trade.

More trades without lowering the quality bar is only available from more instruments -
the strategy's returns across instruments are close to uncorrelated (+0.06 to +0.09), so
each one that carries the edge adds almost its full square-root-of-N benefit.

Execution is on M15 bars rather than 1-minute, which is an approximation: on USTEC it
gives PF 1.294 where the true 1-minute figure is 1.253, so it flatters slightly. That is
fine for RANKING - the survivors then get a real tick-level test in the Strategy Tester.
"""
import pathlib, re, sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L, ict_bt, ict_system

SRC = pathlib.Path(r"C:\Users\Vijayakumar R\AppData\Roaming\MetaQuotes"
                   r"\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files")
SPREAD_MULT = 0.4


def load(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d.t, format="%Y.%m.%d %H:%M:%S")
    d = d.set_index("t").sort_index()
    # point size from the quoted precision, so spread (in points) becomes a price
    dec = max(len(str(x).split(".")[1]) if "." in str(x) else 0 for x in d.c.head(200))
    point = 10.0 ** (-dec)
    b = d.rename(columns={"o": "o_b", "h": "h_b", "l": "l_b", "c": "c_b"})[
        ["o_b", "h_b", "l_b", "c_b"]]
    for k in "ohlc": b[k + "_a"] = b[{"o": "o_b", "h": "h_b", "l": "l_b", "c": "c_b"}[k]]
    return b, float(d.spread.median()) * point


def run_one(path):
    b, spread = load(path)
    if len(b) < 20000: return None
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    atr = tr.rolling(14).mean().values
    ctx = ict_system.daily_context(b); asia = ict_system.session_pools(b)
    sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)
    kw = dict(L.EXECUTE)
    kw["cost"] = SPREAD_MULT * spread
    kw["stf_close"] = b.c_b.values
    t = ict_bt.run(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
    if len(t) and L.SKIP_DOW:
        t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
    return t.reset_index(drop=True) if len(t) else None


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    rows = []
    books = {}
    for p in sorted(SRC.glob("M15_*.csv")):
        sym = p.stem[4:]
        try:
            t = run_one(p)
        except Exception as e:
            print("ERR", sym, e, flush=True); continue
        if t is None or len(t) < 25:
            print("thin", sym, 0 if t is None else len(t), flush=True); continue
        books[sym] = t
        half = len(t) // 2
        rows.append(dict(sym=sym, n=len(t), PF=pf(t.netR), totR=t.netR.sum(),
                         WR=100 * (t.netR > 0).mean(),
                         PF_1st=pf(t.netR[:half]), PF_2nd=pf(t.netR[half:]),
                         yrs=(t.t.max() - t.t.min()).days / 365.25))
        print("%-8s n=%3d PF=%.3f totR=%+6.1f" % (sym, len(t), pf(t.netR), t.netR.sum()), flush=True)
    r = pd.DataFrame(rows).sort_values("PF", ascending=False)
    r.to_csv(r"C:\personal\ICT_v7\reports\broker_screen.csv", index=False)
    pd.to_pickle(books, r"C:\personal\ICT_v7\reports\broker_books.pkl")
    print("done", len(r))
