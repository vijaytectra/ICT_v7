# The draw-on-liquidity reachability gate

Found 2026-09-07 while mining nine ICT repositories. It is the first filter in this project
that improves profit factor, total R, win rate AND drawdown at the same time, on both
periods, and the first whose permutation test says it is genuinely selecting trades rather
than merely dropping them.

## The rule

One line. At the signal bar, take the draw-on-liquidity target the trade would use, and
count how many times price has CLOSED across that level in the previous 96 M15 bars
(24 hours). Take the trade only if the count is **2 or more**.

```python
st = max(0, i - 96)
side_of = close[st:i+1] > target
crossings = int(np.sum(side_of[1:] != side_of[:-1]))
if crossings < 2: skip
```

Everything it reads is knowable at the signal bar: the target comes from the previous day's
high/low or the closed Asian range, and the closes are all at or before the bar the detector
fires on. The entry is a limit placed after that bar closes.

## Mechanism, which is why it is believable

`crossings = 0` means price spent the whole of the last 24 hours on one side of the target.
The trade is being asked to travel to a level price has not reached in a day. `crossings >= 2`
means the target sits inside the range price has actually been trading in. The model's own
premise is that the algorithm is reaching for resting liquidity; if it has not been near that
liquidity all day, the premise is not in play.

This is the same idea two of the repositories reach for independently: islero's
liquidity-pool round-trip/"outdated pool" filter (`rules/liquidity_pool_reuse_rule.py:306-361`)
and OPKYEI's low-resistance vs high-resistance liquidity-run classifier
(`src/features/liquidity.py:312-400`). Both implementations peek forward; the idea does not
need to.

## Measured

Selection on DEV = the three US indices 2015-2023. VAL = all nine instruments 2024-2026,
read once. Costs are the spread-relative ones from the units fix, Monday skipped, locked
detector untouched.

| | trades | PF | total R | win rate | max DD |
|---|---|---|---|---|---|
| DEV, every trade | 603 | 1.233 | +107.4 | 27.4% | -43.4R |
| **DEV, crossings >= 2** | **384** | **1.576** | **+159.1** | **32.8%** | **-18.0R** |
| VAL, every trade | 532 | 1.367 | +141.2 | 28.6% | -18.0R |
| **VAL, crossings >= 2** | **370** | **1.712** | **+179.9** | **33.2%** | **-13.5R** |

Fewer trades and MORE total R, on both periods. Every previous filter in this project bought
profit factor by giving up total R.

## Why I believe it

**Permutation.** Keeping the same number of trades at random beats the filter's expectancy
with p = **0.0002** on DEV and p = **0.0000** on VAL. Every other filter tested in this
project scored p around 0.25 - they were dropping trades, not choosing them.

**Bootstrap.** DEV E[R] +0.414, 95% CI **[+0.186, +0.649]**. VAL E[R] +0.486, CI
**[+0.252, +0.726]**. P(edge>0) = 100.00% on both. No other result here has had a
confidence interval clear of zero on both halves.

**Not a proxy for anything already in the model.** Correlation with planned R:R -0.07/-0.10,
with stop size -0.06/-0.18, with hold time -0.26/-0.27. It works INSIDE every R:R band
(6 of 6 across both periods) and inside 7 of 8 stop-size quartiles.

**Per instrument.** 3 of 3 on DEV. 8 of 9 on VAL - only EURUSD goes the wrong way, and by
0.06 of profit factor.

**Per year on DEV.** The rejected bucket loses money in 7 of 9 years.

**Neighbourhoods are regions, not spikes.** Lookback 24 / 48 / 96 / 192 / 384 bars all give
DEV 1.35-1.58 and VAL 1.40-2.41. Threshold >=1 / 2 / 3 / 4 / 6 all give DEV 1.37-1.58 and
VAL 1.61-2.22. 96 bars and >=2 is the middle of a smooth surface, not a peak on a cliff.

**Walk-forward on DEV**, rule fixed, rolling 120-train / 40-test: filtered +142.2R with 10 of
12 windows positive, against +136.9R and 9 of 12 unfiltered.

## What it does NOT do

It does not get anywhere near a 70% win rate. 27.4% becomes 32.8%. A high win rate is only
available by banking partials early, and that was measured separately: 69% is reachable and
costs 92% of the profit.

## Open items before this goes into the locked config

1. Re-measure on the broker's own USTEC ticks in MT5, which is the only cost model that is
   not an assumption.
2. Port to `AsiaRangeRaid.mq5` - it needs 96 closed M15 bars and the target level, both of
   which the EA already has.
3. Re-run `tests/test_asia_locked.py` and re-pin, since every number there predates both this
   and the cost-units fix.
4. Measure the partial-exit ladder ON TOP of the filtered book. The path store does not carry
   the crossings field yet, so this has not been done.
