# 224 — DK's TradingView "Liquidations" indicator, rebuilt and tested on BTC (10 Nov 2026)

DK 15:41–15:47: his indicator ("Liquidations" by Mysterysauce, open source, 1000-bar volume average) called today's 72,850 BTC tap exactly; he bought the flush.
`src/liq_levels_test.py` (runs/gate/liq_levels_test.txt). Rebuilt from the published method: pivots 5 left / 2 right; pivot-bar volume vs its 1000-bar
average picks the leverage tier (100x > +20% ... 5x > +1.25%); LONG liquidation level = pivot low x (1 − 0.49 … 6.115%), SHORT level = pivot high x
(1 + 0.51 … 6.705%); a level is live from the pivot's confirmation until first touched. Binance BTC 1-minute 2020–Nov 2026 -> 15-minute bars;
fill AT the level (limit), 0.04% round-trip costs; random-bar drift for reference: 1h 0.000%, 4h +0.013%, 24h +0.117%.

## Buy when price taps a LONG liquidation level (DK's trade today)
| | n | 1h | 4h (t, win) | 24h | median worst dip within 4h |
|---|---|---|---|---|---|
| all | 9,253 | +0.064% | **+0.089% (t 4.57, 56%)** | +0.206% | −0.89% |
| 2020–22 | 4,376 | +0.108% | +0.132% (t 3.87) | +0.163% | −1.09% |
| 2023–26 | 4,877 | +0.024% | +0.050% (t 2.44) | +0.244% | −0.74% |
| 100x levels | 7,758 | +0.040% | +0.060% | +0.185% | |
| 50x | 814 | +0.059% | +0.124% | +0.568% | |
| 25x | 403 | +0.161% | +0.155% | −0.126% | |
| **10x** | 178 | +0.557% | **+0.636% (t 3.86, 66%)** | +0.561% | −1.04% |
| **5x** | 100 | +0.648% | **+0.769% (t 3.36, 62%)** | −0.438% | −1.00% |
Positive in both halves; the far, high-volume levels (10x / 5x — the biggest liquidation clusters) bounce most.

## Taps of SHORT liquidation levels — the squeeze runs ON
Selling at a short-liquidation level loses (4h −0.175%, t −10.2; both halves): when price reaches the shorts' stops it keeps going UP.
The mirror trade (buy as price breaks through short-liquidation levels) is ≈ +0.10% over 4h and +0.32% over 24h after costs — a squeeze-continuation idea.

## Next
Through the standard test (same-day clustering — many levels are hit together; walk-forward; Revolut X costs: limit 0%, taker 0.09%), exits (target /
stop / time), 5-min vs 15-min, and as a Revolut X dry-run book if it passes. Today's 72,850 tap is one of these events.

## DK 15:52: "the strongest buy signal would be a hit of the LOWEST level of liquidations — that direction cleared"
Each long-level tap classed by how many live long levels remain below it (within 10%); one event per 15-min bar (runs/gate/liq_levels_cleared.txt):
| Taps | n | 1h | 4h (win) | 24h (win) | median worst dip within 4h |
|---|---|---|---|---|---|
| CLEARED (none left below) | 25 (all 2020–22) | +0.21% | **+1.05% (60%)** | +0.80% (60%) | −3.44% |
| 1–2 left below | 126 | +0.41% | +0.25% (66%) | +0.90% (65%) | −1.32% |
| 3+ left below | 4,911 | +0.18% | +0.22% (t 8.8, 60%) | +0.35% (57%) | −0.73% |
Direction supports DK's idea (the fewer levels left below, the bigger the bounce), but 'fully cleared' is rare (25 times in 7 years, crash days, with deep
dips first) — too few to prove alone. The practical forms: the deep, low-leverage tiers (10x +0.64%, 5x +0.77% over 4h) and 'few levels left below'.
To build next, with the standard test: a ladder that buys the deeper clusters in size (like TPS rungs), stop just below the last cluster.
