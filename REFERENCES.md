# Reference material this project was built against

None of it is redistributed here. Clone it yourself if you want to follow the audit trail;
the findings that came out of each one are recorded in the documents listed at the end.

## The three original sources

```
git clone https://github.com/MobiusQuant/OpenMobius-skill      OpenMobius-skill
git clone https://github.com/brodenbeck1/ict_trading           ref_brodenbeck
git clone https://github.com/SrsBlack/ict-knowledge-library    ref_srsblack
```

## The fifteen repositories audited afterwards

```
cd ref_new
git clone --depth 1 https://github.com/silotabs/ict-trading-bot                 silotabs_ict-trading-bot
git clone --depth 1 https://github.com/GdotAiM/ICT-Options-Agent                GdotAiM_ICT-Options-Agent
git clone --depth 1 https://github.com/islero/ICT-NT                            islero_ICT-NT
git clone --depth 1 https://github.com/fallenpheonix23/ict-trading-bot          fallenpheonix23_ict-trading-bot
git clone --depth 1 https://github.com/OPKYEI/ICT-Trading                       OPKYEI_ICT-Trading
git clone --depth 1 https://github.com/sixscripts-ai/train-ict                  sixscripts-ai_train-ict
git clone --depth 1 https://github.com/futureteck/ICT_Automated_Trading_System  futureteck_ICT_Automated_Trading_System
git clone --depth 1 https://github.com/dextergsm/ict-trading                    dextergsm_ict-trading
git clone --depth 1 https://github.com/zakariab0/ozo                            zakariab0_ozo
git clone --depth 1 https://github.com/rcook0/SMC-ICT                           rcook0_SMC-ICT
git clone --depth 1 https://github.com/GifariKemal/xaubot-ai                    GifariKemal_xaubot-ai
git clone --depth 1 https://github.com/SiyabongaDlamini/SmartMoney.MQ5          SiyabongaDlamini_SmartMoney.MQ5
git clone --depth 1 https://github.com/Musyimi97/phase404                       Musyimi97_phase404
git clone --depth 1 https://github.com/Aditya18487/mt5-trading-bot              Aditya18487_mt5-trading-bot
git clone --depth 1 https://github.com/lordgaruda/XAU-60                        lordgaruda_XAU-60
git clone --depth 1 https://github.com/MoAbdullahi/ICT_Strategy_Video_Extraction MoAbdullahi_ICT_Strategy_Video_Extraction
```

## What came out of them

One rule survived testing, out of everything in all eighteen repositories and roughly 1.1
million words of transcript: the draw-on-liquidity reachability gate in
`DOL_REACHABILITY.md`. Everything else measured is written up in `UNICORN_CEILING.md`,
`ASIA_PF_REVIEW.md` and `BREADTH.md`.

The most useful negative result is in `high-winrate-is-a-simulator-bug` (see the notes in
those documents): one repository reached an 82.4% win rate and a 2.51 profit factor from a
single simulator asymmetry - take profit checked on the bar's wick, stop checked only on the
close and at half size - and then lost money on its first live day. `tests/test_sim_invariants.py`
exists so that specific failure cannot happen here.

## Data

Not included. `engine/load.py` rebuilds the Dukascopy parquets from 1-minute bid/ask CSV
exports; `models/screen_broker.py` re-dumps the broker's M15 bars from a running MT5 terminal
via `mt5/DumpManyEA.mq5`.
