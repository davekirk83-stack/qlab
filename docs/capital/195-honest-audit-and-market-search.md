# 195 — Honest audit, ladder fix attempts, market search 1, spike engine recheck (9 Nov 2026 evening)

Confidence labels used from now on: **MEASURED** = real fills on IG/Revolut X; **TESTED** = honest backtest (closed bars only, one position
at a time, costs) that held on data it was not tuned on; **WEAK** = honest but small, uneven or few trades; **FAILED** = loses when honest.

## Audit for the look-ahead flaw (doc 194)
Ignition (paperbook7: signal on closed bar, entry next open, stop first) — clean. Spike engine — clean pricing (but see below). Book 15
(BTC 1h sweep: FVG confirmed on a closed bar, limit from the next bar, 4h bias shifted) — clean. Book 16 (OBV double divergence: pivot known
3 bars later, entry at that close) — clean. BTC stress ladder (buys at the close of the bar making the low) — clean. Capitulation retest —
clean except a same-day fill+target ordering ambiguity (optimistic; fix before any use). Keltner Range v1 (daily, entry at the close that
crosses the band) — clean; not running since ~23 Oct. Range v3 ladder (IG and Revolut X) — FAILED (prices bar i with bar i's close).

## Ladder fix attempts (`src/ladder_solve_1.py`, `runs/ladder_solve_1.txt`) — crypto 26 coins, 12 months, honest
Depth x1 / 1.25 / 1.5 / 2 with exit at the EMA or EMA - 0.5 ATR: £500 -> £325-369, worst falls -28% to -38%, both halves negative in every
variant. Reclaim entry (buy the close after a wick through the band): £500 -> £51. Band-movement-adjusted bids: £333. FAILED.

## Market search 1 (`src/market_search_1.py`, `runs/market_search_1.txt`) — honest fixed rules, costs, halves
Opening-range breakout (first 30 min, 2R): negative or flat on US Tech 100, US 500, Wall Street, Germany 40, FTSE, gold NY, GBP/USD,
USD/JPY and 7 crypto coins. Exception: gold London session n120 (~230/yr) +0.07R, H1 +0.08 / H2 +0.06 — WEAK (7 months of data).
Spike CONT on crypto (7 coins, 5 years, UTC day and US hours): FAILED everywhere. Spike CONT Wall Street n17 +0.43R both halves — WEAK (few).

## Spike engine recheck — the doc 191 numbers counted overlapping trades
The doc 191 test booked every signal even while a previous spike trade was still open (e.g. three on 29 Jan). Live can hold one per market.
Matched trade for trade, one at a time: US Tech 100 2025-26 **+0.05R n31** (doc 191: +0.19R n40); US 500 **+0.10 to +0.17R n22-23**
(doc 191: +0.27R n34); US Tech 100 2020-21 +0.46R n40 but H1 -0.32 / H2 +1.25. Verdict: WEAK. Stays live at IG minimum stakes only as
a real-fill measurement; not a candidate for sizing up until real fills say otherwise.
