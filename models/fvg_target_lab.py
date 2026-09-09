"""STAGE A (FVG selection) and STAGE B (day-scoped target unswept).

Pre-registered in PREREG_FVG_TARGET.md before any variant number was read.  Nothing in
this file may be changed to chase a result; it exists to measure five frozen FVG
selection rules and one frozen target rule against the locked baseline.

Two things this file deliberately does NOT do:

  * It does not touch the detector.  Every variant re-picks from the `gaps` list that
    ict_system.detect already emits with age / mitigated / mit_ce / inverted metadata,
    so the SET of signals is identical across A0-A4 and only the chosen zone moves.
    (A2 FRESH is the one exception: when no gap is fresh the signal is dropped.)
  * It does not scan global history for "target already swept".  A pool like PDH is by
    definition touched the previous day, so `high[:signal_bar]` would reject nearly
    every trade and collapse the sample to nothing.  Swept-state is DAY-SCOPED, the
    same pattern mmxm4.pool_clock uses: reset at every new calendar day, and the Asian
    bounds monitored only from 09:00 EET, which is when the detector makes them
    knowable at all.

The execution path below re-implements ict_bt.run rather than calling it, because the
variant has to intervene between "signal" and "entry price".  That is a real risk of
silent divergence, so `control()` reproduces the pinned locked result exactly before any
variant is read.  If the control fails, nothing else here means anything.
"""
import sys

import numpy as np
import pandas as pd
from numba import njit

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_system

pd.set_option("display.width", 250)

VARIANTS = ["FIRST", "LARGEST", "FRESH", "NEAREST_MSS", "NEAREST_RAID"]
POOL_KEYS = ("ah", "al", "pdh", "pdl")
_span = {}


# --------------------------------------------------------------------- STAGE A pick
def pick_gap(s, v):
    """The five frozen selection rules.  A3/A4 are PRICE distance: bar distance would
    collapse NEAREST_RAID into FIRST, since gaps are emitted in bar order."""
    gs = s["gaps"]
    if v == "FIRST":
        return gs[0]
    if v == "LARGEST":
        return max(gs, key=lambda g: g["hi"] - g["lo"])
    if v == "FRESH":
        f = [g for g in gs if not g["mit_ce"] and not g["inverted"]]
        return f[0] if f else None
    ce = lambda g: (g["lo"] + g["hi"]) / 2.0
    if v == "NEAREST_MSS":
        r = s.get("ref", np.nan)
        return gs[0] if not np.isfinite(r) else min(gs, key=lambda g: abs(ce(g) - r))
    if v == "NEAREST_RAID":
        return min(gs, key=lambda g: abs(ce(g) - s["sweep_px"]))
    raise ValueError(v)


# --------------------------------------------------------------------- STAGE B clock
def swept_clock(bars, ctx, asia):
    """Per structure bar: has TODAY's price already taken each pool?

    Reset at every calendar day.  PDH/PDL are monitored from 00:00 because they are
    knowable from 00:00; the Asian bounds only from 09:00 EET, which is exactly when
    ict_system.detect stops returning NaN for them - so a finite ah/al always belongs
    to the same calendar date and no cross-day carry is possible.

    Bar i's own high/low count: the signal is decided at bar i's close and the order is
    placed at bar i+1, so bar i's extremes are knowable.  Both a WICK sweep and a CLOSE
    across are tracked; only the wick version is used as a filter in this
    pre-registration, the close version is logged for description.
    """
    idx = bars.index
    day = idx.normalize().values
    hour = idx.hour.values
    hi, lo, cl = bars.h_b.values, bars.l_b.values, bars.c_b.values
    C = ctx.reindex(idx.normalize())
    A = asia.reindex(idx.normalize())
    lv = dict(pdh=C.pdh.values, pdl=C.pdl.values, ah=A.ah.values, al=A.al.values)
    N = len(idx)
    w = {k: np.zeros(N, bool) for k in POOL_KEYS}
    xc = {k: np.zeros(N, bool) for k in POOL_KEYS}
    last = {k: np.full(N, -1, np.int64) for k in POOL_KEYS}
    f = {k: False for k in POOL_KEYS}
    fc = {k: False for k in POOL_KEYS}
    lb = {k: -1 for k in POOL_KEYS}
    cur = None
    for i in range(N):
        if day[i] != cur:
            cur = day[i]
            for k in POOL_KEYS:
                f[k] = fc[k] = False
                lb[k] = -1
        for k, up in (("pdh", True), ("pdl", False), ("ah", True), ("al", False)):
            if k in ("ah", "al") and hour[i] < ict_system.ASIA_EET[1]:
                continue
            v = lv[k][i]
            if not np.isfinite(v):
                continue
            if (hi[i] > v) if up else (lo[i] < v):
                if not f[k]:
                    lb[k] = i
                f[k] = True
            if (cl[i] > v) if up else (cl[i] < v):
                fc[k] = True
        for k in POOL_KEYS:
            w[k][i] = f[k]
            xc[k][i] = fc[k]
            last[k][i] = lb[k]
    return w, xc, last


