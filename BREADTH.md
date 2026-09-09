# The answer to "more trades" is breadth, not selection

2026-09-07. After the reachability gate, the obvious next question was how to raise the trade
count without lowering the quality bar. Two candidate answers: pick better instruments, or
trade more of them. They were tested against each other and only one survives.

## Instrument selection does not work

Forty-five instruments were dumped from the broker's own M15 history and run through the
locked rules. An in-sample screen looks superb - 28 of 45 clear PF 1.15 with both halves
positive, pooling to PF 1.672. **That number is worthless**, because the survivors were
chosen on the same data they are being scored on.

The honest test: choose instruments on the FIRST half of each one's own history, then measure
the pooled book on the SECOND half only.

| selection rule, applied to the 1st half | kept | 2nd-half PF |
|---|---|---|
| PF > 0.00 (i.e. take everything) | 41 | 1.700 |
| PF > 1.00 | 29 | 1.763 |
| PF > 1.15 | 25 | 1.701 |
| PF > 1.50 | 14 | 1.832 |

Selecting on PF > 1.15 gives a second-half PF of 1.701. **A random selection of the same
size gives 1.701 on average**, 95% range [1.545, 1.867], and beats the real selection 50.4%
of the time. The rank correlation between an instrument's first-half and second-half profit
factor is **rho = +0.184, p = 0.25** - the ranking does not carry.

So the "US30 + Nasdaq only" conclusion from earlier in this project, and the 28-survivor
screen above, are both artifacts. **Do not pick instruments on past profit factor.**

## Breadth does work

Taking everything, on the second halves only: n=1257, PF 1.700, +610R, max drawdown -22.0R.

Dropping the pegged and exotic crosses - EURDKK is literally pegged, and the Scandi and
Singapore crosses carry real execution costs this screen cannot see - leaves a **tradeable
core of 30 instruments**: 7 majors, 21 major crosses, and the two index CFDs in the dump.
That costs 18% of the gross profit and removes the part of it least likely to survive contact
with a real fill.

| tradeable core, 30 instruments | |
|---|---|
| trades | 2,067 over 5.8 years = **357 a year** |
| profit factor | 1.545 |
| total R | +800.3 |
| win rate | 29.8% |
| max drawdown | -42.9R |
| **out-of-sample halves only** | **n=991, PF 1.766, +523R, max DD -15.3R** |

Per year: 2022 -11.3R (PF 0.922), 2023 +132.7R, 2024 +227.8R, 2025 +248.6R, 2026 +197.9R.
One losing year out of five, and it is the year with the worst drawdown.

**Concurrency is the thing that makes this sizeable**: peak 4 positions open at once, average
well under one. The engine holds one position per instrument and they rarely overlap, so a
fixed risk per trade does not compound into a fixed risk per moment. Mean pairwise monthly
correlation across the book is **+0.025**.

## What this changes

Running one instrument gives 27 trades a year and a 73% chance of a profitable year. Running
the tradeable core gives 357 a year. The edge per trade is unchanged - it is the same rules -
but the number of independent bets is thirteen times higher, and that is the only lever in
this project that improves the odds of any given year without touching expectancy.

## What is not proven

- Execution here is on M15 bars, not 1-minute. On USTEC that flatters by about 3%
  (PF 1.294 against the true 1.253).
- Broker M15 history is 1.6 to 5.8 years depending on the instrument; most of it is 2022
  onwards. This is not a twelve-year test.
- The dump caught only AUS200, ES35 and STOXX50 - the US indices were not included and should
  be added.
- -42.9R of drawdown at 1% risk per trade is a 43% account drawdown. Position size has to come
  down as breadth goes up; the R-per-drawdown ratio is what improved, not the drawdown itself.
- Every instrument still needs a tick-level run in the Strategy Tester before it is traded.
