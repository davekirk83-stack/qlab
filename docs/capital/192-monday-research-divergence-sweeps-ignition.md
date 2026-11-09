# 192 — Monday research (9 Nov 2026): double divergence, trend-aligned sweeps, Ignition's big losers, 99-day line

DK 9 Nov 16:46: "Do the research now" — the items queued during the day from Cheds' *Trading Wisdom* (lesson 38), Atif Hussain's
ICT course page, and DK's thesis-stop point (8 Nov). Same rule as always: build each to work, iterate once where it fails, judge on both periods.

## 1. Double divergence (Cheds lesson 38) — `src/double_divergence_test.py`
BTC 1h 2020-26, pivots 3 bars each side. Forward return in the reversal direction over 48h:
- OBV bullish DOUBLE divergence (two lower lows in price, two higher lows in OBV): +60bp (dev, n22) / +66bp, 68% (hold, n22) vs
  +32 / +12bp at any swing low. Better in both periods, but only 22 cases each.
- OBV bearish double divergence, and both CVD versions: inconsistent between periods.
- Verdict: the bullish OBV double divergence is a promising, rare signal (about 3 a year) — worth a forward watch, not yet a trigger.

## 2. ICT trend sweep (4h bias, sweep against it, FVG pullback entry, 3R) — `src/ict_trend_sweep_test.py`
- 15-min BTC: gross +0.05R per trade in both periods with the bias, but stops are tight and costs eat it (-0.16 / -0.26R at 0.1%).
- 1-HOUR BTC (iteration): with the 4h bias, gross +0.15R in both periods (n276 / n231, 34-35% wins at 3R); with limit-order fees
  (0.04% round trip) +0.11R / +0.09R. WITHOUT the bias filter the hold period is negative (-0.02R gross, -0.07R with fees).
  The bias filter is what makes it work — the first sweep variant that holds up in both periods.
- US Tech 100 15-min (cash hours): ~0 in 2020-21, negative in 2025-26.
- Verdict: candidate engine — BTC 1h trend-aligned sweep, limit entries. Next: costs/fill realism on a real venue, then paper.

## 3. Ignition's big losers — `src/ignition_losers_test.py`
84 trades Oct 2025 - Nov 2026, 10 big losers (<= -30 pts). Signal-bar expansion size, delta share, close position, ATR and hour
do NOT separate them from the rest. So no thesis-stop or filter can target them from the signal bar; keep Ignition as is.
Side note: signal bars closing in their top 20% averaged +36.5 pts vs +10.5 for the rest (n26 vs 44) — a sizing idea for later.

## 4. 99-day line on the panel's ladder — `src/ladder_99line_test.py`
Range v3 ladder on BTC 2020-26: filtering by the 99-day line cut totals (+226% / +74% -> +124% / +43%) with no consistent gain per
episode; every side/regime bucket is positive. Not added. (It does matter for the panic ladder — doc 191 — and for the sweep engine above.)
