# ICT 2022 Asian-range model — full report

Every number below is recomputed from the raw trade lists in `reports/`, not copied from
a summary. Spec: [SETUP_FINAL.md](SETUP_FINAL.md). Code: `models/ict_system.py` +
`models/ict_bt.py`.

## The rules

Structure and signals on **M15**, execution on **M1**. Bullish; bearish mirrors.

1. **Asian range** — high and low of **02:00–09:00 EET**, usable only **after 09:00**.
2. **Raid** — price trades beyond the Asian bound, having been inside it on the prior bar.
   Record the raid extreme `SL_px`.
3. **Window** — 40 M15 bars, else reset.
4. **Displacement** — an M15 candle closes through the swing that was current at the raid,
   body / (high − low) ≥ 0.5.
5. **FVG** — first 3-candle gap inside the raid-to-displacement leg.
6. **Entry** — limit at the FVG's consequent encroachment (50 % midpoint).
7. **Stop** — `SL_px`.
8. **Target** — the draw on liquidity: nearest unswept pool (Asian high/low or PDH/PDL).
   **Skip if it is closer than 2R.** Never move the target to fit.
9. **Cost gate** — skip if all-in cost > 20 % of stop distance.
10. One position at a time, per instrument.

---

## 1. Headline — 9 instruments, 2024-01 → 2026-09, cost charged

Costs beyond the spread already inside the fills: **0.8 pip** FX, **1.5 points** index.
Source: `reports/asia_model_trades.csv` (471 rows).

| | |
|---|---|
| trades | **471** — 14.7/month across all nine |
| outcomes | 135 target / 333 stop / 3 timeout |
| win rate | **28.7 %** |
| average planned R:R | 3.68 |
| expectancy | **+0.146 R** |
| profit factor | **1.189** |
| total | **+68.9 R** |
| max drawdown | −21.7 R (R earned per R of drawdown: 3.17) |
| longest losing streak | **14** |
| median stop | 12.4 units · median hold 40 min |
| in-sample → out-of-sample | **1.306 → 1.050** (decay −0.257) |
| P(edge > 0) | **0.937** |
| 95 % CI on expectancy | **[−0.038, +0.338]** — crosses zero |

### Per instrument

| instrument | n | WR | E[R] | PF | total R | IS PF | OOS PF |
|---|---|---|---|---|---|---|---|
| US30 | 108 | 0.306 | +0.296 | **1.409** | +32.0 | 1.801 | 0.912 |
| US100 | 80 | 0.275 | +0.239 | **1.308** | +19.1 | 1.139 | 1.552 |
| GBPUSD | 54 | 0.259 | +0.204 | 1.253 | +11.0 | 1.527 | 0.993 |
| USDJPY | 45 | 0.267 | +0.185 | 1.236 | +8.3 | 1.422 | 0.952 |
| USDCAD | 46 | 0.283 | +0.054 | 1.067 | +2.5 | 1.594 | 0.676 |
| AUDUSD | 43 | 0.302 | +0.007 | 1.009 | +0.3 | 0.577 | 1.766 |
| US500 | 16 | 0.312 | −0.006 | 0.993 | −0.1 | 2.878 | 0.287 |
| EURUSD | 42 | 0.286 | −0.032 | 0.960 | −1.3 | 1.065 | 0.843 |
| USDCHF | 37 | 0.297 | −0.079 | 0.895 | −2.9 | 0.556 | 1.391 |

**Six of nine profitable.** US500 has only 16 trades — ignore its numbers.

### Quarterly

| quarter | n | total R | PF | cumulative |
|---|---|---|---|---|
| 2024 Q1 | 27 | −15.6 | 0.394 | −15.6 |
| 2024 Q2 | 41 | +1.9 | 1.055 | −13.7 |
| 2024 Q3 | 40 | +0.9 | 1.030 | −12.8 |
| 2024 Q4 | 42 | +2.4 | 1.076 | −10.4 |
| **2025 Q1** | 43 | **+31.4** | 2.201 | +21.0 |
| **2025 Q2** | 71 | **+39.7** | 1.797 | +60.7 |
| 2025 Q3 | 37 | +1.5 | 1.051 | +62.2 |
| 2025 Q4 | 53 | −12.7 | 0.731 | +49.5 |
| 2026 Q1 | 54 | +1.9 | 1.045 | +51.4 |
| 2026 Q2 | 35 | +11.8 | 1.468 | +63.2 |
| 2026 Q3 | 28 | +5.7 | 1.252 | +68.9 |

