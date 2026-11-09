# 202 — Fifty more ideas, tested and rated (9 Nov 2026, 23:20)

DK 23:12: "find 50 more trading ideas to test and then rate them all after testing". Code `src/fifty_ideas.py`, results `runs/gate/fifty_ideas.csv`.
One shared honest simulator for all 50 (decisions on closed daily bars; entries at that close / next open / same-day open->close only when the
signal is known before the open; stop checked first; one position per market; IG-like costs and overnight funding; crypto spot 0.2%).
Daily data 2000-2026 (crypto 2021-2026). Units: ATR at entry. Rating rule fixed before running: t* = 3.64 (190 ideas tried in total);
**A** t >= t*, >= 60% of years positive, last 5 years positive; **B** t >= 2, >= 55% of years positive, last 5 years positive; **C** mean > 0; **F** mean <= 0.
Not yet applied to these 50: random-entry benchmark and costs x1.5 — next step for the A and B ideas before any build.

| Rating | # | Idea | Family | Trades | Mean (ATR) | t | Years + | Last 5y |
|---|---|---|---|---|---|---|---|---|
| A | 47 | US strong close (top 10% of range, +1%) -> DAX/FTSE next open->close | cross-asset | 1140 | 0.112 | 5.99 | 22/27 | 0.005 |
| A | 14 | Turnaround Tuesday: Monday down > 1% -> buy Monday close, sell Tuesday | mean reversion | 1424 | 0.128 | 5.83 | 21/27 | 0.071 |
| A | 39 | Turn of the quarter: last day of quarter -> 3rd day | calendar | 689 | 0.252 | 4.27 | 22/27 | 0.133 |
| A | 37 | Santa rally: last 5 trading days of Dec + first 2 of Jan | calendar | 174 | 0.495 | 4.2 | 20/26 | 0.06 |
| B | 7 | Williams %R(2) < -90 above 200MA, exit close > prior high | mean reversion | 2591 | 0.139 | 4.67 | 16/27 | 0.088 |
| B | 2 | Cumulative RSI(2) 2-day sum < 35, above 200MA | mean reversion | 1549 | 0.134 | 3.43 | 18/26 | 0.202 |
| B | 12 | Weekly RSI(2) < 10 above 40-week MA, hold 5 days | mean reversion | 244 | 0.34 | 2.98 | 18/26 | 0.117 |
| B | 1 | Connors R3: RSI(3) falls 3 days, <10, above 200MA | mean reversion | 443 | 0.273 | 2.67 | 19/26 | 0.412 |
| B | 40 | Gold seasonal: long gold in Jan, Aug, Sep only | calendar | 141 | 0.927 | 2.39 | 20/27 | 0.908 |
| B | 21 | Absolute momentum: long index only while 12m return > 0 (monthly) | trend | 895 | 0.284 | 2.36 | 15/26 | 0.567 |
| B | 4 | Double 5s: 5-day low close above 200MA, exit 5-day high | mean reversion | 2964 | 0.065 | 2.02 | 16/27 | 0.081 |
| B | 5 | Close below lower Bollinger(20,2), above 200MA, exit at 20MA | mean reversion | 555 | 0.207 | 2.0 | 17/26 | 0.158 |
| C | 29 | Larry Williams volatility breakout: next day open + 0.6 x range (O->C) | breakout | 18705 | 0.03 | 7.8 | 20/27 | -0.02 |
| C | 35 | First trading day of the month (close before -> close) | calendar | 2158 | 0.114 | 5.92 | 17/27 | -0.064 |
| C | 17 | Golden cross long-only (50/200), exit death cross | trend | 129 | 2.917 | 2.41 | 10/25 | 6.407 |
| C | 49 | Crypto above 50-day average, long only (exit below), spot | crypto | 561 | 0.7 | 2.33 | 3/6 | 0.712 |
| C | 3 | Three lower highs & lows, above 200MA, exit > 5MA | mean reversion | 1035 | 0.097 | 2.15 | 16/26 | -0.037 |
| C | 46 | Tokyo lead: Nikkei up/down > 1.5% -> same direction US index open->close | cross-asset | 3014 | 0.026 | 2.01 | 17/27 | -0.036 |
| C | 27 | Rising 200-day average and close above it: long, exit below | trend | 474 | 0.552 | 1.84 | 13/27 | 1.455 |
| C | 9 | Four down closes above 200MA, exit first up close | mean reversion | 627 | 0.076 | 1.72 | 14/26 | 0.169 |
| C | 42 | Falling yields: 10y note up > 1% in 5 days -> long US index 5 days | cross-asset | 739 | 0.111 | 1.7 | 16/27 | 0.386 |
| C | 45 | Copper/gold ratio rising (20d) -> long SPX for the month | cross-asset | 338 | 0.307 | 1.56 | 14/27 | 0.668 |
| C | 16 | Short bear-market rallies: 3 up days below 200MA, cover first down close | mean reversion | 773 | 0.042 | 1.35 | 12/25 | 0.068 |
| C | 28 | Gold above its 200-day average (long only) | trend | 98 | 1.456 | 1.32 | 9/20 | 5.447 |
| C | 32 | VIX RSI(2) > 90 (fear stretch): buy index 3 days | volatility | 1570 | 0.044 | 1.18 | 13/27 | 0.169 |
| C | 50 | ETH/BTC rotation: hold ETH when ETH/BTC 30d rising, else BTC (monthly) | crypto | 50 | 0.46 | 0.66 | 4/6 | 0.625 |
| C | 41 | Flight to safety: SPX down > 2% -> buy gold 5 days | cross-asset | 173 | 0.112 | 0.65 | 10/23 | 0.034 |
| C | 20 | MACD(12,26,9) cross up above 200MA, exit cross down | trend | 1506 | 0.04 | 0.64 | 12/27 | -0.006 |
| C | 31 | VIX > 30 then 10% below its 5-day high: buy SPX/NDX 10 days | volatility | 137 | 0.061 | 0.3 | 9/13 | 0.756 |
| C | 13 | After a month down >= 5%, buy and hold one month | mean reversion | 298 | 0.056 | 0.28 | 16/26 | 1.685 |
| C | 36 | Options-expiry week long (Mon close of the week with the 3rd Friday -> Fri) | calendar | 1196 | 0.009 | 0.21 | 15/27 | -0.248 |
| C | 10 | 10-day low in a range (efficiency < 0.3), hold 5 days | mean reversion | 2512 | 0.005 | 0.14 | 15/27 | -0.074 |
| F | 30 | NR4 inside day breakout (Crabel), exit at close | breakout | 8261 | -0.001 | -0.12 | 12/27 | -0.061 |
| F | 48 | Crypto turn of the month (last day -> 3rd day), spot | crypto | 569 | -0.022 | -0.43 | 2/6 | -0.016 |
| F | 19 | 52-week-high breakout long, exit 50-day low | trend | 375 | -0.263 | -0.54 | 10/27 | -0.54 |
| F | 11 | Down day closing in top 25% after a 5-day fall, hold 3 days | mean reversion | 785 | -0.031 | -0.57 | 13/27 | -0.057 |
| F | 44 | Yen risk-off: USD/JPY down > 1.5% -> buy NDX/SPX 5 days | cross-asset | 133 | -0.114 | -0.68 | 9/23 | 0.074 |
| F | 33 | Low-vol regime: 20-day realised vol < 10% -> long until > 15% | volatility | 229 | -0.368 | -0.94 | 10/26 | 1.072 |
| F | 25 | Supertrend(10,3) style: 10-day ATR channel flip, 18 markets | trend | 408 | -0.509 | -2.35 | 8/27 | -1.217 |
| F | 18 | Donchian 20 breakout long above 200MA, exit 10-day low | trend | 1579 | -0.254 | -2.84 | 9/27 | -0.352 |
| F | 34 | Bollinger squeeze (6-month narrowest) then 20-day breakout | volatility | 863 | -0.341 | -3.52 | 5/27 | -0.406 |
| F | 43 | Oil shock: oil +5% day -> short US index 3 days | cross-asset | 354 | -0.214 | -3.6 | 5/23 | -0.602 |
| F | 15 | Weekend: buy Friday close, sell Monday close | calendar | 9432 | -0.039 | -4.61 | 11/27 | -0.011 |
| F | 22 | 3-month time-series momentum, 18 markets (monthly) | trend | 3254 | -0.299 | -4.86 | 10/27 | -0.436 |
| F | 8 | Daily gap down > 0.5 ATR below prior low -> buy open, sell close | mean reversion | 1185 | -0.136 | -6.15 | 3/27 | -0.151 |
| F | 23 | 1-month time-series momentum, 18 markets (monthly) | trend | 3277 | -0.393 | -6.38 | 7/27 | -0.348 |
| F | 24 | Keltner breakout (close > EMA20 + 2 ATR) with trend, exit at EMA20 | trend | 3407 | -0.331 | -6.4 | 3/27 | -0.525 |
| F | 26 | Turtle 20/10 both sides, 18 markets | trend | 9399 | -0.104 | -6.95 | 4/27 | -0.118 |
| F | 38 | Monday weakness: short Friday close -> Monday close | calendar | 9432 | -0.083 | -9.86 | 6/27 | -0.111 |
| F | 6 | Connors %b < 0 three days, above 200MA, exit %b > 0.75 | mean reversion | 0 | - | - | - | - |

