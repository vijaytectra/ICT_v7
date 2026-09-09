# Unicorn — consolidated mechanical spec

Sources: OpenMobius `knowledge_base/concepts/unicorn_model.json` · brodenbeck1
`concepts/ict/**` + `models/ict/unicorn` · SrsBlack `concepts/**`.
Every row is a rule taken verbatim from a source, plus how it is encoded here.

| # | Rule | Source wording | Encoding |
|---|---|---|---|
| R1 | Sweep is mandatory | "No sweep → not a breaker" (breaker-block) | `low < prior confirmed swing low` |
| R2 | MSS breaks the swing that originated the sweep leg | entry-sequence | swing high frozen **at sweep time** |
| R3 | Sweep→MSS window | "max_bars_sweep_to_mss e.g. 30 bars on 1-5m" | `max_gap` (30 / 60) |
| R4 | Displacement, candle level | "body >= 1.5-2.0 x ATR(14) and body/range >= 0.7" | `disp_atr`, `disp_ratio` |
| R5 | Displacement must leave an FVG | "most models require this form" | required |
| R6 | FVG must come from the SAME displacement | common mistake: "arbitrary FVG" | FVG scanned only inside the leg |
| R7 | Breaker = last down-closed candle **series** | KB: "whole sequence incl. wicks"; brodenbeck: "body of" | `breaker_body` flag (both tested) |
| R8 | Overlap must be non-empty | "adjacency does not count" | `intersect != empty` |
| R9 | Entry at zone edge **or** CE | KB gives both; CE-favoured for wide zones | `entry_mode` |
| R10 | Premium/discount gate | "never buy in premium, never sell in discount" | `pd_gate` 0.5 / 0.35 |
| R11 | OTE 62-79% of the leg | "FVG inside OTE is higher quality" | `ote_gate` |
| R12 | Killzone gates price | "same pattern outside the window is not the same trade" | LDN 09-12 EET, NY 14-17 EET |
| R13 | HTF bias must agree | SrsBlack criterion 3 | HTF close vs HTF EMA |
| R14 | SMT: trade the one that refused to confirm | smt-divergence | cross-pair sweep check |
| R15 | Stop: swept extreme / zone far edge / MSS origin | stop-placement, widest→tightest | `stop_mode` |
| R16 | **RR gate: min 2-3R; 2022 model uses 1:3. Below → skip** | targets-and-exits | `rr` 1 / 2 / 3 |

## Common mistakes encoded as guards
- entering before the full sequence completes → state machine, every step a gate
- displacement not confirmed → R4 is a hard filter, not a preference
- **stop at the far swing instead of tight to the zone** → R15 tested all three ways
- arbitrary FVG → R6
- breaker vs order block confusion → R7 tested both ways
- "3 of 4 is not a Unicorn" (SrsBlack) → all gates required simultaneously