Nine of eleven quarters positive — but **2025 Q1 + Q2 alone are +71.1 R of the +68.9 R
total. Strip those two quarters and the system is −2.2 R.** Drop the 20 best trades and
PF falls to 0.864.

---

## 2. The pool comparison — what makes the model work

Source: `reports/ict2022_trades.csv`.

| pool raided | n | WR | PF | total R |
|---|---|---|---|---|
| **Asian range** | 429 | 0.291 | **1.197** | +64.9 |
| previous day high/low | 243 | 0.160 | **0.726** | −53.9 |
| both together | 672 | 0.244 | 1.021 | +11.1 |

The Asian range carries the whole result. PDH/PDL loses money and dilutes it. This is the
single largest lever found in the project — and it comes straight from `ict-2022-model.md`
step 3, which names time-defined pools rather than swing pivots.

---

## 3. The 2015–2023 holdout — nine years the model never saw

Source: `reports/holdout_2015_2023.csv` (483 rows, US30 / US500 / US100 only).

| | |
|---|---|
| period | 2015-01-06 → 2023-12-28 (**9.0 years**) |
| trades | 483 (4.5/month) |
| win rate | 26.1 % (126 tp / 351 stop / 6 eod) |
| expectancy | **+0.071 R** |
| profit factor | **1.090** |
| total | **+34.4 R** |
| max drawdown | −41.9 R |
| P(edge > 0) | **0.776** |
| 95 % CI | [−0.103, +0.257] — crosses zero |

| year | n | total R | PF |
|---|---|---|---|
| 2015 | 42 | +10.5 | 1.332 |
| 2016 | 42 | **−29.3** | 0.296 |
| 2017 | 19 | −4.6 | 0.741 |
| 2018 | 40 | +30.9 | 2.223 |
| 2019 | 59 | +7.8 | 1.170 |
| 2020 | 68 | −0.7 | 0.987 |
| 2021 | 50 | +7.3 | 1.193 |
| 2022 | 76 | +3.4 | 1.056 |
| 2023 | 87 | +9.2 | 1.136 |

Six of nine years positive. Per instrument: US100 1.290, US30 1.011, US500 0.766.

The holdout is **weaker than the 2024–2026 result but the same sign** — 1.09 against 1.19.
That is the honest read: the model is not a 2025 artefact, but it is not strong either.

---

## 4. The finding that actually replicates — shorts, not longs

Not stated in `SETUP_FINAL.md`, and it is the most robust thing in the whole dataset.

| period | side | n | WR | PF | total R | P(edge>0) | 95 % CI on E[R] |
|---|---|---|---|---|---|---|---|
| 2024–2026, 9 instruments | **SHORT** | 258 | 0.333 | **1.484** | **+90.3** | 0.997 | [+0.087, +0.619] |
| 2024–2026, 9 instruments | LONG | 213 | 0.230 | 0.879 | −21.4 | 0.220 | [−0.345, +0.158] |
| 2015–2023, 3 indices | **SHORT** | 276 | 0.275 | **1.213** | **+45.6** | 0.899 | [−0.083, +0.429] |
| 2015–2023, 3 indices | LONG | 207 | 0.242 | 0.933 | −11.2 | 0.337 | [−0.301, +0.210] |

**Pooled across both periods — 11.7 years of data:**

| | n | PF | E[R] | total R | P(edge>0) | 95 % CI |
|---|---|---|---|---|---|---|
| **SHORTS** | 534 | **1.340** | **+0.255** | **+135.9** | **0.998** | **[+0.071, +0.442]** |
| LONGS | 420 | 0.906 | −0.078 | −32.6 | 0.201 | [−0.258, +0.105] |

- The short-minus-long expectancy gap is **+0.332 R**; a 20,000-shuffle permutation test
  puts it at **p = 0.006**.
- Shorts hold out of sample within 2024–2026: **IS 1.563 → OOS 1.379**.
- Shorts are profitable on **8 of 9 instruments**: USDCHF 2.449 · GBPUSD 1.728 ·
  AUDUSD 1.669 · US30 1.589 · EURUSD 1.373 · US100 1.358 · USDCAD 1.331 · USDJPY 1.174 ·
  US500 0.878.
- The pooled shorts CI is the **only interval in this entire project that does not cross
  zero**.

