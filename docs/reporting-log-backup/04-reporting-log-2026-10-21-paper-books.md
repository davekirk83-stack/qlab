# Daily paper books — 21 October 2026

Simulated ledger only (CAP-021). Nothing opened, no account, no key.

## Gates
- **Investing crash alert: AMBER** — file "CRASH ALERT — AMBER — 2026-10-16" (16 Oct, 5 days old, inside the 30-day window). AMBER = no action taken.
- **Kill switch: OFF** — pb_halt active=0, no reason, no resume date. HALT.json written to match.
- **Queued writes:** 6 statements from runs/pending_d1_2026-10-20.sql (doc 101 and 105 findings, rules 176 and 177) applied to D1 in order; file removed from the repo.
- **Schema fix:** pb7_equity had no equity_us / shadow_us / closed_us columns, so yesterday's Ignition equity row was never written and today's failed. Added the three columns (ALTER TABLE ADD COLUMN) and applied today's row. 20 Oct is a gap in pb7_equity; the book replays from its start date each run, so no record is lost. No spec, universe, threshold or weight was touched.

## The seven books (all started at $2,000)

| Book | Started | Equity | Today | Since start |
|---|---|---|---|---|
| Keltner v1 (daily crypto) | 15 Oct | $2,015.69 | unchanged | +$15.69 |
| Range v2.2 (15-min, 27 coins) | 16 Oct | $1,963.93 | −$45.15 | −$36.07 |
| ETF v3 (15-min, 32 ETFs) | 16 Oct | $2,003.15 | +$5.63 | +$3.15 |
| Death-cross short v1 | 18 Oct | $2,000.00 (shadow $2,000.00) | flat | $0.00, gap $0.00 |
| Golden-cross long v1 | 19 Oct | $2,000.00 (shadow $2,000.00) | flat | $0.00, gap $0.00 |
| Range v3 mid-target | 19 Oct | $2,048.20 | −$18.17 | +$48.20 |
| Ignition v1 (NQ 5-min) | 19 Oct | $1,912.96 (shadow $2,070.70) | first closes | −$87.04, gap −$157.74 |

### Detail
- **Keltner v1** — one signal (CTX) seen and dropped by the filters, nothing taken, nothing closed. Two positions still open: CTX from 16 Oct, BIGTIME from 18 Oct.
- **Range v2.2** — 59 trips closed: 15 sold at target (avg +1.60%), 28 on a break (−1.14%), 13 on regime (−1.04%), 3 stopped (−2.90%). 11 open. The breaks did the damage.
- **ETF v3** — 26 trips closed: 9 sold (+0.72%), 15 on a break (−0.18%), 2 on regime (flat). 14 open, held overnight.
- **Death-cross short v1** — one short opened and still running; nothing has closed since the book started. Real and shadow both untouched, so no verdict yet.
- **Golden-cross long v1** — no entry qualified. Still a blank record.
- **Range v3 mid-target** — 72 trips closed: 48 sold at the mid EMA (+0.59%), 10 on a break (−2.07%), 13 on regime (−1.13%), 1 stopped (−4.48%). 2 open. **v3 minus v2.2 = +$84.27** — the mid-EMA exit is ahead of the three-step scale-out on identical signals.
- **Ignition v1** — bars to 20 Oct 23:55 UTC (current). Four trips closed, three of them winners; yesterday's two both ran to breakeven (+0.74 pts each) after the trail. Nothing open. **Real minus shadow = −$157.74** — the random time-matched control is beating the book. The US-hours (IG candidate) variant has not traded yet: $2,000 real, $2,000 shadow.

## The 50-trip lines (vs Hyperliquid consistent winners: 53% win / 81% of P&L in the top 5%)
- **Range v2.2** — 266 trips, win rate **46.6%**, top 5% (13 trips) = **23.9%** of gross winnings.
- **Range v3** — 131 trips, win rate **80.2%**, top 5% (7 trips) = **16.3%** of gross winnings.

Both are far less concentrated than the Hyperliquid winners: the profit is spread across many small trips rather than carried by a handful. v2.2's win rate is below their 53%; v3's is well above it.

## Allocation
Not the 1st of the month — skipped.

## Memory
Committed and pushed as `paper books 2026-10-21` (171d4fe). All seven state files, the seven SQL files, HALT.json and the 15-minute and NQ caches are in the repo.
