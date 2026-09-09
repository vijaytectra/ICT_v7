# ICT 2022 model — Asian-range raid. The best fully-causal result of this project.

Built after reading all three references end to end: the model pages, the concept families
behind each step, the eight annotated cases, and the common-mistake sections. Two things in
that read had never been implemented in any earlier version here, and both mattered.

## What the full read changed

**1. The pool.** `ict-2022-model.md` step 3 names the liquidity that gets raided:
*"liquidity sweep of a known pool — **Asian range, PDH/PDL, session high/low**"*. Every earlier
version in this project swept a 3-to-5-bar swing low — minor structure, inducement, not where
stops rest. Time-defined pools are a different object entirely.

Measured separately, fully causal, across 9 instruments:

| pool | n | PF | total R |
|---|---|---|---|
| **Asian range** | 471 | **1.19** | +68.9 |
| both pools | 672 | 1.02 | +11.1 |
| previous day high/low | 320 | 0.76 | −63.5 |

The Asian range carries it. PDH/PDL alone loses money.

**2. The target.** `targets-and-exits.md` and `draw-on-liquidity.md`: the exit is *"where the
next counterparty pool sits, not a fixed R multiple"*, and *"if rr_planned < min_rr the setup is
skipped even if every other box is checked"*. Replacing the fixed 2R with the actual draw on
liquidity plus a hard R:R gate is the single largest improvement found in this project.

**3. A cost/risk gate was mandatory.** brodenbeck v4 Screen 2: cost / structural risk ≤ 20 %.
Without it the population fills with degenerate setups whose FVG midpoint sits on the sweep low
— sub-pip stops, planned RR in the hundreds, a 2 % win rate and negative expectancy.

## The rules

**Structure and signals on M15. Execution on M1.** Bullish; bearish mirrors.

1. **Asian range** — the high and low of **02:00–09:00 EET**. Usable only **after 09:00**, when
   the session has closed. (Using it earlier is a look-ahead; it cost this project a false
   PF of 1.43.)
2. **Raid** — price trades **below the Asian low** (a long) having been above it on the prior bar.
   Record the raid low `SL_px`.
3. **Window** — the next step must occur within **40 M15 bars**, else reset.
4. **Displacement** — an M15 candle **closes above the swing high that was current at the raid**,
   with **body / (high − low) ≥ 0.5**.
5. **FVG** — the first 3-candle gap inside the raid-to-displacement leg.
6. **Entry** — limit at the FVG's **consequent encroachment**, its 50 % midpoint.
7. **Stop** — `SL_px`, the raid extreme.
8. **Target** — the **draw on liquidity**: the nearest unswept pool above (Asian high or previous
   day high). **Skip the trade if that target is closer than 2R.** Never move the target to fit.
9. **Cost gate** — skip if all-in cost exceeds **20 %** of the stop distance.
10. One position at a time, per instrument.

## Measured — 9 instruments, 2024-01 → 2026-09, cost charged on every trade

Costs assumed beyond the spread already in the fills: **0.8 pip** FX, **1.5 points** index.

| | |
|---|---|
| trades | 471 (14.7 / month across 9 instruments) |
| win rate | 28.7 % |
| average planned R:R | 3.68 |
| expectancy | +0.146 R |
| profit factor | **1.19** |
| total | +68.9 R |
| max drawdown | −21.7 R |
| longest losing streak | 14 |
| median stop | 12.5 units · median hold 40 min |
| in-sample → out-of-sample PF | 1.28 → **1.09** |
| bootstrap P(edge > 0) | 94.0 % |
| **95 % CI on expectancy** | **[−0.040, +0.335]** |

Per instrument: US30 1.41 · USATECH 1.31 · GBPUSD 1.25 · USDJPY 1.24 · USDCAD 1.07 ·
AUDUSD 1.01 · USA500 0.99 · EURUSD 0.96 · USDCHF 0.90. **Six of nine profitable.**

Robust to the two knobs that matter:

| cost multiple | 0× | 1× | 1.5× | 2× |
|---|---|---|---|---|
| PF | 1.34 | **1.19** | 1.10 | 1.17 |

| R:R gate | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 |
|---|---|---|---|---|---|
| PF | 1.11 | **1.19** | 1.19 | 1.13 | 1.18 |

## What does NOT help — measured, not assumed

| gate | source | PF with it |
|---|---|---|
| baseline | — | **1.19** |
| HTF daily bias required | *"No HTF bias, no pattern"* | 1.04 |
| trending-market profile required | ideal-swing-conditions | 1.00 |
| both | — | 0.92 |
| killzone window | 2022 model step 2 | 1.11 |
| short-term-low discriminator | ict-core-patterns | 1.05 |

Every doctrinal gate reduces performance on this data. The corpus insists the HTF condition
comes first; measured mechanically, it does not pay. That is worth knowing, and it is the
opposite of what the material claims.

## Honest verdict — read this before risking money

**This is the best fully-causal result in the project, and it is still not established.**

- **The confidence interval crosses zero**: [−0.040, +0.335]. P(edge > 0) is 94 %, so roughly a
  one-in-sixteen chance the whole thing is noise.
- **The profit is concentrated.** 2025 Q1 and Q2 contributed +71 R of the +68.9 R total. Strip
  those two quarters and the system is flat. Nine of eleven quarters are positive, but small.
- **It decays out of sample**: 1.28 → 1.09.
- Three of nine instruments lose money; two more are within noise of breakeven.
- Fourteen consecutive losses occurred inside 32 months.

471 trades at PF 1.19 is past the point where more backtesting settles anything. If you want to
know whether this is real, the next measurement is forward, not backward: run it on demo,
log every signal and the actual all-in cost per round trip, and let 100 live trades answer it.
