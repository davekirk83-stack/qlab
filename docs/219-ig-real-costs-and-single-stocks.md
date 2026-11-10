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
