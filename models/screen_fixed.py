"""Broker-wide screen with THREE defects of models/screen_broker.py corrected.

DEFECT 1 - ASK WAS ALIASED TO BID.   screen_broker.py:30 assigns every `*_a` column the
    corresponding bid column, so no fill in the 33-instrument headline ever crossed a
    spread.  Here the ask is built as bid + spread.

DEFECT 2 - THE SPREAD COLUMN IS MOSTLY ZERO, SO THE COST DEDUCTION WAS ZERO TOO.
    screen_broker.py:31 takes `d.spread.median()`.  Measured on the broker dump: EURUSD
    is 95.2% zeros (median 0), USDCHF 57.8% (median 0).  The headline therefore charges
    NOTHING on the majors.  Here the typical spread is the mean of the NON-ZERO
    observations, and a commission is added on top.

DEFECT 3 - window_min / max_hold WERE COUNTED IN BARS, NOT MINUTES.  ict_bt.run consumes
    them as row offsets into the index it is given.  screen_broker.py:45 hands it the
    M15 index, so the documented "6 hour" order life became 360 M15 bars = 90 hours and
    the "24 hour" time stop became 1440 bars = 15 days.  Zero of the 2,239 headline
    trades ever timed out.  Here they are 24 and 96 bars = the documented 6 h and 24 h.

Plus the short-side quote fix from fx_lab (a short fills on the BID, covers on the ASK).

COMMISSION is IC Markets Raw: USD 3.50 per lot per side, USD 7.00 round turn per 100k.
On a USD-quoted pair that is 0.7 pip.  Converted per instrument via the quote currency.
Indices are charged the measured spread only; IC Markets does not commission cash indices.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import fx_lab, ict_system, asia_locked as L, portfolio_locked as P

SRC = pathlib.Path(r"C:\Users\Vijayakumar R\AppData\Roaming\MetaQuotes"
                   r"\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files")

COMMISSION_RT_USD = 7.0          # per 1.0 lot round turn, IC Markets Raw
LOT = 100_000.0


def load(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d.t, format="%Y.%m.%d %H:%M:%S")
    d = d.set_index("t").sort_index()
    dec = max(len(str(x).split(".")[1]) if "." in str(x) else 0 for x in d.c.head(200))
    point = 10.0 ** (-dec)

    # typical spread = mean of the observations that are actually populated
    nz = d.spread[d.spread > 0]
    spread_pts = float(nz.mean()) if len(nz) else 0.0
    spread_px = spread_pts * point

    b = d.rename(columns={"o": "o_b", "h": "h_b", "l": "l_b", "c": "c_b"})[
        ["o_b", "h_b", "l_b", "c_b"]]
    # DEFECT 1 FIXED: a real ask, one spread above the bid
    for k in "ohlc":
        b[k + "_a"] = b[k + "_b"] + spread_px
    return b, spread_px, point


def commission_px(sym, last_px, point):
    """Round-turn commission expressed as a price distance, so it adds to the spread."""
    if sym in P.INDICES or sym in ("US500", "USTEC", "US30", "AUS200", "ES35",
                                   "STOXX50", "F40", "US2000", "UK100", "JP225", "HK50",
                                   "IT40"):
        return 0.0                                   # cash indices: spread only
    # USD/XXX quote -> $7 per 100k of BASE.  Convert to quote-price distance.
    if sym.endswith("USD"):
        return COMMISSION_RT_USD / LOT               # quote is USD
    if sym.startswith("USD"):
        return COMMISSION_RT_USD / LOT * last_px     # quote is the foreign ccy
    return COMMISSION_RT_USD / LOT * last_px         # cross: approximate via its own quote


def run_one(path, **over):
    sym = path.stem.replace("M15_", "")
    b, spread_px, point = load(path)
    if len(b) < 20000:
        return None
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
    atr = tr.rolling(14).mean().values
    ctx = ict_system.daily_context(b)
    asia = ict_system.session_pools(b)
    sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)

    kw = dict(L.EXECUTE)
    # DEFECT 3 FIXED: M15 bars, so 6 h = 24 bars and 24 h = 96 bars
    kw["window_min"] = 24
    kw["max_hold"] = 96
    # DEFECT 2 FIXED: real spread + commission, not a zero median
    kw["cost"] = spread_px + commission_px(sym, float(b.c_b.iloc[-1]), point)
    kw["stf_close"] = b.c_b.values
    kw.update(over)

    # UNITS: ict_bt computes net = rr - cost/Rp with Rp = R/pip, so `cost` and `pip` must
    # share units.  Passing pip=point (1e-5) while cost is a PRICE makes cost/Rp ~1e-7,
    # i.e. free trading.  screen_broker.py:45 passes pip=1.0 and a price cost, which is
    # dimensionally right; keep that.
    t = fx_lab.run_fixed(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
    if len(t) and L.SKIP_DOW:
        t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
    if not len(t):
        return None
    t = t.reset_index(drop=True)
    t["sym"] = sym
    return t


def screen(names=None, **over):
    files = sorted(SRC.glob("M15_*.csv"))
    if names:
        files = [f for f in files if f.stem.replace("M15_", "") in names]
    out = []
    for f in files:
        try:
            t = run_one(f, **over)
        except Exception as e:                      # noqa: BLE001
            print(f"  {f.stem}: {type(e).__name__} {e}")
            continue
        if t is not None:
            out.append(t)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def summarise(t, label):
    if not len(t):
        print(f"{label}: no trades")
        return
    d, v = fx_lab.split(t.sort_values("t"))
    def part(x):
        if not len(x):
            return "n=0"
        return (f"n={len(x):5} PF={fx_lab.pf(x.netR):5.3f} R={x.netR.sum():+8.1f} "
                f"WR={(x.netR > 0).mean()*100:4.1f}%")
    print(f"{label:26} DEV {part(d)}   |   VAL {part(v)}")


def per_symbol(t):
    rows = []
    for s, g in t.groupby("sym"):
        g = g.sort_values("t")
        d, v = fx_lab.split(g)
        yrs = max((g.t.max() - g.t.min()).days / 365.25, 0.01)
        rows.append(dict(sym=s, n=len(g), PF=fx_lab.pf(g.netR), totR=g.netR.sum(),
                         per_wk=len(g) / (yrs * 52),
                         PF_dev=fx_lab.pf(d.netR) if len(d) else np.nan,
                         PF_val=fx_lab.pf(v.netR) if len(v) else np.nan))
    return pd.DataFrame(rows).sort_values("totR", ascending=False)
