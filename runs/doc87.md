# 87 — How might AuclairsDad's algo be doing it? Second and third passes on Nasdaq-100 (19 Oct 2026)

DK, 19 Oct 10:03: *"Don't close this guy's tick book. I want you to figure out how his algo is or might be doing it."* Book reopened as OPEN — PENDING DATA. Docs 84/86 tested the literal reading (delta imbalance, go with it, plus HTF trend) and it equals random on crypto and on NQ. These passes treat the edge as unknown and test every other reading that fits his numbers. Code `src/flow_nq2.py`, `src/flow_nq3.py`; logs `runs/flow_nq2.log`, `runs/flow_nq3.log`. Same data, management (stop 50 / half at +20 → BE / trail 30 / 2h cap), random controls and ±30-pt barrier race as doc 86.

## What his numbers imply
PF 1.68 at 67.5% win ⇒ average win ≈ 0.81 × average loss ⇒ roughly +7 to +8 pts per trade net. Per-trade SD under his management is ~30–35 pts, so 80 trades give t ≈ 2.0 — a real but thin record, on 11 days he chose to post. "Up 28% in 3 months" on one lot is consistent with that and with an account of roughly $40–60k. Nothing in his posts rules out a lucky quarter; nothing proves it either.

## Pass 2 — fade, divergence, our range logic (flow_nq2)
- **The overnight NQ at the minute scale is a random walk in his window.** Random entries with his management: barrier race 50% in every hour block, 1-minute autocorrelation within ±0.04. The geometry alone loses 0.6–2.3 pts/trade overnight; only 20:00–22:00 UTC (post-cash, pre-Globex) is positive and that is 1,890 bars of thin trading.
- **Fading the extreme is worse than random**: overnight H/L touch −2.52 (ctrl −0.89); prior-day H/L −1.72; VWAP ±30 stretch −2.26 (t −4.2); 240-min z −1.61. Adding "delta balanced" makes each worse. So "the delta didn't go off balance" is not "fade when quiet".
- **Cumulative-delta vs price divergence is the worst thing tested**: −3.5 pts/trade, t −6.7, race 46%.
- **Our range book on NQ overnight** (containment switch + Keltner touch): −1.25 vs ctrl −0.85. Does not transfer to this market at this scale — consistent with rule 152's limits (the range edge was shown on 15-minute and daily bars, not minutes).
- One cell with a pulse: **absorption** — heavy 15-minute delta while price does not move (sellers hitting, price holding → long): +1.56 pts, t 1.2, race 55% vs 52%.

## Pass 3 — night selection, session opens, slower delta (flow_nq3)
- **Night selection**: 66 nights, only 30% positive for the geometry; nothing known at 22:00 (prior-day range, close location, return, realised vol, weekday) separates good nights from bad; night-to-night autocorrelation +0.05. If he is picking nights, it is not on anything in the price series.
- **Opening-range breakouts** (22:00, 00:00, 07:00, 13:30): every go-with break loses; every fade is small-positive on n = 64–83 (t ≤ 0.8). Noise-level.
- **Slower delta**: 60-min delta go-with −2.49, fade +1.89 (t 1.2); 180-min the reverse. No stable sign.
- **Absorption, every cut**: any session +1.25 (n 917, t 1.1, race 54%); z>2 +1.66; overnight gap-30 +1.09. Same sign in every cut, but by month −2.8 / +2.3 / −0.1 / +4.1. Not a finding; the only lead.
- **Dukascopy tick sizes are zero** for the index CFD — there is no volume or book information in that feed at all. Our delta is purely the tick rule on the CFD mid.

## Where this leaves it
Everything observable in the price series has now been tested in his market, his window, his management: trend-following, fading, divergence, absorption, session opens, night selection, our own range logic. Nothing beats random with any confidence. The candidate explanations, ranked:

1. **His delta is real and ours is not.** He reads a CME footprint (aggressor-side trades, per price level). The tick rule on a CFD mid-price, with zero size data, is the weakest possible proxy — a CFD quote *follows* the future. Absorption is the footprint read most likely to survive a real feed, and it is the one cell with the right sign everywhere here. This is testable: CME trade data with aggressor side is sold per-GB by Databento (GLBX.MDP3, NQ/MNQ trades); three months of NQ trades is a small purchase. Alternatively the same absorption test can be run free on crypto with Binance 1-minute klines (`taker_buy_base_volume` is a true aggressor delta) — `src/ingest_binance_1m.py` is written and not run.
2. **Discretionary levels.** His purple lines are drawn by hand; an algorithm scoring "near a level" with mechanical levels is not the same input.
3. **A thin record.** 80 trades at t ≈ 2 on selected days. He may be good; the posts cannot show it.

## Decision
Finding 157: **OPEN — PENDING DATA.** Not rejected, not a candidate. Absorption (heavy delta, no price progress) is the lead; it needs a true aggressor-side feed to be tested properly. Two routes, DK to choose: (a) buy three months of CME NQ trades with aggressor flags (his market, small cost, research-only data — not an account); (b) run the free Binance taker-volume ingest and test absorption on 18 perps first. Nothing changes in the paper books.
