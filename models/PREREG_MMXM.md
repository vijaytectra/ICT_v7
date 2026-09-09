# Pre-registration — Market Maker Buy / Sell Model (MMXM) + Market Maker Trap

Written BEFORE any number was produced. v1 postmortem mistake #1 was measuring first and
deciding the hypothesis afterwards; this file exists so that cannot happen again.

## The model, from the three references

Sources actually read for this build:

| source | file | what it contributed |
|---|---|---|
| brodenbeck | `models/ict/market_maker_models/market-maker-models.md` | the 4-phase MMXM curve: original consolidation → engineering (left side) → smart money reversal → redelivery (right side); "decompose: consolidation detection, leg counting, then SMR = sweep + MSS at/beyond a HTF array" |
| brodenbeck | `concepts/ict/market_structure/change_in_state_of_delivery/` | CISD: close through the high of the consecutive down-close candles of the manipulation leg; the same candle run defines the OB |
| brodenbeck | `concepts/ict/liquidity/internal_external_range_liquidity/` | ERL/IRL alternation inside a dealing range — "whichever type was taken last, the other is next" |
| OpenMobius | `concepts/market_maker_buy_model.json`, `market_maker_sell_model.json` | the operative definition: ERL sweep → into IRL (FVG) and respect it → CSD → expand IRL→ERL. Entry at LTF OB/FVG retest, stop below swept low, target HTF ERL |
| OpenMobius | cases `3OivsP1j_UE_case_003`, `IJcfC6wAPZU_case_002` | the nesting: HTF FVG is the POI, LTF sweep + CISD is the trigger, target = 2R / previous high |
| SrsBlack | `31-models/market-maker-trap.md` | the trap: HTF flow = D, retail trigger against D **is** the pool; measure liquidity off **bodies not wicks**; false breakout of consolidation in a bullish market = accumulation |
| SrsBlack | `12-power-of-three/power-of-three.md` | PO3/AMD is MMBM/MMSM: accumulation → manipulation → distribution |
| SrsBlack | `31-models/market-maker-manipulation-template.md` | target array must sit on a **lesser** timeframe than the entry array |
| SrsBlack | raw `MONTH-1-HOW-MARKET-MAKERS` | "it never goes consolidation → retracement or consolidation → reversal. It is always consolidation → expansion." |

## The setup being tested (bullish; bearish mirrors exactly)

Structure + signals on M15 (M5 arm also tested). Execution on M1 bid/ask.

1. **Dealing range** — last confirmed H4 swing high and swing low. Gives ERL high, ERL low,
   equilibrium.
2. **Phase A, accumulation** — the POI: an unfilled **bullish H4 FVG** (internal range
   liquidity) that price is now trading down into, in **discount** (below equilibrium).
3. **Phase B, manipulation** — inside/at the POI, price takes out a sell-side pool
   (prior confirmed M15 swing low, or relative equal lows). Record `SL_px`.
   The trap reading: this break is *against* HTF bias and is therefore accumulation,
   not a breakdown.
4. **Phase C, smart money reversal** — **CISD**: a bar closes above the highest high of
   the consecutive down-close candles that produced `SL_px`, within 40 bars.
5. **Entry** — limit at the mean threshold of that down-close run (the order block),
   valid 6 h, then cancel.
6. **Stop** — `SL_px`, the swept extreme.
7. **Phase D, distribution** — target: fixed 2R / 3R, or the ERL high (draw on liquidity).
8. **Killzone** — fill must land in the tested window.
9. One position at a time per instrument.

## Hypotheses, stated before measurement

- **H1** The MMXM as specified has PF > 1.0 out-of-sample on the US indices.
- **H2** CISD as the reversal trigger beats the MSS/displacement trigger the v7 Unicorn
  used (Unicorn OOS PF on indices = 1.25, n=5 arm; 1.18 for the corroborated n=3 arm).
- **H3** The HTF-FVG POI gate (ERL→IRL→ERL) adds edge over an ungated sweep.
- **H4** Measuring the swept pool off candle **bodies** beats measuring off wicks.
- **H5** It does not transfer to FX (prior: six FX majors, ~600 Unicorn configs, nothing).

## Protocol — fixed now, not negotiable later

- **Split.** IS = 2024-01-01 → 2025-06-30. OOS = 2025-07-01 → end. OOS is looked at once
  per frozen config.
- **Selection instrument.** US100 only. The winner is then applied **unchanged** to
  US500 and US30 (corroboration) and to the six FX majors (transfer test).
- **Grid.** 8 detector variants x 27 execution variants = 216 configs on US100 IS.
  Nothing outside this grid is added after seeing results.
- **Keep rule.** A config is kept only if, on US100: IS PF > 1.10 **and** OOS PF > 1.05,
  and, applied unchanged, ≥ 2 of 3 indices are PF > 1.0 over the full period.
- **Costs.** Real Dukascopy bid/ask spread is in every fill (long enters at ask, exits on
  bid). Extra commission/slippage sensitivity reported at 0 / 1 / 2 points.
- **Guards run before any number is believed.** (a) latched-state synthetic test,
  (b) per-quarter signal census on every instrument, (c) prefix-invariance causality test.
  Any guard failure invalidates the run — this is exactly the class of bug that made the
  v7 first pass wrong.
- **Both barriers inside one M1 bar counts as a loss.**

## What would make this a failure

PF ≤ 1.0 out-of-sample on the indices, or an IS→OOS decay worse than −0.15 PF, or fewer
than 150 index trades. Those get reported as a negative result, not re-searched.

---

# AMENDMENT — experiment 2, declared before it was run

Experiment 1 returned zero survivors.  Before accepting that as the verdict, two
implementation choices are corrected.  Both are justified by results this project
produced **before** the MMXM existed, so neither is a response to MMXM output:

1. `sweep_pool='asia'` — the Asian-range extreme, a time-defined pool, frozen at 09:00
   EET.  `ict-2022-model.md` step 3 names time-defined pools; measured here at PF 1.19
   across nine instruments against 0.76 for PDH/PDL.  Experiment 1 swept swing pivots,
   which is inducement.
2. `max_cost_frac=0.20` — brodenbeck v4 Screen 2, cost / structural risk.  Experiment 1
   had no floor, and its one apparent survivor showed the exact pathology the floor
   exists to remove.

Real cost is now charged on top of the spread: FX 0.8 pip, index 1.5 point.  This is
stricter than experiment 1.

Grid: 24 configs — pool {asia, swing} x entry {mt, edge} x target {2R, 3R, ERL}
x killzone {IDX, LDN}.  All 24 reported.  Keep rule unchanged.  Guards re-run first.
This is the last experiment; whatever it returns is the verdict.
