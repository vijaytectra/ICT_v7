# ICT_v7

A measured ICT / smart-money trading system for MT5, and the record of what did not work.

Fifteen months and seven rebuilds went into this. Most of the repository is negative results,
because most of what was tried failed, and the failures are the part that took the longest to
establish properly.

## What is actually traded

The **Asian-range raid model**. M15 structure, M1 execution.

1. Take the Asian session range, 02:00–09:00 EET, readable only once the session has closed.
2. Wait for a raid: the bar that FIRST breaks one of its extremes.
3. Require displacement — a candle closing through the last confirmed swing (5 bars either
   side), body / range ≥ 0.5.
4. Enter with a resting limit at the consequent encroachment (midpoint) of the first fair
   value gap in that leg. Stop at the swept extreme.
5. Target is dynamic: the nearest unswept previous-day high/low or Asian extreme, gated at a
   minimum 2.0 R:R. Never a fixed multiple, and the position is never resized to make the
   gate pass.
6. Skip Mondays. Skip a setup whose cost exceeds 20% of its structural risk.
7. **The draw-on-liquidity reachability gate**: the target must have been crossed, on a close,
   at least twice in the previous 96 M15 bars.

Frozen in `models/asia_locked.py` and `models/portfolio_locked.py`, pinned by
`tests/test_asia_locked.py` and `tests/test_portfolio_locked.py`. The EA is
`mt5/AsiaRangeRaid.mq5`; installation and the parameters not to touch are in
`mt5/SETUP_MT5.md`.

## What it measures

33 instruments — the USD majors, the crosses among the eight major currencies, and liquid
index CFDs. Broker M15 history, 2022–2026, cost charged at 0.4 × each instrument's own median
spread.

| | trades | profit factor | total R | win rate | max drawdown |
|---|---|---|---|---|---|
| whole period | 2,239 | 1.515 | +824.3 | 29.9% | −40.5R |
| first half | 586 | 1.155 | +68.0 | 26.8% | −40.5R |
| **out-of-sample half** | **1,653** | **1.651** | **+756.2** | **31.0%** | **−22.0R** |

7.4 trades a week. Expectancy +0.368R, 95% CI [+0.273, +0.465]. Sized at **0.25% of equity per
trade**, the measured drawdown is −10.1% of the account. At 1% it is −40%; do not use 1%.

The one instrument taken to tick level in the real MT5 Strategy Tester, USTEC 2022–2026:
79 trades, profit factor 1.545, drawdown −10.7R, all five years positive. That run is 22%
worse per trade than the M15 screen above, which is the honest cost of realistic fills.

## The three findings worth reading

**The reachability gate** (`DOL_REACHABILITY.md`) is the only filter out of roughly 110
tested that improved profit factor, total R, win rate and drawdown at the same time on both
halves. Its permutation test is p = 0.0002; every other filter scored around p = 0.25, meaning
they were dropping trades rather than choosing them.

**Breadth beats selection** (`BREADTH.md`). Ranking instruments on past profit factor is
noise: choose on the first half of each one's history and a random pick of the same size
scores the same on the second half and wins 50.4% of the time (rank correlation ρ = +0.184,
p = 0.25). The universe here is therefore defined by asset class, never by past performance.

**A high win rate with a high profit factor is not available** (`winrate-pf-frontier` notes in
`ASIA_PF_REVIEW.md`). 136 configurations, zero with a win rate ≥ 50% and profit factor ≥ 2 on
both halves. At 55% win rate the best profit factor is 1.05; the maximum anywhere is 1.73, at
a 20% win rate. The cause is measured, not argued: price reaches 1R before the stop 55% of the
time and 3R 35% of the time, so the population wants a large target and a low win rate.

## The negative results

- `UNICORN_CEILING.md` — the Unicorn model (breaker ∩ fair value gap) across 216+
  configurations. Its edge exists and is smaller than the cost of trading it.
- `SETUP_MMXM.md` — market-maker buy/sell models, no edge.
- `ASIA_PF_REVIEW.md` — every execution lever swept: break-even, target caps, soft exits,
  R:R gates, cost gates. None adds expectancy.
- `REFERENCES.md` — eighteen public ICT repositories audited and roughly 1.1 million words of
  transcript mined. One rule survived.

The most instructive failure is not ours. One audited repository reached an 82.4% win rate and
a 2.51 profit factor across 39 experiments on gold, from a single simulator asymmetry: take
profit checked against the bar's wick, stop never checked intrabar and triggered only on the
close at half size. The same code then traded live for one day — 42 trades, 42.9% win rate,
net −$97.78. `tests/test_sim_invariants.py` exists so that specific failure cannot happen
here, and it asserts that a bar touching both barriers is scored a loss.

## Running it

```bash
python tests/test_asia_locked.py        # pins the strategy
python tests/test_portfolio_locked.py   # pins the universe and its result
python tests/test_sim_invariants.py     # pins the simulator's honesty
python tests/test_invariants.py         # detector census and latched-state guards
```

Market data is not included and is re-derivable — see `REFERENCES.md`.

## Honest limits

One losing year in five (2022, −7.7R). The screen executes on M15 bars rather than 1-minute,
which flatters by about 3%. Only USTEC has had a tick-level run; every other instrument needs
one before real money. Fills at the fair-value-gap midpoint are assumed, and stop slippage is
not modelled outside the tick-level run — those are the two things a backtest cannot answer.

Not financial advice. The numbers above are what the code measures on historical data, which
is not the same thing as what an account will do.
