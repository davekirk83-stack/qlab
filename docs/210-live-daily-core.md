# 210 — Live daily core books on IG (10 Nov 2026)

DK 07:27: "start making me reliable small gains on IG however small."

## What was built
- `src/ig_daily_books.py` now has a LIVE mode (still demo by default). Live = the core books only: **RSI(4) dip, TPS, turn of the month, Santa**.
  No Halloween, US-close->Europe or gold London on live (WEAK or data fault).
- Live rules in code: risk 2% of the book per trade; a trade whose IG minimum stake would risk more than 2% is **skipped**, never oversized;
  6% cap on total equity-index risk; 5x exposure; −4% day stop and −15% floor stop new entries. Stake placed = stake counted (real P&L).
- Workflow `.github/workflows/ig-daily-live.yml`, same times as the demo (US/EU open and close jobs). It trades only when DK sets the repo
  variable **IG_DAILY_LIVE_ENABLED=true** and **IG_LIVE_ENABLED is not true** (one £500 book on the account at a time). Claude never sets either.
  Confirmation string CAP021-AMENDED-2026-11-10-IG-DAILY-CORE-500. Live state/ledger: runs/ig_daily_live.

## What it would have done (backtest: runner replay, last 400 trading days, live rules, IG min stake 0.01/pt assumed)
- 99 trades: RSI(4) 43 (+£96), turn of month 54 (+£44), Santa 2 (+£11). TPS: every rung skipped (IG minimum is ~10x the 2% budget on £500).
- £500 -> £652. 18 of 20 months positive, worst month −£29 (Mar 2026), max drawdown £30, win rate 76%, about £0.38 per trading day.
- NQ and Wall Street mostly skipped (minimum stake > 2% risk); trades land on US 500, FTSE, gold, some DAX.

## To switch
Settings -> Secrets and variables -> Actions -> Variables: IG_LIVE_ENABLED = false (intraday live off), IG_DAILY_LIVE_ENABLED = true.
