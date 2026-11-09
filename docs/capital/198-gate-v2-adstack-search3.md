# 198 — Gate v2 (recognised validation methods), AuclairsDad's layers, market search 3 (9 Nov 2026, late)

## Gate v2 — what was added and why (DK: "check online for other recognised testing systems")
Recognised practice (walk-forward analysis; Bailey & Lopez de Prado's deflated Sharpe / probability of backtest overfitting; White's
Reality Check and Masters' permutation tests; cost stress) vs v1: v1 already had a look-ahead detector, gate-side fills, a last-year holdout and a
random-entry benchmark (a permutation-style test). Added in `src/gate.py` (judge2):
- **walk-forward**: history cut into 6 windows (daily books: years); >= 60% must be positive;
- **multiple testing**: every idea ever judged is counted (runs/gate/registry.json, 113 so far incl. tonight's pre-gate ideas); the full-sample
  t must beat the Sidak-adjusted threshold (now ~3.5). One lucky year can no longer pass — turn-of-the-month's v1 "TESTED" was exactly that;
- **costs x1.5** must still be positive.
Not added (yet): combinatorial purged CV / PBO (needs a parameter grid per book; next step for the survivors).

## Verdicts under v2 (full history, ATR units)
| Book | v2 | All trades | Walk-forward | Last year | Only failing check |
|---|---|---|---|---|---|
| Ignition v1.1, US hours | WEAK | n87 +0.33, t 2.3 | 83% | +0.30 (n39) | t < 3.5 |
| Gold: London breakout of the Asian range | WEAK | n104 +1.78, t 2.2 (+8 pts/trade, 6 of 7 months +) | 83% | +1.51 (n45) | t < 3.5 |
| Spike, Wall Street | WEAK | n19 +0.86 | 67% | +1.51 (n10) | t < 3.5 |
| Noise band, US Tech 100 | WEAK | n229 +0.16 | 67% | +0.30 | t, random |
| Turn of the month, 6 indices | FAILED | n1868 +0.07 | 48% of 27 years | +0.58 | t, walk-forward, random |
| Trend 100-day, IG quarterly bets, 18 mkts | FAILED | n1021 +0.49 | 59% of 27 years | -1.94 | holdout, WF, t, random |

## AuclairsDad's layers on US Tech 100 (src/ad_stack_gate.py), all hours ex-lunch, +1 pt out of hours
Base Ignition all hours: +3.6 pts dev / +1.6 hold. + REGIME (16x15-min regression): +4.2 / -0.6. + REGIME + COIL: +5.0 / +3.5 (n120/83).
Mean reversion only when no regime: -1.5 / -6.5 (fails). The coil+regime stack is the best-quality AuclairsDad variant (~200/yr).

## Market search 3 (src/market_search_3.py)
Overnight drift after weak US closes (NY Fed): mixed — US Tech 100 + small, US 500 and Wall Street negative. Every-night version: fails pooled.
Gold London breakout of the Asian range (published retail backtest, PF ~1.37 over 3.7 years): see table — the best new candidate tonight.

Sources: Boyarchenko, Larsen & Whelan, "The Overnight Drift" (NY Fed Liberty Street, 2021); MQL5 "London Breakout on Gold: 3.7 Years of
Backtests"; Baltussen, Da & Soebhag "End-of-Day Reversal" (stocks only — not testable on our indices); Della Corte, Kosowski & Wang
overnight/intraday reversal (cxoadvisory); MQL5 "Unified Validation Pipeline Against Backtest Overfitting"; Sullivan, Timmermann & White.

## Market search 4 (src/market_search_4.py, gate v2), 9 Nov 22:40
| Idea | v2 | All trades | Walk-forward | Last year |
|---|---|---|---|---|
| RSI(2) pullback, 8 markets daily (Connors & Alvarez) | WEAK | n1482 +0.13 ATR, t 2.9 | 69% of 26 years | +0.34 (n92) |
| Asian-range breakout, Germany 40 | WEAK | n88 +0.55 | 67% | +2.0 |
| Asian-range breakout GBP/USD, USD/JPY, FTSE | FAILED | | | |
| VIX spike reversion (SPX, NDX) | WEAK, barely | n334 +0.05 | 54% | |
| Crypto 20-day-high breakout, 10 coins (spot) | FAILED | n275 +1.37 but 33% of windows; last year -0.55 | | |
| Opening-gap fade, 3 US indices | FAILED | | | |

## Seasonal "fallow months" (DK 22:41) — src/seasonal_switch.py, walk-forward (months to skip chosen only from earlier years, >= 8 of them)
- Trend 100-day, IG quarterly bets: total +290 -> **+373 ATR**; last 5 years **-95 -> +14**; positive years 11 -> 10 of 19; keeps 60% of trades.
- Turn of the month: total +27 -> +9; last 5 years -2 -> +19; positive years 8 -> 10 of 19. Mixed.
- RSI(2) pullback: total +183 -> +153; last 5 years +91 -> +55. Hurts — keep it running all year.
Intraday books (Ignition, gold, spike) have ~1 year of data: no month-of-year test possible until more history is pulled.

## Market search 5 (src/market_search_5.py), daily, 2000-2026, gate v2
| Idea | v2 | All trades | Years positive | Last 5 years |
|---|---|---|---|---|
| Time-series momentum 12m, 18 markets (Moskowitz, Ooi & Pedersen 2012), IG quarterly bets | WEAK | n3140 +0.18 ATR, t 2.9 | 16/27 | +0.15 |
| Double 7s, 8 markets (Connors & Alvarez) | WEAK | n2070 +0.14, t 2.9 | 17/26 | +0.13 |
| IBS low close, 8 markets | FAILED | n9348 0.00 | 14/27 | 0.00 |
Note: for long-only daily books the random-entry benchmark also earns the market's drift (2026 was a strong year), so "beats random" is hard.
Robustness (src/robustness_daily.py): trend 25/27 nearby settings positive; RSI(2) 24/24.

## Daily books combined (src/portfolio_daily.py), 2001-2026, risk-balanced
Monthly correlation: RSI(2)-Double 7s 0.69 (same idea); every other pair 0.04-0.08 (independent).
Combined: 60% of months positive, 18 of 26 years; worst 12 months -38 ATR vs -134 for the worst single book. 2022 -20, 2023 +11, 2024 +27,
2025 +54, 2026 so far -4.

## Market search 6 (src/market_search_6.py)
| Idea | v2 | All trades | Years positive | Last 5 years |
|---|---|---|---|---|
| Halloween: long 7 indices Nov-Apr only (Bouman & Jacobsen 2002) | WEAK (passes the multiple-testing t: 3.56 vs 3.54; random benchmark n/a) | n668 +0.48 ATR | 19/27 | +0.79 |
| Same, every month (comparison) | WEAK | n1305 +0.15 | 14/27 | +0.44 |
| NR7 breakout (Crabel), 12 markets | FAILED | n7511 -0.06 | 8/27 | |
| Pre-holiday, 4 US indices | FAILED | n1084 -0.03 | 10/27 | |
| FX month-end rebalancing (Melvin & Prins) | FAILED | n727 0.00 | 11/23 | |

## Liquidity sweeps (Stoic's thread, DK 22:55) — src/sweep_liquidity_test.py, src/sweep_liquidity_1h.py, BTC Dec 2021 - Nov 2026
Fading a sweep of the recent range (12h on 15-min / 24h on 1h), closing back inside, target the range middle: FAILED in every year
(15-min -0.34 ATR, 1h -0.18). His mechanism shows up — sweeps where open interest DROPPED (a real liquidation) lose about half as much
(1h: -0.08 ATR, 2 of 5 years positive) — but not enough to pay costs. His own chart (13 daily sweeps of 30+ day levels, 6 reversed) agrees.
## Positioning (src/positioning_test.py), Binance futures metrics
| Idea | v2 | Trades | By year |
|---|---|---|---|
| Crowd contrarian: Binance long/short ratio in its top/bottom 10% of 90 days -> fade 3 days | WEAK | n202 +0.23 ATR, t 2.1 | 2022 -0.28, 2023 +0.51, 2024 +0.31, 2025 +0.26, 2026 +0.20 |
| OI-confirmed 20-day breakout (OI +5% in 3 days) | WEAK | n45 +0.60 | 4 of 5 years + |
| OI flush buy (OI -8% & price -4% in a day) | FAILED (n12) | | |
