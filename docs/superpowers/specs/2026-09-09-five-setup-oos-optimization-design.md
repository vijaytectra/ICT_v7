# Five-Setup OOS Optimisation Design

**Purpose:** Evaluate the five existing ICT setups under one conservative, reproducible
protocol. The work may reject every setup; it must never manufacture a profitable result
by selecting on the final holdout.

## Scope

The candidates are existing executable definitions, not newly invented signals:

1. v5 Model 2022 (its own `model_2022.py` and backtest runner).
2. v5 Judas Swing.
3. v7 ICT 2022 Asian-range model (Arm A/B are result arms, not two setups).
4. v7 Unicorn indices. The FX Unicorn is explicitly retracted and is not optimised.
5. v7 MMXM. Stage-A/B FVG selection is an experiment inside the ICT 2022 model,
   not a sixth setup.

SMT divergence is explicitly out of scope at the user's direction.

## Data and execution model

- Use the nine local bid/ask M1 parquet series: EURUSD, GBPUSD, USDJPY, USDCHF,
  USDCAD, AUDUSD, USATECH, USA500, and USA30.
- Use 2015--2023 index history only where it exists; do not imply equivalent FX history.
- Long entry and short exit use ask; short entry and long exit use bid.
- Charge the observed bid/ask spread and a predeclared commission/slippage stress matrix.
- If one M1 candle crosses both stop and target, score the stop first. Limit fills require
  the executable side to trade through the limit.
- Label every result as **M1 bid/ask replay**, not tick-level. Existing USTEC MT5
  every-tick output is reported separately and is not generalized to other instruments.

## Data splits and selection

- Development: 2024-01-02 through 2024-12-31.
- Validation: 2025-01-01 through 2025-12-31.
- Final holdout: 2026-01-01 through 2026-09-04; it is opened once per chosen
  configuration only.
- Candidate parameters are chosen only by development plus validation stability. No
  parameter, instrument, or side is selected after inspecting the final holdout.

## Required measurements

For each setup and each parameter cell: number of trades, trades/week, win rate,
average win/loss, gross and net R, PF, expectancy, max drawdown, cost/R, and the same
metrics independently in development and validation.

The user target is recorded, not weakened: at least 1:2 initial RR, 8--16 trades/month
per setup, and net PF above 2.0. A setup is called a **target pass** only when all three
appear in validation and final holdout after costs. It is never called live-ready from
M1 testing alone.

## Promotion and rejection

- A candidate with net PF <= 1.0 in either development or validation is rejected.
- A candidate whose validation frequency is under 2 trades/week is rejected for the
  stated frequency objective.
- A candidate that needs a different target, stop, execution assumption, or instrument
  list after final-holdout inspection is rejected as selected-on-holdout.
- Any candidate failing the user's PF > 2.0 target is reported honestly as a target
  failure, even if its PF is positive.
- No new live-money rule is created. The only possible next state is a demo/forward
  candidate with signal, fill, spread, commission, and stop-slippage logging.

## Deliverables

1. Reproducible per-setup trade logs and an aggregate comparison table.
2. A cost-stress table, including the point at which PF falls below 1.0.
3. A concise verdict per setup: target pass, research-only, or reject.
4. A separate statement of what is and is not true tick evidence.
