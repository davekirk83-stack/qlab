# 215 — TPS coin ladder on Revolut X: dry run built (10 Nov 2026)

DK 09:51 "Yes" (build the crypto TPS ladder for Revolut X as a dry run, ready for live). Why: the IG books are all index dip/calendar
trades — busy and idle at the same times; average exposure ~1x of the 5x allowed (doc 214 replay). Coins trade every day, weekends too.

- Runner `src/revx_tps.py`; workflow `.github/workflows/revx-tps.yml` daily 00:10 UTC, **dry** (no orders) unless DK sets
  REVX_TPS_LIVE_ENABLED=true. State runs/revx_tps_dry/.
- Rules = doc 200: 10 coins (BTC ETH SOL XRP DOGE AVAX LINK ADA LTC DOT), daily UTC candles; close > 200-day and RSI(2) < 25 twice -> buy
  10% of the episode budget; each lower close adds 20/30/40%; exit RSI(2) > 70, 30 days, or 15% under average cost. Budget 10% of the book
  per episode, max 10 open, book −15% -> halt (CAP-021 5 Nov limits). Market orders (IOC 1% through), 0.09% taker + 0.1% slippage.
- Replay through the runner on Revolut X daily candles (backtest), Aug 2024 – Nov 2026: £500 -> £657, 150 episodes, 91% won,
  worst episode −$13, max drawdown 4.5%, lowest £498. By year: 2024 (4 months) +£28, 2025 +£130, 2026 −£1. Best coins ADA, XRP, LINK.
- Going live is DK's decision: it uses the 5 Nov Revolut X approval for this book instead of the (unfunded) Range book.
