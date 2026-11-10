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

## Addendum — toxic order flow (DK 10 Nov: "Yes please")

**What "toxic flow" means.** Market makers call flow *toxic* when the aggressive orders are mostly one way: someone is hitting bids (or lifting offers) relentlessly, usually because they know or are forced to do something. Liquidity providers lose money against it, so they pull their quotes, and price slides through levels faster. VPIN is the academic measure of it. We rebuilt a simple version from Binance BTC taker volume: on 15-minute bars, **toxicity = |net taker buy − sell| ÷ total volume over the last 3 hours**. Its percentile is taken against the previous 30 days, and "cooling" means it is lower than 45 minutes earlier.

**The test.** We took every tap of a long-liquidation level, 5,062 taps from 2020 to 2026, measured from the level and after 0.04% costs, and grouped them by the toxicity at the moment of the tap.

| At the tap | n | 4h | t | 24h |
|---|---|---|---|---|
| All taps | 5,062 | +0.227% | 8.45 | +0.367% |
| Toxic (top 20%, sellers), still accelerating | 1,657 | +0.226% | 4.38 | +0.303% |
| Toxic (sellers), cooling | 327 | +0.270% | 3.19 | +0.536% |
| Moderate | 1,939 | +0.227% | 5.38 | +0.354% |
| Calm | 1,129 | +0.211% | 3.92 | +0.439% |

By period:

| Period | Group | 4h | 24h |
|---|---|---|---|
| 2020–22 | All taps | +0.358% | |
| 2020–22 | Toxic + cooling | +0.473% | +1.02% |
| 2023–26 | All taps | +0.108% | |
| 2023–26 | Toxic + cooling | +0.116% (t 1.27) | +0.17% |
| 2023–26 | Toxic + accelerating | +0.046% | |

**Verdict.**
- Toxicity **does not usefully filter** liquidation-level taps. "Toxic and cooling" looks a little better over 1h and 24h, but only on 327 events, and the edge comes from 2020–22. In the recent period it is indistinguishable from simply taking every tap.
- The one consistent hint is to **avoid buying while toxic selling is still accelerating**. Those taps were the weakest group in 2023–26: +0.05% over 4h, about zero after real costs.
- That is a sensible "wait one bar" rule, not an edge on its own.
- The base finding still stands: taps of long-liquidation levels bounce, with t 8.45 on all taps. The bounce has shrunk a lot since 2022 (4h +0.36% → +0.11%), so it needs Revolut X's real costs and the standard test before any money goes near it.
- Script: `src/toxicity_test.py`. Output: `runs/gate/toxicity_test.txt`.

## Addendum 2: "once the last cluster in a region is gone, it reverses to the other extremity" (DK, 16:03)

**The test.** At every tap of a long-liquidation level on BTC (15-minute bars, 2020–26) I recorded two things:
- whether any long levels were still live below, within a region of 5% or 10%. If none were, the tap counts as **cleared**;
- the live **short**-liquidation levels above at that moment. The *nearest* one and the *farthest* one within the region are the targets.

The trade is a buy at the tapped level. It exits at the target, at a stop 1.5% or 3% below the level, or after 7 days, whichever comes first. Costs are 0.04%. Script: `src/liq_reversal_test.py`. Output: `runs/gate/liq_reversal_test.txt`.

**5% region:**

| Target | Stop | Taps | Hit target | Avg trade | 2023–26 |
|---|---|---|---|---|---|
| Nearest | 1.5% | Cleared, 111 | 32% | +0.06% (t 0.25) | −0.29% |
| Nearest | 1.5% | Levels still below, 3,961 | 39% | +0.10% (t 3.07) | +0.02% |
| Farthest | 3% | Cleared, 111 | 41% | −0.03% | +0.05% |
| Farthest | 3% | Levels still below, 3,961 | 40% | +0.19% (t 3.53) | +0.05% |

**10% region:**

| Target | Stop | Taps | Hit target | Avg trade |
|---|---|---|---|---|
| Farthest | 3% | Cleared, 21 (all in 2020–22) | 10% | −1.66% |
| Farthest | 3% | Levels still below, 4,915 | 20% | +0.34% (t 5.06) |

**Verdict: the data says the opposite.**
- When the last long cluster in a region is cleared, price reaches the short clusters above *less* often than usual, and gets stopped more.
- Cleared taps mostly happen inside liquidation cascades, the 2020–22 crash days, where the whole ladder gets blown through. That is not the exhaustion point.
- The better setting is a tap of an upper cluster *while there are still clusters below*. There the reversal toward the short clusters is the stronger result. With the farthest target and a 3% stop it is positive in both halves: 2020–22 +0.46%, 2023–26 +0.22%.
- **Candidate for the standard test:** buy the tap of a long level that still has live levels below, target the farthest short cluster within 10%, 3% stop, 7-day limit.
