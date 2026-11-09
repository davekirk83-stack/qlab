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
