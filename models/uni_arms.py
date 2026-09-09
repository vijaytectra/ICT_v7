"""Run one execution arm across the three indices and both periods."""
import pathlib, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models import unicorn_lab

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
CACHE = pathlib.Path(r"C:\personal\ICT_v7\reports\uni_cache.pkl")
IDX = ["USATECH", "USA500", "USA30"]
SUF = {"DEV": "_H", "VAL": ""}
_C = pickle.load(open(CACHE, "rb"))
_df = {}


def frame(per, sym):
    key = (per, sym)
    if key not in _df:
        _df[key] = pd.read_parquet(DATA / f"{sym}{SUF[per]}.parquet")
    return _df[key]


_bc = {}


def _bars_close(per, sym):
    """M15 closes for the reachability count.  MUST use the same resample the signal
    cache was built with, or `s["bar"]` indexes a different bar than it names."""
    k = (per, sym)
    if k not in _bc:
        from models.uni_prep import resample
        b, _ = resample(frame(per, sym))
        assert len(b) == len(_C[(per, sym)]["bars"]), "bar index mismatch"
        _bc[k] = b.c_b.values
    return _bc[k]


def arm(per, **kw):
    out = []
    for sym in IDX:
        c = _C[(per, sym)]
        kw2 = dict(kw)
        kw2.setdefault("stf_close", _bars_close(per, sym))
        t = unicorn_lab.run(frame(per, sym), c["sigs"], c["bars"], 1.0,
                            pd.Timedelta("15min"), ctx=c["ctx"], asia=c["asia"], **kw2)
        if len(t): out.append(t.assign(sym=sym))
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def show(label, kw, per_sym=False):
    row = {}
    for per in ("DEV", "VAL"):
        t = arm(per, **kw)
        s = unicorn_lab.stats(t, per)
        row[per] = (t, s)
    d, v = row["DEV"][1], row["VAL"][1]
    print("%-38s DEV n=%4d PF=%5.3f totR=%+7.1f WR=%4.1f%% | VAL n=%4d PF=%5.3f totR=%+6.1f WR=%4.1f%%" % (
        label, d["n"], d["PF"], d["totR"], 100 * d["wr"],
        v["n"], v["PF"], v["totR"], 100 * v["wr"]))
    if per_sym:
        for per in ("DEV", "VAL"):
            t = row[per][0]
            if not len(t): continue
            bits = []
            for sym, x in t.groupby("sym"):
                s = unicorn_lab.stats(x)
                bits.append("%s %d/%.2f" % (sym[3:], s["n"], s["PF"]))
            print("      %-4s %s" % (per, "  ".join(bits)))
    return row
