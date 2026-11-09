# 203 — Fifty more ideas (#51-100), tested, rated, gate-checked and fallow-checked (9 Nov 2026, 23:35)

DK 23:22: "Repeat this process for another 50 ideas or trading concepts". Same simulator and fixed rating as doc 202 (`src/fifty_ideas_2.py`,
`runs/gate/fifty_ideas_2.csv`); t* = 3.70 (240 ideas tried in total). Totals: **A 3, B 6, C 13, F 28.**

## Gate and fallow checks on the A/B ideas (`src/fifty_ideas_2_checks.py`)
| Verdict | Idea | Mean (ATR) | Random 95th | Costs x1.5 | Last year | Years + | Fallow switch |
|---|---|---|---|---|---|---|---|
| **PASS** | 51 RSI(2) < 5 and below the 5-day average, above 200MA, exit above the 5-day average | +0.245 | +0.060 | +0.221 | +0.70 | 19/26 | none helps |
| **PASS** | 61 Stochastic %K(5) < 10 above 200MA, exit %K > 50 | +0.169 | +0.026 | +0.144 | +0.37 | 18/26 | none helps |
| PASS except t | 62 Z-score(20) < -2 above 200MA (= the Bollinger dip-buy of doc 202) | +0.207 | +0.045 | +0.183 | +0.43 | 17/26 | none helps |
| PASS except t | 84 Stocks down 5 days while bonds up -> long US index 5 days | +0.100 | +0.022 | +0.079 | +0.18 | 17/27 | none helps |
| PASS except t | 96 Crypto 7-day high breakout above the 50-day, exit 5-day low (spot) | +0.357 | +0.087 | +0.357 | +0.04 | 5/6 | none helps |
| FAIL | 52 Two closes below Keltner, above 200MA | +0.437 | | | -0.55 | 17/26 | |
| FAIL | 59 5-day drop > 2.5 ATR above 200MA | +0.251 | | | +0.82 | 15/26 (< 60%) | |
| FAIL | 86 Copper +3% -> long AUD/USD | +0.208 | | | -0.09 | 15/19 | |
| FAIL | 87 SPX > 1% -> FTSE/DAX next day same way (last year -0.10; overlaps doc 202 #47) | +0.116 | n/a* | | -0.10 | 23/27 | |
*#87's random benchmark is not valid (its side depends on the signal day); it fails on the last year regardless.

## All 50, ranked
| Rating | # | Idea | Family | Trades | Mean | t | Years + | Last 5y |
|---|---|---|---|---|---|---|---|---|
| A | 87 | SPX day move > 1% -> FTSE/DAX next open->close in the same direction | cross-asset | 3637 | 0.116 | 10.1 | 23/27 | 0.042 |
| A | 61 | Stochastic %K(5) < 10 above 200MA, exit %K > 50 | mean reversion | 1774 | 0.169 | 4.48 | 18/26 | 0.129 |
| A | 51 | RSI(2) < 5 and below 5MA, above 200MA, exit close > 5MA | mean reversion | 752 | 0.245 | 4.35 | 19/26 | 0.362 |
| B | 59 | 5-day drop > 2.5 ATR, above 200MA, hold 5 | mean reversion | 703 | 0.251 | 3.35 | 15/26 | 0.539 |
| B | 52 | Two closes below Keltner (EMA20 - 2 ATR), above 200MA, exit EMA20 | mean reversion | 210 | 0.437 | 2.69 | 17/26 | 0.07 |
| B | 96 | Crypto 7-day high breakout above 50-day, exit 5-day low | crypto | 694 | 0.357 | 2.45 | 5/6 | 0.356 |
| B | 86 | Copper +3% day -> long AUD/USD 3 days | cross-asset | 139 | 0.208 | 2.35 | 15/19 | 0.176 |
| B | 84 | Stocks down 5 days while bonds up -> long US index 5 days | cross-asset | 1565 | 0.1 | 2.23 | 17/27 | 0.311 |
| B | 62 | Z-score(20) < -2 above 200MA, exit z > 0 | mean reversion | 555 | 0.207 | 2.0 | 17/26 | 0.158 |
| C | 63 | Short RSI(2) > 95 below 200MA, cover RSI(2) < 50 | mean reversion | 334 | 0.179 | 3.06 | 12/22 | 0.269 |
| C | 88 | Yen carry unwind: USD/JPY -3% in 5 days -> long USD/JPY 5 days | cross-asset | 67 | 0.392 | 2.0 | 13/21 | 0.153 |
| C | 60 | RSI(14) < 30 above 200MA, exit RSI(14) > 50 | mean reversion | 70 | 0.529 | 1.63 | 14/23 | 0.235 |
| C | 76 | January effect: Russell first 5 trading days | calendar | 52 | 0.438 | 1.49 | 17/26 | 0.668 |
| C | 97 | Crypto low-volatility regime (20d vol < 40%/yr) above 100-day: long 10 days | crypto | 112 | 0.482 | 1.37 | 3/5 | 0.482 |
| C | 65 | Pullback to the 50-day in an uptrend (50 > 200), exit +2 ATR or 10 days | trend pullback | 896 | 0.076 | 0.91 | 14/27 | -0.188 |
| C | 83 | Gold/silver ratio z > 2 -> long silver (expect silver to catch up), exit z < 0 | pairs | 96 | 0.249 | 0.61 | 14/27 | 1.112 |
| C | 95 | ETH/BTC ratio z < -2 -> long ETH, exit z > 0 | crypto | 35 | 0.256 | 0.59 | 2/5 | 0.256 |
| C | 55 | Bullish engulfing at a 10-day low, above 200MA, hold 3 | candles | 142 | 0.069 | 0.58 | 13/24 | -0.164 |
| C | 89 | Gold down 3 days in a row above 200MA -> hold 3 | mean reversion | 363 | 0.038 | 0.44 | 9/25 | -0.041 |
| C | 53 | Big red candle (close < open - 1 ATR), above 200MA, hold 2 days | candles | 1883 | 0.011 | 0.38 | 15/26 | 0.095 |
| C | 66 | Two closes in the bottom 20% of the range, above 200MA, hold 2 | candles | 1054 | 0.01 | 0.27 | 14/27 | 0.075 |
| C | 99 | Commodity pullback: RSI(2) < 10 above 200MA on oil/copper/silver, exit RSI > 70 | mean reversion | 555 | 0.011 | 0.15 | 12/25 | -0.115 |
| F | 68 | Gap up > 0.5 ATR above prior high -> buy open, sell close | momentum | 1316 | -0.002 | -0.13 | 11/27 | 0.05 |
| F | 54 | Hammer at a 10-day low (lower wick > 2x body, close top third), above 200MA, hold 3 | candles | 440 | -0.01 | -0.14 | 13/26 | -0.211 |
| F | 70 | Close at a 6-month high -> hold one month, 18 markets | momentum | 279 | -0.048 | -0.19 | 9/26 | 1.084 |
| F | 77 | September effect: short indices for September | calendar | 185 | -0.054 | -0.19 | 13/27 | 1.016 |
| F | 72 | Above 200MA with positive 20-day momentum: long indices, hold 20 | momentum | 809 | -0.026 | -0.21 | 12/27 | 0.563 |
| F | 79 | Triple-witching Friday: short Thursday close -> Friday close | calendar | 424 | -0.007 | -0.21 | 12/27 | 0.064 |
| F | 69 | Weekly inside bar -> buy a close above its high the next week, hold 5 | breakout | 564 | -0.017 | -0.25 | 13/27 | 0.188 |
| F | 67 | 20-day-high close above 200MA, hold 10 days fixed | momentum | 1903 | -0.016 | -0.32 | 12/27 | 0.053 |
| F | 93 | Crypto RSI(2) < 10 above its 200-day, exit RSI(2) > 70 | crypto | 252 | -0.039 | -0.46 | 2/5 | -0.039 |
| F | 57 | Close above prior high after 3 down days (reversal confirmed), hold 3 | candles | 700 | -0.028 | -0.51 | 12/27 | -0.04 |
| F | 82 | VIX > 1.3 x its 20-day average -> buy index 5 days | volatility | 364 | -0.063 | -0.52 | 10/23 | -0.064 |
| F | 100 | FX pullback: RSI(2) < 10 above 200MA on 5 pairs, exit RSI > 70 (both sides) | mean reversion | 1531 | -0.016 | -0.61 | 13/27 | -0.099 |
| F | 92 | Crypto -10% day -> buy, hold 3 days | crypto | 220 | -0.056 | -0.72 | 4/6 | -0.093 |
| F | 85 | Oil +3% day -> short USD/CAD 3 days | cross-asset | 322 | -0.078 | -1.3 | 12/24 | -0.142 |
| F | 58 | Key reversal: new 20-day low but closes up on the day, hold 3 | candles | 959 | -0.061 | -1.32 | 12/27 | -0.11 |
| F | 56 | Inside day after a down day, above 200MA, hold 2 | candles | 2029 | -0.036 | -1.39 | 11/27 | 0.032 |
| F | 91 | Crypto weekend: long Friday close -> Sunday close | crypto | 2500 | -0.025 | -1.51 | 3/6 | -0.03 |
| F | 64 | Short 5-day high close below 200MA, cover 5-day low | mean reversion | 1287 | -0.071 | -1.63 | 9/26 | -0.308 |
| F | 81 | Overreaction: short the day after a > 2% up day | mean reversion | 2262 | -0.025 | -1.8 | 8/27 | -0.026 |
| F | 78 | Day after a US holiday: long the close before -> next close | calendar | 1080 | -0.056 | -2.14 | 10/27 | -0.235 |
| F | 73 | 50-day slope / ATR > 0.1 (or < -0.1), 18 markets, exit on slope flip | trend | 1653 | -0.223 | -2.46 | 10/27 | -0.129 |
| F | 94 | Alt 20% below its 20-day high while BTC above its 50-day -> hold 7 | crypto | 172 | -0.271 | -2.67 | 2/5 | -0.271 |
| F | 80 | Quarter-end window dressing: long the last 5 days of the quarter | calendar | 745 | -0.153 | -2.76 | 11/27 | -0.082 |
| F | 75 | Tuesday close -> Wednesday close long | calendar | 9603 | -0.033 | -4.14 | 9/27 | -0.006 |
| F | 74 | Breakout after a 30-day consolidation (range < 5 ATR), 18 markets, hold 10 | breakout | 2309 | -0.212 | -4.75 | 5/27 | -0.265 |
| F | 98 | Crypto Monday: long Sunday close -> Monday close | crypto | 2509 | -0.076 | -4.94 | 2/6 | -0.075 |
| F | 71 | Dual moving average 10/30 both sides, 18 markets | trend | 2533 | -0.477 | -6.89 | 3/27 | -0.576 |
| F | 90 | 10-year note golden cross (bond trend), exit death cross | trend | 21 | -6.989 | -7.68 | 1/16 | -6.257 |

Pattern (both batches of 50): what survives is buying short, sharp dips in rising equity indices (+ gold), a few calendar effects, and
one crypto breakout. Candlestick patterns, daily breakouts/trend systems after IG costs and funding, weekday effects, most cross-asset
triggers, crypto weekday/weekend effects, and pullback rules on FX/commodities fail. No fallow switch helps any of the survivors.
