# 86 — AuclairsDad on his own market: Nasdaq-100 (19 Oct 2026)

DK, 19 Oct: *"Why did you apply his method to coins and not to his actual markets?"* Fair. Doc 84 tested the book on 18 crypto perps because that is the data we held. This doc tests it where he trades it.

## Data
Dukascopy USATECHIDXUSD (Nasdaq-100 CFD) tick archive, **his three months, 15 Jul – 16 Oct 2026**: 25.7 million ticks → 86,283 one-minute bars, all hours including the overnight Globex session. Median quoted spread 1.43 points. Order-flow delta = the tick rule (uptick buy, downtick sell), the standard stand-in when the aggressor side is not recorded. Code `src/get_nq_ticks.py` (per-day checkpoints under `data_nq/days/`), `src/flow_nq.py`; log `runs/flow_nq.log`.

## The book, in his units (NQ points)
Score 0–5: 15-minute EMA20 vs EMA50 direction · side of the Globex-day VWAP · 15-minute delta z-score > 1.5 vs the trailing day · within 10 points of prior-day high/low, overnight high/low or VWAP · overnight session (22:00–13:30 UTC). Trade at score ≥ 4. **His management on every row:** stop 50 pts, half off at +20 and stop to breakeven, remainder trails 30 pts, 2-hour cap. Cost = half the quoted spread each way. Five random entries per trade with the identical management; entries also judged exit-free by the ±30-point barrier race.

## Result — the same answer as on crypto

| variant | n | pts/trade | t | win | PF | random ctrl | edge | race | ctrl |
|---|---|---|---|---|---|---|---|---|---|
| score ≥ 4 (his book) | 3,002 | −0.58 | −1.0 | 69% | 0.96 | −1.10 | +0.52 | 50% | 50% |
| score = 5 | 220 | −1.74 | −0.7 | 66% | 0.89 | −1.13 | −0.61 | 50% | 53% |
| delta off (other four ≥ 3) | 7,210 | −0.57 | −1.4 | 69% | 0.96 | −0.92 | +0.35 | 52% | 50% |
| delta only, overnight | 1,458 | −2.72 | −3.1 | 67% | 0.83 | −1.12 | −1.61 | 47% | 50% |
| delta + trend + VWAP, overnight | 531 | −1.43 | −1.0 | 69% | 0.90 | +0.34 | −1.77 | 50% | 53% |
| trend + VWAP + level, overnight | 2,376 | −0.49 | −0.7 | 69% | 0.97 | −1.20 | +0.72 | 51% | 49% |
| delta z > 2.5, overnight | 229 | −2.91 | −1.3 | 67% | 0.82 | +1.45 | −4.36 | 46% | 51% |
| delta z > 2.5 against trend (fade) | 114 | −5.49 | −1.6 | 62% | 0.70 | −1.21 | −4.28 | 43% | 51% |

By month for the full book: Jul +0.9, Aug −0.3, Sep −0.6, Oct −2.2 pts/trade. Exits: 62% breakeven, 27% stop, 11% cap.

Three things to read off it:

1. **His management reproduces his published statistics from random entries.** 67–69% win rate on every row, including the random controls — he posts 67.5%. The win rate is a property of a 20-point first target against a 50-point stop with a breakeven move, not of the entry. His PF 1.68 is the one number we cannot reproduce; ours is 0.83–1.05.
2. **Delta carries no forward information at this resolution.** The barrier race is 46–50% for every delta variant against 49–53% for random bars. Adding delta to the other four ingredients *lowers* the edge; the strongest delta signal (z > 2.5) is the worst row in the table. His "the delta didn't go off balance once, so no trades" is the thing that most looks like skill in his posts and it does not show up in the data.
3. **Nothing beats zero.** The best edge over random is +0.52 pts/trade (t ≈ 1) on 3,000 trades, which is less than the 1.4-point spread. The day-session row is positive (+0.83, 192 trades, t = 0.3) — noise.

## What this does not settle
Tick-rule delta on a CFD mid-price is a proxy for the futures footprint delta he reads; a CFD's quotes follow the future rather than lead it. Drawn levels are his, not an algorithm's. If his edge lives in discretionary level selection or in a true aggressor-side feed, this test cannot see it — but it tests every observable ingredient, in his market, in his window, with his management, and finds nothing. By rule 164 that is the bar.

## Decision
**Finding 156 — REJECTED on his own market as well.** The AuclairsDad book is closed on both panels. Nothing is transferred into ours except the lesson already taken (test an imported strategy on its own market first) and the reinforced rule 164: a posted win rate and profit factor describe the management, not the edge. The ingest scripts stay for any future order-flow question.

## Record
Data `data_nq/` (1-minute file + 82 daily checkpoints, in the repo). Finding 156 queued to D1 in `runs/pending_d1_2026-10-18.sql`. Paper books unchanged.
