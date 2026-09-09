"""Guards on the SIMULATOR itself, not on any result.

Added 2026-09-07 after auditing fifteen public ICT repositories. One of them
(GifariKemal/xaubot-ai) ran 39 experiments on gold and reached 82.4% win rate and profit
factor 2.51 - exactly the numbers this project is repeatedly asked for. The cause was a
single asymmetry in its simulator: the take profit was checked against the bar's high/low,
so an intrabar wick booked a full win, while the initial stop was never checked intrabar at
all and only triggered off a bar CLOSE at half notional. Wins on the wick, losses on the
close. The same codebase then traded live for one day: 42 trades, 42.9% win rate, -$97.78.

These tests make that specific failure impossible here.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import ict_bt

FAILS = []


def check(cond, msg):
    if not cond: FAILS.append(msg)


def frame(rows):
    """rows: (o,h,l,c) on the bid; the ask is the bid plus a fixed spread."""
    idx = pd.date_range("2024-01-02 10:00", periods=len(rows), freq="1min")
    d = pd.DataFrame(rows, columns=["o_b", "h_b", "l_b", "c_b"], index=idx)
    for k in "ohlc": d[k + "_a"] = d[k + "_b"] + 0.02
    return d


def one_signal(px, stop, tp_level):
    return [dict(bar=0, side=1, zone_lo=px - 0.01, zone_hi=px + 0.01, ce=px,
                 sweep_px=stop, sweep_bar=0, pool="asia", stl=np.nan,
                 pdh=tp_level, pdl=np.nan, ah=tp_level, al=np.nan, bias=0, gaps=[])]


def test_same_bar_goes_against_us():
    """A bar that touches BOTH the stop and the target must be scored a LOSS."""
    px, stop, tp = 100.0, 99.0, 102.0
    bars = [(100.5, 100.6, 100.4, 100.5),          # signal bar, no fill
            (100.5, 100.6, 99.90, 100.0),          # ask low 99.92 <= 100 -> FILLS here
            (100.0, 103.0, 98.00, 100.0),          # touches target AND stop
            (100.0, 100.0, 100.00, 100.0)]
    df = frame(bars)
    t = ict_bt.run(df, one_signal(px, stop, tp), df.index[:1], 1.0, pd.Timedelta("1min"),
                   min_rr=1.0, cri_max=0.0, cost=0.0, window_min=6, max_hold=6)
    check(len(t) == 1, "same-bar test produced no trade")
    if len(t):
        check(t.out.iloc[0] == -1,
              f"a bar touching both barriers was scored {t.out.iloc[0]}, must be -1 (loss)")


def test_stop_is_evaluated_on_the_wick_not_the_close():
    """A wick through the stop that closes back inside must still stop us out."""
    px, stop, tp = 100.0, 99.0, 102.0
    bars = [(100.5, 100.6, 100.4, 100.5),          # signal bar, no fill
            (100.5, 100.6, 99.90, 100.0),          # fills here
            (100.0, 100.5, 98.50, 100.4),          # wicks below the stop, closes above it
            (100.0, 103.0, 100.00, 103.0)]         # then runs to target
    df = frame(bars)
    t = ict_bt.run(df, one_signal(px, stop, tp), df.index[:1], 1.0, pd.Timedelta("1min"),
                   min_rr=1.0, cri_max=0.0, cost=0.0, window_min=6, max_hold=6)
    check(len(t) == 1, "wick test produced no trade")
    if len(t):
        check(t.out.iloc[0] == -1,
              "a wick through the stop that closed back inside was not counted as a stop-out")


def test_long_fills_on_the_ask_and_exits_on_the_bid():
    """The spread must be paid, in the right direction, on both sides."""
    px, stop, tp = 100.0, 99.0, 102.0
    # ask low never reaches 100.00 (bid low 99.99 -> ask low 100.01), so no fill
    bars = [(100.5, 100.6, 100.4, 100.5)] + [(100.0, 100.05, 99.99, 100.0)] * 3
    df = frame(bars)
    t = ict_bt.run(df, one_signal(px, stop, tp), df.index[:1], 1.0, pd.Timedelta("1min"),
                   min_rr=1.0, cri_max=0.0, cost=0.0, window_min=6, max_hold=6)
    check(len(t) == 0, "a long filled even though the ASK never reached the limit price")


if __name__ == "__main__":
    for fn in (test_same_bar_goes_against_us,
               test_stop_is_evaluated_on_the_wick_not_the_close,
               test_long_fills_on_the_ask_and_exits_on_the_bid):
        n = len(FAILS); fn()
        print(("PASS  " if len(FAILS) == n else "FAIL  ") + fn.__name__.replace("test_", "").replace("_", " "))
    for f in FAILS: print("   -", f)
    print("\n" + ("SIMULATOR GUARDS HOLD" if not FAILS else "SIMULATOR IS UNSOUND - %d failure(s)" % len(FAILS)))
