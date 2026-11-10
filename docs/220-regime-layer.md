# 220 — The regime layer (reviewer 2, section 4: "make the agent an intelligent portfolio manager") (10 Nov 2026)

DK 11:05 pointed out this section had not been addressed. `src/regime_layer.py`, runs/gate/regime_layer.txt, regime_bear_off.txt.

## Layer 1 — regime from completed data (US 500 + VIX at the signal close, fixed in advance)
SHOCK = VIX > 30 or US 500 −7% over 5 days · BEAR = US 500 below its 200-day · BULL-CALM = above, VIX < 20 · BULL-NERVOUS = above, VIX >= 20.

## Our live books by regime (result per trade at the signal; next-open execution, IG costs)
| Book | BEAR | BULL-CALM | BULL-NERVOUS | SHOCK |
|---|---|---|---|---|
| RSI(4) dip (ATR) | **−0.272** (n97) | +0.217 (791) | +0.609 (306) | +0.703 (68) |
| TPS ladder (% of budget) | **−0.099** (125) | +0.188 (1075) | +0.149 (299) | +0.570 (59) |
| Turn of month (ATR) | +0.152 (359) | +0.139 (1107) | +0.338 (220) | +0.313 (168) |
| Santa (ATR) | +0.415 (40) | +0.331 (115) | +1.135 (7) | +1.950 (12) |
Dip-buying works best when markets are frightened and worst when the US 500 is in a downtrend.

## Layer 2 — which books run, out of sample 2008–26
- Reviewer's rules as written (shock: nothing new; bear: dips off; nervous: TPS halved): lower totals for every book (RSI4 +303 -> +271,
  TOM +222 -> +151) — "suspend in a shock" removes the best trades. TPS risk-adjusted better (Sharpe 0.51 -> 0.64, worst 12m −44 -> −29) but −19% profit.
- Walk-forward weights per regime (learned from earlier years): RSI4 +303 -> +424 at 11% more average risk, Sharpe 0.88 -> 0.91 but worst 12m
  −54 -> −60; worse for TOM, TPS, Santa. Not adopted.
- **One rule: dip books (RSI4, TPS) take no NEW positions while the US 500 is below its 200-day** — RSI4 +303 -> +323 (Sharpe 0.88 -> 0.97),
  TPS +178 -> +189 (0.51 -> 0.57); TOM and Santa worse with it (they stay on). Walk-forward would have adopted it from 2008 (bear-regime dips
  already negative on earlier data). **ADOPTED** in `src/ig_daily_books.py` (demo and live): logged as "REGIME: …"; exits and open ladders unaffected.

## Layer 3 — already in place (docs 212–216)
Shared pot, account-wide 5x cap, 6% index risk cap, −4% day stop and −15% floor on the whole account incl. TPS, TPS 5% stop with 200-day restart,
risk tiers by pot size. Not adopted: "suspend new positions in a volatility shock" — shocks are the dip books' best regime.
