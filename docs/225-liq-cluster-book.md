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