**Caveats, stated plainly.** Side is a post-hoc split — it was not pre-registered. It is a
single binary split rather than a search over many cuts, and it replicates on nine
independent prior years, which is much stronger than an in-sample-only split. But the
2015–2023 shorts alone are *not* significant (CI [−0.083, +0.429]), the pooled CI clears
zero only barely, and pooling two periods treats them as independent when the instruments
overlap. Trading shorts only also halves the sample to about 8 signals/month.

---

## 5. Exit variants — all measured, baseline wins

Source: `reports/exit_variants.csv`.

| variant | n | PF | E[R] | total R | max DD | R/DD | TP % | IS → OOS |
|---|---|---|---|---|---|---|---|---|
| **A0 baseline (24 h fallback)** | 471 | **1.202** | +0.156 | **+73.6** | **−20.7** | **3.56** | 28.7 % | 1.295 → **1.093** |
| A target = IRL, EOD fallback | 472 | 1.206 | +0.147 | +69.5 | −28.5 | 2.44 | 24.4 % | 1.369 → 1.017 |
| B 50 % IRL / 50 % ERL | 472 | 1.193 | +0.138 | +65.0 | −34.6 | 1.88 | 10.6 % | 1.374 → 0.983 |
| C 50 % IRL + BE / 50 % ERL | 472 | 1.180 | +0.129 | +60.8 | −31.9 | 1.90 | 10.2 % | 1.342 → 0.993 |
| D 100 % ERL runner | 472 | 1.164 | +0.128 | +60.4 | −44.5 | 1.36 | 10.6 % | 1.340 → 0.953 |

Variant A has a marginally higher PF but 38 % more drawdown and a worse out-of-sample
number. The partial-take variants (B, C) reproduce the v1 lesson exactly: they raise
nothing and cost drawdown. **Keep the baseline.**

---

## 6. Robustness

| cost multiple | 0× | **1×** | 1.5× | 2× |
|---|---|---|---|---|
| PF | 1.34 | **1.19** | 1.10 | 1.17 |

| R:R gate | 1.5 | **2.0** | 2.5 | 3.0 | 4.0 |
|---|---|---|---|---|---|
| PF | 1.11 | **1.19** | 1.19 | 1.13 | 1.18 |

## 7. Every doctrinal gate reduces performance

| gate | source | PF with it |
|---|---|---|
| **baseline** | — | **1.19** |
| HTF daily bias required | "No HTF bias, no pattern" | 1.04 |
| trending-market profile | ideal-swing-conditions.md | 1.00 |
| both | — | 0.92 |
| killzone window | 2022 model step 2 | 1.11 |
| short-term-low discriminator | ict-core-patterns.md | 1.05 |

This replicates independently in the MMXM work ([SETUP_MMXM.md](SETUP_MMXM.md)): SMT
−0.034, contraction test −0.014, Judas window −0.020, HTF order flow −0.104. Two
separately built models, same conclusion — the corpus's confirmation stack does not pay.

---

## Verdict

**The best fully-causal result in this project, and still not established.**

- P(edge > 0) is 93.7 % on the main sample — roughly one chance in sixteen the whole thing
  is noise. The CI crosses zero.
- +71 R of the +68.9 R total comes from two quarters of 2025.
- It decays out of sample, 1.31 → 1.05.
- The nine-year holdout is positive but weaker (1.09) and its CI also crosses zero.
- Three of nine instruments lose money; two more are within noise of breakeven.
- Fourteen consecutive losses occurred inside 32 months.

**The one thing worth acting on:** the short side is where the edge lives, it replicates
across two independent periods separated by nine years, and it is the only result here
whose confidence interval excludes zero.

471 + 483 trades at PF ~1.1–1.2 is past the point where more backtesting decides anything.
The next measurement is forward: demo, log every signal and the real all-in cost per round
trip, shorts and longs tracked separately, 100 trades.

## Files

```
SETUP_FINAL.md                      the spec
models/ict_system.py                detector (gates, pools, causal Asian range)
models/ict_bt.py                    M1 bid/ask execution, DOL targeting, R:R gate
reports/asia_model_trades.csv       471 trades - the headline result
reports/ict2022_trades.csv          672 trades - both pools, for the pool comparison
reports/holdout_2015_2023.csv       483 trades - the nine-year holdout
reports/exit_variants.csv           five exit schemes measured head to head
```
