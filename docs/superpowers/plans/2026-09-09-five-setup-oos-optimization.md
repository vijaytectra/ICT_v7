# Five-Setup OOS Optimisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce conservative, reproducible OOS verdicts for v5 Model 2022, v5 Judas Swing, v7 ICT 2022 Asian-range, v7 Unicorn indices, and v7 MMXM without selecting on the final holdout.

**Architecture:** A new analysis-only runner consumes existing setup functions and their local parquet data, writes all output below a new dated report directory, and never edits existing locked reports. It evaluates predefined parameter grids over development and validation, freezes one candidate per family, then opens the 2026 holdout exactly once.

**Tech Stack:** Python 3.14, pandas, numpy, existing `models/asia_locked.py`, `models/unicorn_v5.py`, `models/mmxm*.py`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-five-setup-oos-optimization-design.md`

## Global Constraints

- Use only local bid/ask M1 parquet data and label output M1 bid/ask replay.
- Never call an M1 result tick-level.
- Apply executable bid/ask sides and stop-first treatment for same-bar barrier ambiguity.
- Split 2024 development, 2025 validation, and 2026 final holdout; no holdout selection.
- Preserve all existing strategy source files and existing report files.
- A target pass requires net PF > 2.0, at least 1:2 initial RR, and 2--4 trades/week in validation and holdout.

---

### Task 1: Lock baseline reproducibility before optimisation

**Files:**
- Create: `reports/oos_optimisation_2026-09-09/baseline_manifest.json`
- Test: `tests/test_asia_locked.py`, `tests/test_invariants.py`, `tests/test_mmxm_invariants.py`, `tests/test_sim_invariants.py`

**Interfaces:**
- Consumes: existing locked data loaders and tests.
- Produces: exit-code evidence and a manifest recording data coverage and test timestamp.

- [ ] **Step 1: Run the existing invariant tests**

Run: `python -m pytest tests/test_asia_locked.py tests/test_invariants.py tests/test_mmxm_invariants.py tests/test_sim_invariants.py -q`

Expected: exit 0; any failure stops optimisation.

- [ ] **Step 2: Record local data coverage**

Write a JSON manifest listing each parquet file's row count, first timestamp, last timestamp, and columns.

- [ ] **Step 3: Confirm the manifest is complete**

Run: `python -c "import json; d=json.load(open('reports/oos_optimisation_2026-09-09/baseline_manifest.json')); assert len(d['datasets']) >= 9"`

Expected: exit 0.

### Task 2: Build an analysis-only conservative evaluator

**Files:**
- Create: `models/oos_optimisation.py`
- Create: `tests/test_oos_optimisation.py`

**Interfaces:**
- Consumes: `pandas.DataFrame` with `o_b,h_b,l_b,c_b,o_a,h_a,l_a,c_a` columns and candidate trade signals.
- Produces: `evaluate_trade_path(frame, side, entry, stop, target, expiry) -> dict` and `summarize(trades) -> dict`.

- [ ] **Step 1: Write failing execution tests**

Add tests that assert a long limit fills only on ask, a long exit uses bid, and a M1 candle touching both barriers returns `stop`.

- [ ] **Step 2: Run the new test file**

Run: `python -m pytest tests/test_oos_optimisation.py -q`

Expected: FAIL because `models.oos_optimisation` does not exist.

- [ ] **Step 3: Implement the minimal evaluator**

Implement `evaluate_trade_path` with only executable-side fills, first touch, stop-first ambiguity, expiry, and net-R cost deduction. Implement `summarize` with count, weekly frequency, win rate, PF, expectancy, and max drawdown.

- [ ] **Step 4: Run evaluator tests**

Run: `python -m pytest tests/test_oos_optimisation.py -q`

Expected: exit 0.

### Task 3: Run frozen grids and choose without final holdout

**Files:**
- Modify: `models/oos_optimisation.py`
- Create: `reports/oos_optimisation_2026-09-09/dev_validation.csv`
- Create: `reports/oos_optimisation_2026-09-09/frozen_candidates.json`

**Interfaces:**
- Consumes: existing family signal generators and Task 2 evaluator.
- Produces: one frozen candidate per family, selected from development/validation only.

- [ ] **Step 1: Write a failing split-integrity test**

Assert that candidate selection receives no timestamp after `2025-12-31 23:59:59` and raises `ValueError` if holdout rows are passed to the selector.

- [ ] **Step 2: Run the split-integrity test**

Run: `python -m pytest tests/test_oos_optimisation.py -q`

Expected: FAIL because no split guard exists.

- [ ] **Step 3: Implement fixed, documented grids**

Use only already documented axes: v5 Model 2022 YAML configurations, Judas exit policies,
v7 ICT 2022 FVG A0--A4 without counting arms as new setups, Unicorn target 2R/3R/4R,
and MMXM pre-registered families. Do not add data-mined rules. SMT is excluded.

- [ ] **Step 4: Freeze one candidate per family**

Select only candidates with both development and validation PF > 1.0, validation frequency >= 2/week, and no worse than 20% PF decay from development. Persist the selection rationale and rejected alternatives.

- [ ] **Step 5: Run tests and write development/validation output**

Run: `python -m pytest tests/test_oos_optimisation.py -q; python models/oos_optimisation.py --stage select --out reports/oos_optimisation_2026-09-09`

Expected: exit 0 and both artifacts exist.

### Task 4: Open the 2026 holdout once and report honestly

**Files:**
- Modify: `models/oos_optimisation.py`
- Create: `reports/oos_optimisation_2026-09-09/holdout.csv`
- Create: `reports/oos_optimisation_2026-09-09/verdict.md`

**Interfaces:**
- Consumes: frozen candidates JSON only; the holdout dataset is inaccessible to selection code.
- Produces: immutable comparison rows and one `target pass`, `research-only`, or `reject` verdict per family.

- [ ] **Step 1: Write a failing no-reselection test**

Assert that `--stage holdout` fails if `frozen_candidates.json` is absent and that it cannot call the selection function.

- [ ] **Step 2: Run the no-reselection test**

Run: `python -m pytest tests/test_oos_optimisation.py -q`

Expected: FAIL because holdout guard is missing.

- [ ] **Step 3: Implement holdout-only evaluation and verdict logic**

Report target pass only if validation and holdout both meet all three user targets after costs; otherwise report the exact failed condition.

- [ ] **Step 4: Run holdout once and verify artifacts**

Run: `python models/oos_optimisation.py --stage holdout --out reports/oos_optimisation_2026-09-09; python -m pytest tests/test_oos_optimisation.py tests/test_asia_locked.py tests/test_invariants.py tests/test_mmxm_invariants.py tests/test_sim_invariants.py -q`

Expected: exit 0; `verdict.md` names all five families and labels all evidence M1 bid/ask replay.
