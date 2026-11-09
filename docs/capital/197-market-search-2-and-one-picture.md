# 197 — Market search 2 (published research), AuclairsDad stack, and the one consolidated picture (9 Nov 2026, late)

Gate change made before re-judging (doc 196 updated): results in ATR units (points / ATR at the signal), because tight stops inflated "R".
Turn-of-month uses the business-month calendar (known in advance); the first version's look-ahead flag was a false positive from using the next bar's date.

| Book | Label | Most recent period | Earlier period | Trades/yr |
|---|---|---|---|---|
| Turn of the month, 6 indices (long 1 day before month end -> 3rd day) | **TESTED** | n68, +0.58 ATR, t 3.0, both halves + , above random | n1800 (2000-25) +0.05 ATR — far weaker history | ~70 |
| Ignition v1.1 US Tech 100 (US hours) | WEAK | n39 +0.30 ATR, both halves + | n48 +0.35 ATR (+14.5 pts, t 2.4) | ~90 |
| Ignition all hours ex-lunch | FAILED by rule (first recent half -) | n287 +2.6 pts | n432 +4.5 pts (t 2.7) | ~670 |
| Noise-band momentum, US Tech 100 | WEAK | n98 +0.30 ATR | n131 +0.06 | ~230 |
| Spike, Wall Street | WEAK | n10 +1.5 ATR | n9 +0.13 | ~45 |
| Spike US Tech 100 / US 500 | FAILED | | | |
| Noise band US 500 / Wall St; last-half-hour (3 indices); BTC 22:00 UTC; daily 100-day breakout trend (20 mkts); books 15/16; Keltner v1; ORB gold | FAILED | | | |
| Stack: Ignition direction + noise band (NQ) | WEAK in ATR, negative in points | n28 | n12 | ~66 |

Daily trend (20 markets): +0.19 ATR per trade over 2000-25 (n1036) but -2.4 ATR in the last 12 months (whipsaw year); judged FAILED by the
fixed rule. A one-year holdout is a poor judge of a slow book — noted, not a reason to change the rule now.

AuclairsDad's own sheets (doc 90): +3.75 to +8 pts/trade on futures (~0.5 pt costs), 3.5-5 trades/day. Our honest all-hours Ignition:
+4.5 / +2.6 pts per trade on ~670/yr at IG-like costs — the same order. The edge is thin per trade; costs decide it.
Sources: Zarattini, Aziz & Barbon (2024) "Beat the Market" (concretumgroup.com / SSRN); Gao, Han, Li & Zhou (2018, JFE); Quantpedia
"Intraday seasonality in Bitcoin"; Hurst, Ooi & Pedersen "A Century of Evidence on Trend-Following"; Hatlemark & Grohshennig (2022) turn of month.
