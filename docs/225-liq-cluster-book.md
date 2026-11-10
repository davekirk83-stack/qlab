# 225: LIQ, the BTC liquidation-cluster book (10 Nov 2026)

DK, 16:15: "It's not magic… and it can surely be put to use." At 16:16: "avoid holding positions during a CPI announcement."

This doc builds the doc-224 findings into a book and runs it through standard test v3. Costs are Revolut X's real fees: **maker 0%** on resting limit orders and **taker 0.09%** on market orders (checked on Revolut's own Revolut X page today), plus 0.05% slippage on market exits.

## Rules (best version)
- **Entry:** a resting limit buy at each live long-liquidation cluster that still has other live long clusters below it within 10%. Half the position fills at the cluster and half 1% lower, to allow for the normal pierce.
- **Skips:**
  - the previous 15-minute bar was toxic selling that was still accelerating;
  - BTC's previous daily close was **below its 200-day average** (the regime rule);
  - the bar falls in the **CPI blackout**, from 08:15 to 10:30 New York on CPI days. Any open position is also **closed before the 08:30 release**.
- **Exit:** a resting limit sell 3% above the cluster (maker, no fee), a stop 4% under the cluster (taker), or after 3 days (taker).

## Results (BTC 2020 to 7 Nov 2026)

**Without the 200-day rule, all 45 combinations failed.** I tried five target types, three stops and three holding periods, all with the CPI rule. Means were up to +0.14% a trade, but every version lost over the last 12 months and in 2022. Both were BTC bear markets: the same failure the index dip-buyers have below their 200-day.

**With the 200-day rule:**

| Version | n | Mean | Win | Clustered t | Year-block CI | Last 5y | Last 12m | Costs ×1.5 | Random 95th | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Target 3%, stop 4%, 3 days, all taps | 2,051 | **+0.229%** | 63% | 2.36 | [+0.02, +0.47] | +0.17 | +0.31 | +0.19 | +0.02 | **WEAK** |
| Same, one position at a time | 647 | +0.233% | 64% | 2.10 | [+0.06, +0.52] | +0.14 | +0.54 | +0.19 | +0.04 | WEAK |
| Target 3%, stop 3%, 3 days, one at a time | 718 | +0.231% | 59% | 2.54 | [+0.09, +0.48] | +0.15 | +0.53 | +0.19 | +0.02 | WEAK |
| Nearest short cluster, stop 4%, 3 days | 2,051 | +0.239% | 63% | 2.17 | [+0.01, +0.55] | +0.13 | +0.24 | +0.20 | +0.05 | WEAK |

**By year**, for target 3% / stop 4% / 3 days:

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| +0.69% | +0.39% | no trades (below the 200-day) | +0.27% | +0.07% | −0.14% | +0.56% |

**Verdict: WEAK.**
- The book passes every check except the strict multiple-testing bar: t\* 3.81 after 372 ideas. That bar is high partly because this round tried 55 versions.
- It beats random entries by a factor of about 10.
- It survives 1.5× costs.
- It is positive over the last 5 years and the last 12 months.
- On our rules, WEAK means **paper or dry run, not live money**. TOM and Santa went the same route.

## Right now
- BTC's daily close on 7 Nov was 75,868, against a 200-day of 73,240, so the book was **on**.
- Today's tap at 72,850 sits essentially *on* the 200-day: the level Cheds' tweet flagged.
- A daily close below about 73,200 would switch the book **off**.

## Next
- A Revolut X dry run, like coin TPS: 15-minute candles, live cluster levels, resting limits, no orders.
- The cluster volume comes from Binance-style taker volume. The dry run needs an exchange feed that GitHub runners can reach, and Revolut X's own volume needs checking first.

Scripts: `src/liq_book.py` (`grid`, `regime`). Output: `runs/gate/liq_book.txt`, `liq_grid.txt`, `liq_regime.txt`.

## Addendum: trade management (DK, 16:36: "should have taken profit on the bounce… instead out at B/E")

Each variant was run on the same 2,051 trades: target 3%, stop 4%, 3 days, with the 200-day, CPI and toxicity skips. Same-bar conflicts were resolved against us.

| Management | Mean | Win | Year-block CI | Verdict |
|---|---|---|---|---|
| A: as doc 225 | **+0.229%** | 63% | [+0.03, +0.46] | WEAK |
| B: stop to breakeven at +0.75% | +0.034% | 28% | [−0.07, +0.11] | FAIL |
| C: breakeven at +0.75% and half off at +1% | +0.041% | 66% | [−0.05, +0.12] | FAIL |
| **D: half off at +1% only** | +0.157% | **66%** | [+0.02, +0.30] | WEAK |
| E: breakeven at +0.5% | +0.040% | 22% | [−0.01, +0.08] | FAIL |
| F: breakeven at +0.75% and half off at +0.8% | +0.041% | 80% | [−0.05, +0.12] | FAIL |

**The breakeven stop kills the edge.** Moving the stop to breakeven cuts the average trade from +0.23% to about +0.03–0.04%. The bounce off a cluster usually comes back to the entry at least once before it runs to the target, and that is exactly what happened today. A breakeven stop takes the trade out at that retest and misses the run.

**A partial take-profit is the right way to bank something on the bounce.** Half off at +1% keeps the book at WEAK and lifts the win rate to 66%, at the cost of about 0.07% a trade on average. The remaining half keeps the original stop and target.

**Rule for the dry run:** take half off at +1% with a resting limit (maker, no fee). Keep the stop 4% under the cluster. **No breakeven stop.**

Script: `src/liq_book_be.py`. Output: `runs/gate/liq_book_be.txt`.

## Running: Revolut X LIQ book (10 Nov, 22:25)

The book is built as `src/revx_liq.py` and runs every 15 minutes via `.github/workflows/revx-liq.yml`, one minute after each bar closes.

| Item | Setting |
|---|---|
| Size | £50 a trade (10% of the £500 Revolut X book, CAP-021), one trade at a time |
| Entry | resting limit buys (maker, 0% fee) at the setup cluster and 1% lower |
| Exits | resting sells, half at +1% and the rest at +3%; stop −4%, market; 3-day limit, market |
| Filters | 200-day regime; CPI blackout (out before the 08:30 release) |
| Levels | from Coinbase 15-minute volume, with Revolut X as fallback |
| Not included | the toxicity skip (these feeds carry no taker buy/sell split) |
| Mode | **dry** by default. Live only when DK sets the repo variable `REVX_LIQ_LIVE_ENABLED` = `true`. Claude never sets it. |

**First runs:**
- 22:24: resting buys placed at 72,861 (a 100× cluster) and 72,132. That is the same area as DK's 72,850 level today.
- 22:25 (GitHub): ran clean from the saved state.
- Bench test: the whole cycle was simulated — fill, half off, target exit, then a new resting buy — and it behaved correctly.
