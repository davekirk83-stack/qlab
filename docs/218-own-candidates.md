# 218 — Claude's own book candidates (DK 10:51: "If you could create a new book of your own…")

Built around the gaps in the one edge we have (short-term snap-backs after sharp falls, mostly in stock indices), all through the standard test (doc 217).
`src/own_books.py` (runs/gate/own_books.txt), `src/vix_sizing.py` (runs/gate/vix_sizing.txt).

| Idea | Result | Verdict |
|---|---|---|
| Size RSI(4) by VIX (edge bigger after frightened sell-offs) | By band: VIX<15 +0.19, 15–20 +0.16, 20–25 +0.51, 25–30 +0.18, >30 +0.86 ATR. Since 2014: VIX>=20 +0.60 vs <20 +0.06; before 2014 no difference (+0.34 vs +0.32). Walk-forward sizing (bands chosen from earlier years only), 2008–26: two bands total +325 vs flat +283 but at 7% more average risk, Sharpe 0.77 vs 0.82, worst 12m −61 vs −55; five bands worse (+244). | No risk-adjusted gain — not adopted |
| Bear-market dip: RSI(4)<20 below the 200-day, 5 days | +0.021 ATR, clustered t 0.34, 11/26 years | FAIL |
| Pre-FOMC drift (Lucca & Moench 2015): US indices, close of the day before -> close of decision day | +0.081, 20/26 years, but clustered t 1.49 and last 5 years −0.071 (faded since publication) | FAIL |
| Gold flight to safety: US 500 −2% day -> gold 3 days | +0.129, 16/22 years, +13.5 in the core's 10 worst months, but does not beat random gold entries (+0.211) | FAIL |
Register now at idea #292.
