# The Unicorn works where ICT taught it — on the indices, not on FX

This is the corroboration test v4's own `KNOWN_LIMITATIONS.md` pre-registered and never ran:
a negative FX result cannot separate "no edge" from "does not transfer from index futures".
Run on Dukascopy index CFDs (US 100 Tech / US 500 / US 30 — the NQ / ES / YM proxies), the
answer is the second one.

## The setup

**Structure and signals on M15. Execution on M1.** Bullish; bearish mirrors exactly.

1. **Swing points** — a swing low needs **5 bars either side**, confirmed 5 bars later,
   unusable before that bar.
2. **Sweep** — price trades **below** the last confirmed swing low. Record the sweep low
   `SL_px`. No reclaim or wick test — both were measured and both hurt.
3. **Window** — the next step must occur within **60 M15 bars**, else the state resets.
4. **Displacement** — an M15 candle closes above the breaker body with
   **body / (high − low) ≥ 0.5**.
5. **Breaker** — the **bearish order block at the swing high**: the last consecutive run of
   **up-close** candles before the decline. Zone = **combined bodies**, wicks excluded.
   Not the down-close run at the sweep — that is a bullish *order block*, the confusion the
   sources warn about, and it cost this project several days.
6. **FVG** — a 3-candle gap from inside the sweep-to-displacement leg, overlapping the breaker.
7. **Entry** — limit at the breaker's **mean threshold**, the midpoint of the combined bodies.
   Valid 6 hours, then cancel. No chasing.
8. **Killzone** — the fill must land in **09:00–12:00 EET** (London) or **15:00–18:00 EET**
   (the index AM killzone, 08:30–11:00 New York). This is a different window from the forex
   killzone, and using the forex one was another of this project's errors.
9. **Stop** — `SL_px`, the swept extreme.
10. **Target** — **2R**.
11. One position at a time, per index.

## Measured — US100 / US500 / US30, 2024-01 → 2026-09, spread-only cost

| | swing n=5 | swing n=3 |
|---|---|---|
| trades | 413 (12.9/mo) | 582 (18.2/mo) |
| win rate | **35.6 %** | 34.5 % |
| breakeven win rate | 33.3 % | 33.3 % |
| expectancy | **+0.128 R** | +0.083 R |
| profit factor | **1.21** | 1.13 |
| total | **+52.8 R** | +48.3 R |
| in-sample PF | 1.18 | 1.10 |
| **out-of-sample PF** | **1.25** | **1.18** |
| decay | **+0.06** | +0.08 |
| max drawdown | −16.5 R | −18.5 R |
| longest losing streak | 9 | 10 |
| R per R of drawdown | 3.21 | 2.62 |
| median stop | 45 pt | 33 pt |
| median hold | 79 min | 64 min |
| bootstrap P(edge > 0) | 96.7 % | 92.4 % |

Out-of-sample is **better** than in-sample on both. Every index is positive:
US30 1.29 · US500 1.18 · US100 1.15 (n=5). Eight of eleven quarters positive.

## Why this is not a curve fit

Sixty configurations were scored on US100 alone; nine cleared both halves there. Applied
**unchanged** to US500 and US30, eight of those nine failed — including every one of the
top four. The single survivor had ranked fifth on US100. That is corroboration doing its job.

The parameter neighbourhood is a region, not a point. Nudging each knob one step:

| knob | variants | profitable |
|---|---|---|
| timeframe 10 / 20 / 30 min | 3 | 2 — 30 min fails at 0.91 |
| target 1.5R / 2.5R / 3R | 3 | 3 |
| entry zone-edge / CE | 2 | 2 |
| killzone NYAM / LDN / both / none | 4 | 4 |
| swing n=5, displacement 0.7, gap 30 | 3 | 3 |
| **total** | **17** | **16** |

On the six FX pairs everything sat between 0.80 and 0.92 with no region at all.

## The transfer result, stated plainly

| market | n | PF | IS → OOS |
|---|---|---|---|
| **US indices** | 413 | **1.21** | 1.18 → 1.25 |
| six FX majors, same config | 910 | **0.89** | 0.89 → 0.88 |

ICT taught the 2022 material on index futures and states in that same corpus that he was not
trading FX. Six FX majors and roughly 600 configurations found nothing. The corpus-native
market, tested once with a frozen spec, is profitable on all three instruments in both halves.
That is the "works where taught, does not transfer to FX" cell of v4's own interpretation table.

## Honest limits — read before risking anything

- **The cost margin is thin.** Breakeven sits at about **1.2 index points** of cost beyond the
  spread already in the fills: PF 1.13 at zero, 1.03 at 1 point, 0.94 at 2 points. Slippage on
  stop-outs is not modelled and eats this directly. Verify your broker's real all-in cost first.
- **The confidence interval on expectancy touches zero** at its lower edge: [−0.008, +0.269]
  for n=5. P(edge > 0) is 96.7 %, not 99 %.
- **413 trades is a moderate sample** across three highly correlated instruments — they are not
  three independent tests.
- `n=5` was found by exploring the neighbourhood *after* corroboration, so it carries a
  selection premium. The cleanly corroborated number is the `n=3` column: **PF 1.13**.
- Index CFDs are not the futures ICT taught on: different spread structure, no order book,
  synthetic overnight pricing.
- Nine consecutive losses occurred inside 32 months. At a 2R target that is the shape of it.

## Next step

Paper-trade it, and log the real all-in cost per round trip. That single number decides whether
a PF of 1.13–1.21 survives contact with a broker.
