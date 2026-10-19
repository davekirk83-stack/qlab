# 96 — His ordering, tested: the range book earns most buying the pullback of a fresh ignition (19 Oct 2026)

AuclairsDad's four-algo sequence (via DK, 19 Oct): "(1) delta algos start the trend, (2) momentum joins, (3) range-break algos activate once momentum has caught, (4) mean reversion buys where the other three take profit." Test: does an ignition bar (his type-3 trigger — 15-minute bar range ≥ 1.25× the prior 20, |taker delta share| ≥ 0.05, direction = sign of delta, from the Binance true-delta panel) shortly before a Range v3 episode change what that episode earns? Code `src/timing_test.py`; log `runs/timing_test.log`. 14 coins with true delta, 17,683 Range v3 episodes, Sep 2025 – Sep 2026.

| bucket (ignition within K bars before entry) | n | per ep | t | win | coins > 0 |
|---|---|---|---|---|---|
| all episodes | 17,683 | +0.144% | 19.3 | 71% | 100% |
| K=4: ignition WITH the trade (up-ignition, then we buy the dip) | 1,721 | **+0.236%** | 9.9 | 74% | 100% |
| K=4: ignition AGAINST the trade (down-ignition, then we buy the low) | 5,907 | **+0.099%** | 7.2 | 70% | 93% |
| K=4: none | 8,220 | +0.146% | 14.2 | 71% | 100% |
| K=12: with / against / none | 2,296 / 5,044 / 3,280 | +0.201% / +0.115% / +0.095% | 10.2 / 8.1 / 6.2 | | |
| K=24: with / against | 1,420 / 2,632 | +0.186% / +0.106% | 8.2 / 5.8 | | |
| long side, K=12: against / none | 2,822 / 1,686 | +0.091% / +0.033% | 4.8 / 1.5 | | 93% / 64% |
| short side, K=12: against / none | 2,222 / 1,594 | +0.146% / +0.161% | 6.8 / 7.8 | | |

## Reading
I had his sentence backwards. "Buys where the other three take profit" does not mean fade the breakout; it means **buy the pullback after the breakout has run and the momentum algos are taking profit**. The range book's best trips are exactly those — an up-ignition, then a dip to the lower band, then the bid fills — at 2.4× the per-trip return of standing in front of a fresh down-ignition. The worst thing the book does is buy a low that a down-ignition has just made (long side, +0.09%; with no flow information at all the long side earns only +0.03%). Shorts care less: the short side is strong in every bucket, which fits everything since doc 68 (crypto short-side range trades are the better half).

## What it is not
A split of one book's episodes, not an out-of-sample test, and the ignition detector is his read of a 15-minute bar on 14 coins — not a new signal. The lift (+0.1pp per trip on a +0.144 base) is large but the buckets overlap in time and coin; monitor mode is the right next step.

## Decision
Finding 164 — PROMISING, monitor mode. A timing clause for the range books: **flag any entry whose last 12 bars contain an ignition against its direction; log what the book would have done with that entry skipped or halved**, against the live v2.2/v3 record, for four weeks, before any registered book carries it (his step 14; rule 172). Nothing changes in the running books. The first thing the monitor-mode harness (next in the queue) will carry.