Totals: A 4, B 8, C 20, F 18 (idea 6 produced no signals).
Notes: #29 (Larry Williams breakout) and #35 (first day of the month) have big t but negative last 5 years -> C. #17/#27/#28 trend filters
have large means but few trades and long holds (C). Classic breakout/trend-following variants on daily bars (#18, 22-26, 34) fail after
IG costs and funding — consistent with doc 197.

## The 12 A/B ideas through the remaining gate checks (`src/fifty_ideas_gate.py`, `runs/gate/fifty_ideas_gate.csv`), 23:25
Random-entry permutation test (200 runs, same markets/counts/exits), costs x1.5, last 365 days, >= 60% of years, multiple-testing t.
| Verdict | Idea | Mean | Random 95th pct | Costs x1.5 | Last year | Years + |
|---|---|---|---|---|---|---|
| **PASS** | Turn of the quarter | +0.25 | +0.04 | +0.23 | +1.08 | 22/27 |
| **PASS** | Santa rally | +0.50 | +0.20 | +0.47 | +0.62 | 20/26 |
| **PASS** | US strong close -> DAX/FTSE next open->close | +0.11 | +0.01 | +0.10 | +0.03 | 22/27 |
| PASS except t | Connors R3 | +0.27 | +0.11 | +0.25 | +0.96 | 19/26 |
| PASS except t | Bollinger dip-buy above 200MA | +0.21 | +0.05 | +0.18 | +0.43 | 17/26 |
| PASS except t | Cumulative RSI(2) | +0.13 | +0.04 | +0.11 | +0.33 | 18/26 |
| FAIL (last year -0.12 only) | Turnaround Tuesday | +0.13 | -0.01 | +0.11 | -0.12 | 21/27 |
| FAIL | Williams %R(2), Double 5s, absolute momentum (< 60% of years) | | | | | |
| FAIL | Weekly RSI(2) (last year -0.48) | | | | | |
| FAIL | Gold Jan/Aug/Sep (does not beat random gold longs: gold rose) | | | | | |

## Fallow periods for the 12 candidates (`src/fifty_ideas_fallow.py`, `runs/gate/fifty_ideas_fallow.txt`), DK 23:21
Same per-condition walk-forward test as doc 201 (month / weekday / VIX band, chosen only from earlier years, adopted only if it raises the
out-of-sample total and keeps >= 50% of trades). Result: **no meaningful switch** for any of them. Skipping each idea's historically bad
months, weekdays or VIX levels cut the out-of-sample total in almost every case (e.g. turn of the quarter +112 -> +83 to +89; Bollinger dip
+123 -> +41 to +81; cumulative RSI(2) +177 -> +113 to +151). The three that technically 'adopt' gain under 1.5% (absolute momentum skip
Wednesdays +206 -> +209; gold seasonal skip Thursdays +65 -> +68; US close -> Europe skip Mar/Aug +63.1 -> +63.6) — too small to trust; not used.
These are short-hold dip-buys and calendar effects: their bad patches don't repeat, so they run every signal.
