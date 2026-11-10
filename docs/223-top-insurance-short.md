# 223 — Insurance short at new highs, valuation 'topping' filter, and the long-bear short on demo (10 Nov 2026)

DK 11:33 "Yes" (long-bear short to demo, refine further); 11:34 "The whole thing is overextended"; 11:35 "I am convinced we are about to enter a major
100 year crash like 1928 ... an insurance short with tight stop loss every time the S&P 500 makes a new high"; 11:36 "make today's updates to our live
book where refinements have been made"; 11:37 "tie some kind of short into a 'topping calculation' like the Buffett index".

## Live book — today's refinements are already live
The live runner runs the repo code + config/live_pot.json, so every pushed refinement applies from its next run: next-open dip books, TOM (monthly),
2 ATR stop fallback, TPS 5% stop counted in the day stop/floor with the 200-day restart, exceptions removed, risk tiers, the bear-regime rule (doc 220).
Live engines (config): RSI4, TPS, TOM, SANTA. TPSS and LBS are demo only.

## LBS (dormant long-bear breakdown short) on the demo — needs refining
Per market: 200-day lower than 60 days ago AND >= 15% below the 1-year high, close below the 200-day and the prior 20-day low -> short at the open;
exit close above the 10-day high, 60 days; stop 2 ATR. Replay of the demo runner 2020–26: 60 trades, −£264 at intended size (2022 −£238 across four
indices: many breakdowns that reversed). The 1928– S&P study's profit came from the 1930s/1970/2001–02/2008 bears; in a 2022-style bear it bleeds.
Next refinement: one position for the whole index group (not one per index), and a longer confirmation before entry.

## Insurance short at new highs (`src/top_short.py`, runs/gate/top_short.txt) — S&P 500 daily 1928–2026, next-close, IG spread, era funding
Valuation filter: Shiller CAPE above the 80th percentile of all EARLIER months (walk-forward). CAPE Sep 2023 30.8 vs threshold 22.4.
| Rule | n | mean ATR | win | total | worst year | 2007–08 | 2020 | 2022 | 1929 |
|---|---|---|---|---|---|---|---|---|---|
| T1 new 1-year high, stop 1 ATR, 20 days | 1014 | −0.211 | 17% | −214 | −54 | +19.4 | +36.8 | +13.8 | −0.4 |
| T2 same, stop 2 ATR | 727 | −0.351 | 25% | −255 | −56 | +16.6 | +40.4 | +7.4 | −0.3 |
| T3 T1 + CAPE expensive | 596 | −0.191 | 17% | −114 | −52 | +19.4 | +36.8 | +13.8 | −0.4 |
| **T4 new ALL-TIME high, stop 1 ATR, 20 days** | 630 | −0.112 | 18% | **−71** | −50 (1995) | +19.4 | +36.8 | +13.8 | −0.4 |
| T5 T4 + CAPE expensive | 488 | −0.176 | 17% | −86 | −50 | +19.4 | +36.8 | +13.8 | −0.4 |
| T6 new high + CAPE, ride up to 120 days | 615 | −0.275 | 25% | −169 | −46 | +11.2 | +14.7 | +5.0 | +0.8 |
- It behaves like an insurance policy: a small premium most years, a payout when a top turns into a crash. The CAPE filter does not help — the
  market was 'expensive' on 47% of days and stayed expensive for years (late 1990s, 2017–25).
- It did NOT catch 1929: each new high in 1929 was stopped out before the crash; what worked in 1929 was trend timing (doc 222: 10-month average) and
  the long-bear short.
- T4 in pounds on a £500 book: at 0.5% risk per trade, 99-year total −£176 (≈ −£1.80 a year), worst year −£126 (1995), payouts 2020 +£92,
  2007–08 +£49, 2022 +£35. At 1% risk everything doubles (worst year −£252).
- Buffett indicator (market cap / GDP): not tested — no long history reachable from here; CAPE is the long-run valuation measure we have (1881–2023).