# ------------------------------------------------------------------------ path walk
@njit(cache=True)
def walk(bl, bh, fill, px, stop, tp, side, max_hold):
    """One pass over the M1 bid path.  Returns the actual outcome, the exit bar, MAE and
    MFE in R over the trade's life, and - independently - the +2R-before--1R race."""
    R = abs(px - stop)
    tp2 = px + side * 2.0 * R
    end = min(fill + max_hold, bl.shape[0] - 1)
    out = 0
    b2 = -1
    mae = 0.0
    mfe = 0.0
    k = fill + 1
    while k <= end:
        if side == 1:
            up = (bh[k] - px) / R
            dn = (bl[k] - px) / R
            hit_stop = bl[k] <= stop
            hit_tp = bh[k] >= tp
            hit_2 = bh[k] >= tp2
        else:
            up = (px - bl[k]) / R
            dn = (px - bh[k]) / R
            hit_stop = bh[k] >= stop
            hit_tp = bl[k] <= tp
            hit_2 = bl[k] <= tp2
        if up > mfe:
            mfe = up
        if dn < mae:
            mae = dn
        if b2 == -1:
            if hit_stop:
                b2 = 0
            elif hit_2:
                b2 = 1
        if hit_stop:                       # stop first, the conservative convention
            out = -1
            break
        if hit_tp:
            out = 1
            break
        k += 1
    return out, k, mae, mfe, b2


# --------------------------------------------------------------------------- build
def build(sym, hist, variant="FIRST", unswept=False):
    suf = "_H" if hist else ""
    df = pd.read_parquet(L.DATA / f"{sym}{suf}.parquet")
    _span[(sym, hist)] = (df.index[0], df.index[-1])
    bars, atr = L.resample(df)
    ctx = ict_system.daily_context(df)
    asia = ict_system.session_pools(df)
    sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
    wk, xc, lastb = swept_clock(bars, ctx, asia)

    E = L.EXECUTE
    pip = L.UNIT[sym]
    cost = L.cost_for(sym, hist)
    stf = bars.c_b.values
    ai_l, ai_h = df.l_a.values, df.h_a.values
    bi_l, bi_h = df.l_b.values, df.h_b.values
    pos = df.index
    tf = pd.Timedelta(L.TF)
    busy = -1
    rows = []

    for s in sigs:
        i0 = pos.searchsorted(bars.index[s["bar"]] + tf, "left")
        if i0 >= len(pos) - 2 or i0 <= busy:
            continue
        side = s["side"]
        g = pick_gap(s, variant)
        if g is None:
            continue
        px = (g["lo"] + g["hi"]) / 2.0
        stop = s["sweep_px"]
        R = (px - stop) * side
        if R <= 0:
            continue
        Rp = R / pip
        if cost / Rp > E["cri_max"]:
            continue

        b = s["bar"]
        pool, dropped = [], 0
        for key in ("pdh", "ah") if side == 1 else ("pdl", "al"):
            v = s.get(key)
            if v is None or not np.isfinite(v):
                continue
            if not ((v > px) if side == 1 else (v < px)):
                continue
            if unswept and wk[key][b]:
                dropped += 1
                continue
            pool.append(v)
        if not pool:
            continue
        tp = min(pool) if side == 1 else max(pool)

        j0 = max(0, b - E["x_lookback"])
        sd = stf[j0:b + 1] > tp
        if int(np.sum(sd[1:] != sd[:-1])) < E["min_target_x"]:
            continue
        rr = side * (tp - px) / R
        if rr < E["min_rr"] or (E["max_rr"] and rr > E["max_rr"]):
            continue

        end = min(i0 + E["window_min"], len(pos) - 1)
        fill = -1
        for j in range(i0, end):
            if (side == 1 and ai_l[j] <= px) or (side == -1 and ai_h[j] >= px):
                fill = j
                break
        if fill < 0:
            continue

        out, kb, mae, mfe, b2 = walk(bi_l, bi_h, fill, px, stop, tp, side,
                                     E["max_hold"])
        busy = kb
        net = (rr - cost / Rp) if out == 1 else (
            -(1 + cost / Rp) if out == -1 else -cost / Rp)
        if side == 1:
            tk = "ah" if (s.get("ah") is not None and tp == s.get("ah")) else "pdh"
        else:
            tk = "al" if (s.get("al") is not None and tp == s.get("al")) else "pdl"
        rows.append(dict(
            sym=sym, t=pos[fill], side=side, R_pips=Rp, rr=rr, out=out, netR=net,
            bars=kb - fill, b2=b2, mae=mae, mfe=mfe,
            n_gaps=len(s["gaps"]), sel_age=g["age"], sel_mit=int(g["mitigated"]),
            sel_mitce=int(g["mit_ce"]), sel_inv=int(g["inverted"]),
            tgt=tk, tgt_wick=int(wk[tk][b]), tgt_close=int(xc[tk][b]),
            tgt_sweep_age=(b - lastb[tk][b]) if lastb[tk][b] >= 0 else -1,
            pool_dropped=dropped))

    t = pd.DataFrame(rows)
    if len(t) and L.SKIP_DOW:
        t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)].reset_index(drop=True)
    return t


