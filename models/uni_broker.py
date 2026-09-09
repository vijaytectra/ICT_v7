"""Run the Unicorn across the broker's whole instrument list.

Every Unicorn result in this project so far comes from three US index CFDs plus six FX
majors.  That is why its best arm fails validation: 141 DEV trades, 4 of 9 positive years,
and the whole profit sitting in six trades in 2023.  Breadth is what fixed the other model -
32 instruments, near-zero cross-correlation - and the Unicorn has never had it.

Same screen as `screen_broker.py`: broker M15 bars, M15 execution, cost = 0.4 x each
instrument's own median spread.  M15 execution flatters by roughly 3%, so this ranks rather
than proves.
"""
import pathlib, sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models.unicorn_v5 import detect
from models import unicorn_lab, ict_system
from models.uni_prep import CFG
from models.portfolio_locked import UNIVERSE, EXCLUDED

SRC = pathlib.Path(r"C:\Users\Vijayakumar R\AppData\Roaming\MetaQuotes"
                   r"\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files")
SPREAD_MULT = 0.4


def load(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d.t, format="%Y.%m.%d %H:%M:%S")
    d = d.set_index("t").sort_index()
    dec = max(len(str(x).split(".")[1]) if "." in str(x) else 0 for x in d.c.head(200))
    b = d.rename(columns={"o": "o_b", "h": "h_b", "l": "l_b", "c": "c_b"})[
        ["o_b", "h_b", "l_b", "c_b"]]
    for k, src in (("o", "o_b"), ("h", "h_b"), ("l", "l_b"), ("c", "c_b")):
        b[k + "_a"] = b[src]
    return b, float(d.spread.median()) * (10.0 ** (-dec))


def run_one(path, **kw):
    b, spread = load(path)
    if len(b) < 20000: return None
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    atr = tr.rolling(14).mean().values
    sigs = detect(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values, atr, **CFG)
    if not sigs: return None
    t = unicorn_lab.run(b, sigs, b.index, 1.0, pd.Timedelta("15min"),
                        ctx=ict_system.daily_context(b), asia=ict_system.session_pools(b),
                        cost=SPREAD_MULT * spread, stf_close=b.c_b.values, **kw)
    return t.reset_index(drop=True) if t is not None and len(t) else None


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    ARM = dict(target="asia+pdhl+range", kz="IDX", min_rr=2.0)   # the best arm so far
    keep = set(UNIVERSE) | {"AUS200", "ES35", "STOXX50"}
    books, rows = {}, []
    for p in sorted(SRC.glob("M15_*.csv")):
        sym = p.stem[4:]
        if sym not in keep: continue
        try:
            t = run_one(p, **ARM)
        except Exception as e:
            print("ERR", sym, e, flush=True); continue
        if t is None or len(t) < 12:
            print("thin", sym, 0 if t is None else len(t), flush=True); continue
        books[sym] = t
        half = len(t) // 2
        rows.append(dict(sym=sym, n=len(t), PF=pf(t.netR), totR=t.netR.sum(),
                         WR=100 * (t.netR > 0).mean(),
                         PF_1st=pf(t.netR[:half]), PF_2nd=pf(t.netR[half:]),
                         yrs=(t.t.max() - t.t.min()).days / 365.25))
        print("%-9s n=%3d PF=%.3f totR=%+6.1f" % (sym, len(t), pf(t.netR), t.netR.sum()), flush=True)
    pd.DataFrame(rows).sort_values("PF", ascending=False).to_csv(
        r"C:\personal\ICT_v7\reports\uni_broker_screen.csv", index=False)
    pd.to_pickle(books, r"C:\personal\ICT_v7\reports\uni_broker_books.pkl")
    print("done", len(rows))
