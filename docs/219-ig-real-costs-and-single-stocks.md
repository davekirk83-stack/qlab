# 219 — Standard test now uses IG's real spreads; single-stock research started (10 Nov 2026)

DK 10:55 "you inherently believe there is no way to find new areas of profit. That is your bias." 10:56 "Why is the test set higher than the
actual IG charges?" 10:57 "Seems arbitrary and counterproductive."

## Costs
The gate charged 0.02% per side on indices since the start — a safety margin never updated to IG's real spreads (about 3x IG's on the US 500).
Now the standard (`src/std_books.py`, IG_COST): ONE FULL IG SPREAD PER SIDE (≈ double IG's real round trip, as the buffer):
US 500 0.5 pt, US Tech 100 1 pt, Wall St 2.4 pt, Germany 40 1.4 pt, FTSE 1 pt, gold 0.3 pt (at today's levels). 1.5x check stays on top.
Funding stays at ~6%/yr (IG: benchmark + admin) — that one is real.
Re-run at IG costs (runs/gate/recost_ig.txt):
| Book | gate costs | IG costs |
|---|---|---|
| RSI(4) dip | +0.279, clustered t 4.07 PASS | +0.300, 4.36 PASS |
| Turn of the month (6) | +0.156, 2.47, 16/26 yrs WEAK | +0.181, 2.88, 18/26 yrs WEAK |
| Gold flight to safety | +0.129 FAIL | +0.165, CI above zero, 16/22 yrs — WEAK (fails only t and random) |
| Pre-FOMC drift | +0.081 FAIL | +0.099, CI above zero — FAIL only on the last 5 years (−0.054) |
| Bear-market dip | +0.021 FAIL | +0.035 FAIL |
(The TOM portfolio line in that file compares TOM with a core that already contains TOM — ignore it.)
Overnight trades were already re-tested at IG spreads in doc 208 and still fail — on funding, which is a real IG charge.

## Single shares — the area we haven't searched
Every idea so far used daily prices on ~20 index/commodity/FX markets. The best-documented anomalies live in single shares (short-term reversal,
post-earnings drift, end-of-day reversal), and IG offers spread bets on thousands of them. `src/get_stocks.py` + workflow `stock-data.yml`
(data only) download S&P 500 + FTSE 100 constituents, daily 2005–. Caveat: current constituents only (survivorship bias).

## Single-share results (`src/stock_books.py`, `src/stock_short.py`; runs/gate/stock_books.txt, stock_short.txt) — IG share costs 0.1%/side + funding
| Book (rules from the literature, next-open in/out) | n | mean ATR | clustered t | full years + | last 5y | verdict |
|---|---|---|---|---|---|---|
| S1 Connors stock RSI(2)<5 above 200-day | 42,690 | +0.031 (US +0.047, UK −0.050) | 1.21 | 14/21 | −0.003 | FAIL (x1.5 costs negative) |
| S2 our RSI(4) dip on shares | 63,777 | +0.050 (US +0.069, UK −0.051) | 1.88 | 15/21 | +0.002 | FAIL |
| S3 short-term reversal, 5 worst 5-day S&P shares | 12,611 | +0.022 | 1.23 | 13/21 | −0.003 | FAIL |
| S4 earnings-gap drift (gap up >= 5%, 2x volume, 20 days) | 5,761 | +0.188 (US +0.206) | 2.19 | 14/21 | +0.184 | WEAK — below random 20-day longs (+0.258): survivorship drift |
| S5 gap-down rebound (long, 5 days) | 2,990 | −0.161 | −3.46 | 6/21 | −0.051 | FAIL |
| S6–S8 gap-down SHORT (bad-news drift), 5/20 days | ~3,000–5,600 | −0.08 to −0.53 | | 3–5/21 | | FAIL (both sides lose: gaps are volatile, costs + survivorship) |
Conclusion: on large US/UK shares since 2005, at IG share spreads, the classic share anomalies are too small; the index versions remain far better.
Data caveat: today's index members only. Next if pursued: point-in-time constituents and true earnings dates.
