# 91 — The ladder is the edge, and one target beats three: Range v3 registered (19 Oct 2026)

Prompted by AuclairsDad's /CL room story (DK, 19 Oct 14:10: *"what gave this Algo its edge was the additional lots it scaled into at −12 and −17 pips before the hard stop at −26 pips, where target was +32 pips for all lots"*). Three sources now say the same thing about adds at worse prices — his /CL algo, the Hyperliquid consistent winners (doc 73: 6.2 adds per trip, half at worse prices), laddered fills (doc 65). The range book already ladders (15/25/30/30% at +0.30/+0.05/−0.25/−0.55 ATR). The question was whether his shape beats ours, and whether the three-step scale-out exit belongs on a mean-reversion book at all.

Code `src/range_scalein.py`, `range_scalein2.py`, `range_live_overlay.py`; logs `runs/range_scalein*.log`, `runs/range_live_overlay.log`. Registered 27-coin universe, 15-minute bars 2021-10 → 2026-10, both sides, chase fills, frozen containment medians, registered stop (close beyond the band by 1.5 ATR, switch off, 48 bars). Same entries in every row; only lot shape and target change.

## Results (per episode; simulator $2,000, 20 slots, 1×)
| ladder | eps | per ep | t | win | median | hold | CAGR 1× | maxDD | Sharpe | coins >0 | months >0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| registered v2.2 (4 bids, 3 asks) | 83,370 | +0.108% | 18.0 | 49% | −0.06% | 19 bars | +112% | −10.5% | 3.9 | 96% | 89% |
| registered bids, ONE target at the band | 86,502 | +0.185% | 25.4 | 49% | −0.13% | 16 | +323% | −12.8% | 5.6 | 100% | 95% |
| CL lots (⅓ at band / −0.7 / −1.0 ATR), target mid EMA | 103,462 | +0.162% | 40.7 | 66% | +0.45% | 4 | +421% | −8.4% | 7.6 | 100% | 98% |
| CL lots deeper (band / −1.0 / −1.3), mid | 103,462 | +0.142% | 35.9 | 65% | +0.43% | 4 | +325% | −8.8% | 6.9 | 100% | 97% |
| CL 4 lots (+0.3 / 0 / −0.7 / −1.0), mid | 139,503 | +0.188% | 58.7 | 72% | +0.46% | 4 | +1235% | −8.9% | 9.8 | 100% | 100% |
| **registered bids, ONE target at the mid EMA** | **139,503** | **+0.207%** | **62.8** | **72%** | **+0.49%** | **4** | +1634% | −9.4% | **10.3** | **100%** | **100%** |
| deeper 25%×4 (+0.3/0/−0.5/−1.0), registered asks | 83,370 | +0.104% | 17.8 | 49% | | | +680% (3×) | −28.5% | 3.9 | | |
| front-loaded 50/30/20 (+0.3/0/−0.5) | 83,370 | −0.007% | −1.2 | 48% | | | −40% (3×) | −93% | −0.6 | | |
| **single lot at the band, no adds** | 71,321 | **−0.108%** | **−16.6** | 45% | | | **blows up** | −100% | −4.2 | | |

By year for the winner: 2021 +0.270%, 2022 +0.202%, 2023 +0.135%, 2024 +0.232%, 2025 +0.243%, 2026 +0.205%; worst month +0.03%. Longs +0.179%, shorts +0.236%.

## What it says
1. **The adds ARE the edge.** One lot at the band with the registered exits loses −0.108% an episode and blows up; front-loading loses. Every shape that puts most of the size *below* the band earns. Doc 70's "execution is the strategy" was literal: there is no range-book entry edge without the ladder.
2. **A mean-reversion book wants one target at the mean.** Every ladder with a single mid-EMA exit beats the same ladder with the three-step scale-out, by a wide margin (t 18 → 63, hold 19 bars → 4, median trade from −0.06% to +0.49%, 89% → 100% of months). DK's scale-out design remains validated where it was validated — the *trend* book (ETF directional, docs 21–27); it is the wrong exit for the range book. The 20% left for band+0.35 and the 40% at the band mostly end up stopped or switched off.
3. **His lot shape is not better than ours.** CL-style equal lots are strong but the registered 15/25/30/30 bids with the mid target are the best row; the bids stay as registered.

## Live-window calibration (his step 14, monitor mode)
Backtest of v2.2 over the days the live book has traded (16–19 Oct): 162 episodes, −0.014%/ep, $2,000 → $2,002. The live book: 172 trips, $1,966.91. So the live book is tracking its backtest to within ~1.7% of friction — a flat week for the strategy, not a broken fill model. The mid-target variant over the same window: +0.028%/ep, $2,025.

## Decision
**Finding 161 — PROMISING, registered.** `Range v3 mid-target` (src/paperbook6.py, runs/paper6_state.json, D1 pb6_*) — identical to v2.2 in every respect except the exit: every lot leaves at the mid EMA. Started 19 Oct 2026 at $2,000, watermark run clean (27 products). Runs beside v2.2 (STEP 3d of the 07:23 task from 20 Oct); judged as v3 minus v2.2 on the same days; PASS if positive at 300 trips each. v2.2 is not changed.
**Rule 167:** on mean-reversion books the exit is one target at the mean; scale-out exits belong to trend books. A single lot with no adds is not the range book — never test the entry without its ladder.
Open: the ETF book (v3) carries the same scale-out; if Range v3 passes, an ETF mid-target twin is the next registration.
