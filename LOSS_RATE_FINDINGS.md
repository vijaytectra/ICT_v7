# Can the loss rate go from ~70% to 20-30%?

**Answer: the loss rate can be moved to roughly 28-37%. The system stops making money when
it gets there. Every route tested that lowers the loss rate also lowers the profit factor,
on both halves of the data, without exception.**

This file also records a **retraction**. An earlier version of this study reported that
"take 50% at +0.5R and move the stop to break-even" produced VAL profit factor 2.02 with
P(edge>0) = 99.1% on the three indices. That number was wrong. It is withdrawn.

---

## 1. The retraction

`run_ladder.py::apply_ladder` applied the break-even stop **only to trades that ended as
losers**. Losers were rescued from -1R to 0R; winners were left to run to their targets.

A stop moved to the entry does not work that way. It fires on **any** trade that returns
to the entry price, and a trade that later reaches its target usually returns to the entry
first. The old function rescued every loser and paid nothing for it. It manufactured the
entire result it was asked to test. This is the same class of error as the four already
found in `models/ict_bt.py` - a simulator that resolves an ambiguity in the strategy's
favour.

**The fix.** `fx_lab.run_fixed` now records, for each arming level `x`, whether price
returned to the entry after first printing +x R (`be_{x}`). Where the bar that first
printed +x R also traded back through the entry, intrabar order is unknowable at this
resolution and the pessimistic reading is taken: the stop fired.

**Consistency check.** A losing trade that reached +x R must have passed back through the
entry to reach its stop. Impossible rows found: **0 of 260**. The field is behaving.

## 2. Why the break-even stop fails here

It kills more winners than it saves losers, and it is not close.

| arm at | trades reaching it | of those, return to entry | winners killed |
|---|---|---|---|
| +0.25R | 66.1% | 90.4% | 47 |
| +0.50R | 62.6% | 83.5% | 40 |
| +0.75R | 57.5% | 67.0% | 25 |
| +1.00R | 52.3% | 58.2% | 20 |
| +1.50R | 45.4% | 43.0% | 13 |

*(three indices, n=174)*

**A trade that reaches +0.5R has an 83.5% chance of coming back to the entry before it
finishes.** This setup enters on a retracement into a fair value gap and targets a
liquidity pool. Price grinding back through the entry is the normal shape of the trade,
not the exception. A stop parked at the entry sits exactly where this setup breathes.

Corrected results, three indices, VAL half:

| policy | VAL loss rate | VAL PF | VAL R | P(edge>0) |
|---|---|---|---|---|
| locked exit, no partial | 68.6% | **1.510** | **+25.8** | 91.7% |
| 50% at +0.50R + break-even | 32.9% | 0.838 | -4.0 | 28.2% |
| 50% at +1.00R + break-even | 45.7% | 1.034 | +1.1 | 54.9% |
| 50% at +1.50R + break-even | 52.9% | 1.278 | +10.9 | 81.6% |

On all nine instruments the +0.5R version reaches VAL PF 0.646 with P(edge>0) = 4.6%. It
is not a weaker edge, it is a losing rule.

## 3. The ceiling is arithmetic, not tuning

No rule that acts at +x R can help a trade that never reaches +x R. So for any arming
level, the loss rate has a hard floor:

| arm at | floor on the loss rate (3 indices) | (all 9) |
|---|---|---|
| +0.25R | 33.9% | 32.7% |
| +0.50R | 37.4% | 38.8% |
| +0.75R | 42.5% | 44.6% |
| +1.00R | 47.7% | 50.0% |
| +1.50R | 54.6% | 55.8% |

To touch the floor you must book the **whole** position at +x R, which caps every winner
at x. The requested 20-30% band is below even the +0.25R floor. It is not reachable by any
exit rule on this trade population.

## 4. The full frontier, partial exits only

The partial-exit family needs no assumption about intrabar order: the remainder runs to
the stop or target already simulated. Three indices, VAL half:

| policy | VAL loss rate | VAL PF | VAL R |
|---|---|---|---|
| locked exit | 68.6% | **1.510** | **+25.8** |
| take 75% at +1.50R | 52.9% | 1.335 | +13.1 |
| take 75% at +1.00R | 45.7% | 1.243 | +8.2 |
| take 75% at +0.75R | 38.6% | 1.268 | +7.7 |
| take 75% at +0.50R | 32.9% | 1.168 | +4.1 |
| take 100% at +0.25R | 28.6% | 0.478 | -11.1 |

The relationship is monotone in both directions across every cell tested. The only policy
that reaches the requested band is the last one, and it loses money.

## 5. What this means

`PF = WR x payoff / (1 - WR)`. A low loss rate and a high profit factor are not two
independent goals that a better exit rule can satisfy at once. They trade against each
other along a curve fixed by how far this setup's trades actually travel, and that curve
is measured above, not assumed.

**The locked exit is the best exit found.** Nineteen management rules were rejected in
`LOSS_FORENSICS.md` on the old engine; re-asked on the corrected engine, the partial-exit
and break-even families are rejected as well. The 70% loss rate is what a 1:2+ target
costs. It is a property of the setup, not a defect in the exit.

## 6. Files

| file | what it does |
|---|---|
| `models/fx_lab.py` | engine; records `mfe_r`, `cost_r`, `be_{x}` |
| `models/run_ladder_honest.py` | the corrected study and the firing-rate table |
| `models/run_frontier.py` | the floor calculation and the full frontier |
| `models/run_ladder.py` | `apply_ladder` corrected in place |
