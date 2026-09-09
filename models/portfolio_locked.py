"""LOCKED PORTFOLIO - which instruments the Asian-range model is traded on.

Locked 2026-09-07.  The strategy itself is locked in `asia_locked.py`; this file locks only
the universe, because the universe turned out to matter more than any filter.

WHY THE LIST IS DEFINED BY ASSET CLASS AND NOT BY PAST PROFIT FACTOR
-------------------------------------------------------------------
Ranking instruments on past profit factor is noise.  Measured directly: choose instruments on
the FIRST half of each one's history and score the SECOND half, and the rule "keep PF > 1.15"
returns 1.701 while a RANDOM pick of the same size returns 1.701 on average and wins 50.4% of
the time.  The rank correlation between an instrument's first-half and second-half profit
factor is rho = +0.184, p = 0.25.  See BREADTH.md.

So the universe is an A-PRIORI class: the USD majors, the crosses among the eight major
currencies, and liquid index CFDs.  Nothing here was picked for scoring well.

WHAT IS EXCLUDED, AND ON WHAT GROUNDS
-------------------------------------
  pegged and exotic FX   EURDKK is pegged; the Scandi, Singapore, Turkish, Mexican, Polish,
                         Czech, Hungarian, Rand and CNH crosses carry real execution costs a
                         median-spread screen cannot see.  Structural, not performance-based.
  metals and energy      Different asset class, tested separately and failed: XAUUSD PF 0.812
                         with the halves at 1.495 then 0.314, XAGUSD 1.024, XTIUSD 0.807.
                         The instability, not the level, is the reason.
  crypto                 The model's premise is a raid of the ASIAN SESSION range.  A 24/7
                         instrument has no session structure for that to mean anything.
                         Measured anyway: BTCUSD 0.889, ETHUSD 0.697.

Every name still needs a tick-level Strategy Tester run before real money.  The screen behind
these numbers executes on M15 bars, which on USTEC flatters by about 3% (PF 1.294 against the
true 1-minute 1.253).
"""

MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]

CROSSES = ["EURJPY", "EURGBP", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
           "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
           "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
           "NZDJPY", "NZDCAD", "NZDCHF",
           "CADJPY", "CADCHF", "CHFJPY"]

INDICES = ["USTEC", "US30", "AUS200", "ES35", "STOXX50"]

UNIVERSE = MAJORS + CROSSES + INDICES

# risk per trade.  Peak concurrency measured at 4 positions and average well under one, so
# risk per trade does not compound into risk per moment - but the pooled drawdown is what
# sizes this, not the concurrency.  At 1% the measured -52R becomes a 52% account drawdown.
RISK_PCT = 0.25

EXCLUDED = dict(
    pegged_exotic=["EURDKK", "EURNOK", "EURPLN", "EURSEK", "EURSGD", "EURTRY", "EURZAR",
                   "EURHKD", "GBPDKK", "GBPNOK", "GBPSEK", "GBPSGD", "GBPTRY", "NOKJPY",
                   "NOKSEK", "SEKJPY", "SGDJPY", "AUDSGD", "CHFSGD", "USDCNH", "USDCZK",
                   "USDDKK", "USDHKD", "USDHUF", "USDMXN", "USDNOK", "USDPLN", "USDSEK",
                   "USDSGD", "USDTHB", "USDTRY", "USDZAR"],
    metals_energy=["XAUUSD", "XAGUSD", "XAUEUR", "XAGEUR", "XPTUSD", "XPDUSD",
                   "XTIUSD", "XNGUSD"],
    crypto=["BTCUSD", "ETHUSD"],
)
