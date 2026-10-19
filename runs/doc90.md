# 90 — AuclairsDad from his own blueprint: the compression–expansion stack (19 Oct 2026, in progress)

DK, 19 Oct 14:01: *"We're doing the thing again mate. You give up or write off ideas with potential when you hit barriers. Use your creative mind to think — 'if I was doing this, how would I make it work?' Not just death by testing."* Then he sent AuclairsDad's own 17-post thread on how the algo is built, plus follow-ups. This doc records what changed and what the first build shows. Finding 157 stays OPEN; this is its first constructive pass.

## What his thread says (and what I had wrong)
- **Thesis: markets store energy in compression and release it in expansion.** Not "delta → go with it" (docs 84, 86, 88 tested that; it is random) and not levels.
- **Layers, each a gate:** REGIME (trend as a *tested hypothesis*: regress price over N higher-timeframe clock buckets — slope t-stat, R², variance ratio — with hysteresis) → SETUP score 0–100 (compression: bar-time behaviour, order-flow flattening, range stability, channel tightness, activity decay) → TRIGGER score 0–100 (activity surge, one-sided flow, range expansion, close location) + directional agreement (flow, candle, structure) → GOVERNORS (daily loss cap, profit target, max trades, cooloff, blackouts, forced flat) → EXITS (hard stop floor → breakeven ratchet → trail).
- **Multi-path entries OR'd through the same gates:** clean breakout, raw-conviction continuation, divergence; he has since added a mean-reversion component.
- **Fully automated, zero discretion, no ML; "the code goes with flow".** He finds level-based systems (volume profile, pivots, OR, fibs) regime-inconsistent and says pure flow wins — which is our own record too (doc 37: only the prior-day low ever held). The "levels" component in doc 84 was my invention and is dropped.
- His own description of his P&L: "not great, not bad… low drawdown and steady growth so it can scale with more lots"; still tuning the minimum delta for entry on 2.5 years of Sierra data. His older /CL room algo's edge was **scaling in at −12 and −17 pips before a −26 stop, with one +32 target for all lots**, on both sides.

## The build (`src/flow_nq4.py`, NQ 1-minute from Dukascopy ticks; activity = tick count, flow = tick-rule delta; closed bars only, HTF on completed 15-min buckets)
Setup = mean of five rolling-percentile components over a 30-min window (range stability, channel tightness/ATR, activity decay, |Σdelta|/Σ|delta| flattening, share of dead minutes). Trigger = activity, one-sided share and range percentiles vs the last 4h, plus close location. Regime = 16 × 15-min regression: enter |t|>2 & R²>0.3, release |t|<1. Governors: overnight 22:00–13:30 UTC, max 8/night, −150-pt cap, 15-min cooloff. Exit: stop 50 → BE at +20 → trail 30, 3h cap. Five random controls per trade with the identical stack; ±30-pt race.

## Three months (15 Jul – 16 Oct 2026) — a shape, not a result
| row | n | pts/tr | t | win | PF | random | edge |
|---|---|---|---|---|---|---|---|
| loose stack (setup ≥60, trigger ≥60, regime, agree, break) | 156 | +2.98 | 0.9 | 74% | 1.23 | +0.12 | +2.9 |
| breakout path only (setup + break + candle) | 203 | +1.92 | 0.7 | 72% | 1.14 | −0.33 | +2.3 |
| continuation path (regime + trigger + agree) | 497 | −1.28 | −0.7 | 69% | 0.92 | +1.08 | −2.4 |
| regime only + candle | 516 | +1.22 | 0.7 | 71% | 1.09 | +0.56 | +0.7 |
| full stack ≥70/≥70 | 35 | +0.74 | — | 71% | 1.05 | | too few |
| mean reversion, **no-regime only**, z60>2, flow flat | 131 | +1.80 | 0.5 | 72% | 1.14 | −1.30 | +3.1 |
| mean reversion, any regime | 419 | −1.37 | | | 0.90 | | −0.9 |
| divergence (weak-flow break of a prior high, fade) | 365 | −0.32 | | | 0.98 | | −0.2 |

First rows with PF > 1 and a positive edge on his market in this study. The **regime layer is where the information is**: breakout pays with it, mean reversion pays only without it, continuation loses. Exit stack: every tighter stop (30), every scratch rule (20 min < +5) and an earlier breakeven all make it worse — the wide stop is right, so his "losers rode to the full stop" fix is the gates, not the exit. The /CL scale-in on the loose stack: +5.3 pts/trade at 2.3 lots average, PF 1.12, worst trade −98. Fill interrogation: 90% of losses are full stops, wins median +14.5; 66% of nights positive.

## Pending
12 months of ticks (15 Oct 2025 – 16 Oct 2026) being pulled; the full-sample run decides whether "Compression–expansion v1" is pre-registered as a paper book on NQ (Dukascopy runs a day behind; fine for paper). Sections to be added: 12-month table, by-month, split-half, the scale-in on the full sample.
