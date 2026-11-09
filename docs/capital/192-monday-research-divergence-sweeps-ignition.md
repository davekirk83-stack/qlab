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

## Follow-up the same evening (DK: "Yes please") — robustness
### Sweep engine — `src/sweep_robustness_test.py`
- Fill realism: requiring price to trade THROUGH the limit changes nothing on BTC (fills 72% of setups).
- BTC: 18 of 27 nearby settings positive in both periods; base rules +0.11R / +0.09R at 0.04% fees, +0.06 / +0.01R at 0.10%.
- ETH and SOL (never seen): base rules about flat (-0.03 / +0.04R; -0.01 / +0.03R). Only the 4R / EMA30 variant is positive on all
  three in both periods (BTC +0.19/+0.10, ETH +0.01/+0.03, SOL +0.10/+0.10). Longs vs shorts split differently by coin.
- Verdict: real on BTC, weak transfer to alts, sensitive to fees -> paper-test on BTC with limit orders only, alts as a shadow arm.
### Bullish OBV double divergence as a rare book — `src/double_div_more.py`
- 48h forward return beats the base rate in all six crypto cells (BTC, ETH, SOL x two periods). Indices: too few events, negative.
- The tight-stop 3R version gets shaken out; the edge is the drift. HOLD version (buy at confirmation, hold 48h, -8% catastrophe stop,
  0.1% costs): BTC +0.78% / +0.56%, ETH +3.36% / +0.82%, SOL +1.78% / +2.52% per trade; 121 trades (~18 a year), 60% winners,
  every calendar year positive (2020 +27%, 2021 +62%, 2022 +25%, 2023 +2%, 2024 +74%, 2025 +1%, 2026 +8%, each trade on its own stake).
- DK (16:51): happy to run a rare book if it makes money on its rare days. Long-only spot -> fits the Revolut X account.

## 9 Nov 17:10 — paper books registered (DK: "Yes")
- **Paper book 15** (`src/paperbook15.py`): 1h trend-aligned sweep. Main = BTC, base rules (3R, 4h EMA50, slope 6, strict fill, 0.04% fees);
  shadow = ETH and SOL with the 4R / EMA30 variant. £500 notional per market, 1% risk per trade. PASS after 3 months: main positive,
  >= 20 trades, mean R within half of the backtest's +0.09R.
- **Paper book 16** (`src/paperbook16.py`): OBV bullish double divergence on BTC/ETH/SOL 1h, long at confirmation, hold 48h, -8% stop,
  0.1% costs, 10% of a £500 pool per trade. PASS after 6 months: positive, >= 8 trades, mean >= +0.5% per trade.
- Both replay from 10 Nov 2026 on public Binance data every 4 hours via `.github/workflows/paper-books-15-16.yml` (no keys, no orders)
  and write runs/paper15/ and runs/paper16/. Reviewed with the other books in the week of 16 Nov.
- Dry run over the last ~6 weeks before registration (not part of the record): book 15 BTC 9 trades, +12.3R; ETH shadow 6 trades -1.4R.
  Book 16 had one BTC signal on 8 Nov 00:00 at 75,799 (before the start date, so not counted).
