# 94 — Bulkowski's Encyclopedia against our pattern record (19 Oct 2026)

DK sent the full *Encyclopedia of Chart Patterns* (Bulkowski, 2nd ed., 2005; 53 chart patterns + 10 event patterns, 500 US stocks, daily bars, bull market 1991–96 and 2003–04, bear market Mar 2000–Oct 2002). Read: the Statistics Summary, the Glossary and Methodology, and the Results Snapshots of every chapter (96 snapshots tabulated). Compared with docs 38–40 (our pattern and candle work, 14 Oct). Text extracted to `/home/claude/bulkowski/book.txt` (container only; the book is DK's copy, not committed).

## How he measures — and why his numbers are upper bounds
- **Average rise** = breakout price to the *ultimate high* (the highest high before a 20% fall), with no stop. His own words: "an average of perfect trades… the likelihood of duplicating that in actual trading is zero."
- **Break-even failure rate** = share of patterns that fail to move 5% past the breakout. No stop, no time limit.
- **Percentage meeting price target** = how often the measure-rule target (pattern height added to the breakout) is reached before the ultimate high. **No stop** — so it is the ceiling on any "target before stop" hit rate.
- No random control anywhere. Bull-market figures carry the drift of the best decade in US equities.
So his tables are base rates, not expectancies. Our doc 39 method (each pattern's own target *and* stop, scored target-before-stop, against a random entry with the same reward-to-risk in the same instrument) is the stricter test, and the only one of the two that says whether a pattern *earns* anything.

## Where the two agree — closely
| pattern | Bulkowski: target met (bull, no stop) | ours (doc 39): target before stop, crypto | his failure rate | ours: edge over control |
|---|---|---|---|---|
| double bottoms (four variants) | 66–67% | 59–70% hourly/daily | 4–5% | +0.031R hourly, +0.076R daily |
| head-and-shoulders bottom | 74% | ~70% | 3% | +0.047R hourly, +0.064R daily |
| ascending triangle | 75% | positive, +0.045R | 13% | +0.045R |
| **flags** | 64% | **26%** at 2.3 R:R | 4% | **−0.199R** |

Three of four patterns give the same hit rates on 1990s US daily stocks and 2020s crypto hourly bars, with and without a stop. That is as good a replication as technical analysis gets: the detectors are finding the same animal, and the animal behaves the same way. His "failure rates climb fast" tables (26% of Adam & Adam double bottoms fail to rise 15%; half top out under 25%) are his version of our "high hit rate, thin economics" — the measure-rule target is modest, hits often, and pays modestly.

**Flags are the divergence, and it is instructive.** His flag target is the flagpole measured from the *flag low* to the *trend high* ("flags and pennants measure performance to the trend high or low, not the ultimate high"); ours projected the full pole from the breakout. His version hits 64%; ours 26%. So doc 39's "flags fail" is partly our target being too ambitious — but even his version has the lowest average rise of any bullish pattern (23%) and the highest sensitivity to throwbacks. Flags stay excluded from the scanner; a half-mast version with his target can be tested if there is ever a reason.

## What he has that we have not tested (bull market, up breakouts)
His own overall ranking (average rise + failure rate + change after trend ends): 1 high-and-tight flags (69% rise, 0% failure, 90% target met — rare), 2 pipe bottoms (45%, 5%, 83%), 3 ascending-and-inverted scallops, 4 three rising valleys (41%, 5%, 58%), 5 rounding bottoms and **descending triangles with an upward breakout (47% rise, 7% failure, 84% target met)**, then Eve & Eve double bottoms, triple bottoms, head-and-shoulders bottoms. **Rectangle bottoms**: 46% rise, 85% target met — the highest target-met rate of any common pattern, and it is the *range* shape our containment books already trade. **Descending-triangle up-breakouts** and **rectangles** are the two detectors worth adding to `patterns_proper.py`, tested exactly as doc 39 tests.

## His cross-cutting findings, as features for the scanner (each to be tested, not assumed)
1. **Throwbacks hurt.** Patterns whose price returns to the breakout before rising do markedly worse (Eve & Eve: 33% rise with a throwback vs 48% without; "throwbacks hurt performance" is his most repeated surprise). Implication: enter on the breakout, do not wait for the retest — which is doc 55/137's retest finding from the other side.
2. **Tall patterns outperform short ones** in nearly every chapter. Pattern height / ATR as a scanner feature.
3. **Bottoms that break out near the yearly low do best**; tops near the yearly high.
4. **Bear-market failure rates run two to four times bull-market ones** for bottoms. Our regime switches are the right answer to this; patterns are not a bear-market tool.
5. **Volume**: receding volume into the pattern and heavy breakout volume help in most chapters — the one place his finding disagrees with ours (doc 23: volume as an entry filter is harmful on daily crypto). Worth a direct test on the pattern population only.

## What changes
- Doc 39 stands, strengthened: an independent 500-stock, decade-long dataset gives the same hit rates for the three patterns we kept. The patterns paper tracker (restarted 18 Oct, 150 resolved trades to a verdict) is the right forward test and is unchanged.
- Research queue (behind the monitor-mode harness and the allocator): add rectangle and descending-triangle detectors; add height/ATR, throwback and yearly-position features to the confluence scanner; re-test flags with his half-mast target; test his volume findings on the pattern population. All with doc 39's method; nothing goes into a book without beating its matched control.
- Rule 170: an external pattern statistic without a stop and without a control is a base rate, not an expectancy; it can suggest a detector, never justify a trade.