def run(syms, hist, variant="FIRST", unswept=False):
    out = [build(s, hist, variant, unswept) for s in syms]
    out = [x for x in out if len(x)]
    return (pd.concat(out).sort_values("t").reset_index(drop=True) if out
            else pd.DataFrame())


# --------------------------------------------------------------------------- stats
def span(sym, hist):
    """Data span, needed for trades/week.  Computed here rather than only inside
    build() so that a cached trade file can still be summarised."""
    if (sym, hist) not in _span:
        d = pd.read_parquet(L.DATA / f"{sym}{'_H' if hist else ''}.parquet",
                            columns=["c_b"])
        _span[(sym, hist)] = (d.index[0], d.index[-1])
    return _span[(sym, hist)]


def metrics(t, syms, hist):
    if t is None or len(t) == 0:
        return None
    lo = min(span(s, hist)[0] for s in syms)
    hi = max(span(s, hist)[1] for s in syms)
    wks = max((hi - lo).total_seconds() / (7 * 86400.0), 1.0)
    v = t.netR.values
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    res = t[t.b2 >= 0]
    w = v[v > 0]
    l = v[v < 0]
    return dict(N=len(t), per_wk=len(t) / wks,
                WR=100.0 * float((t.out == 1).mean()),
                p2R=100.0 * float(res.b2.mean()) if len(res) else np.nan,
                n2=len(res),
                PF=(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.nan,
                ER=float(v.mean()),
                avgW=float(w.mean()) if len(w) else np.nan,
                avgL=float(l.mean()) if len(l) else np.nan,
                MAE=float(t.mae.median()), MFE=float(t.mfe.median()), maxDD=dd)


SLICES = [("DEV", L.INDICES, True), ("VAL-IDX", L.INDICES, False),
          ("VAL-FX", L.FX, False), ("VAL", L.ALL, False)]


def control():
    """The lab must reproduce the pinned locked result before any variant is read."""
    t = run(L.ALL, False, "FIRST", False)
    got_pf = L.pf(t.netR.values)
    ok = len(t) == 268 and abs(got_pf - 1.538895) < 1e-4
    print(f"HARNESS CONTROL   n={len(t)} (pinned 268)   "
          f"PF={got_pf:.6f} (pinned 1.538895)   "
          f"{'PASS' if ok else 'FAIL'}")
    return ok
