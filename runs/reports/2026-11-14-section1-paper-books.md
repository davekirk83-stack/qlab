# 197 — Section 1 paper books: 2026-11-14 run (all fourteen advanced)

CAP-021 unchanged and unbreached — simulated ledger only, no order path exists.
Full detail for this run is in the repo commit `103ef5b` (davekirk83-stack/qlab).

## Kill switch and crash alert

- `pb_halt` id=1: active=0. Nothing tightened. `runs/HALT.json` written to match.
- Crash alert: **"CRASH ALERT — AMBER — 2026-10-16"**, 29 days old, still the
  only file in PA Operation > 01 Capital. AMBER → no action.
- **LAST RUN INSIDE THE STALENESS WINDOW.** The file turns 30 days old on
  **15 Nov**. Rule (c) then makes it unreadable and rule (a) makes an unreadable
  level EXIT, so tomorrow's run must write `pb_halt active=1, flatten=1` and
  flatten every book for 14 days unless the investing side publishes a fresh
  status file first. Flagged in docs 130, 195, 196; now due.
- No `pending_d1_*.sql`. All SQL applied in full, including book 14's 794 trade
  rows (validated locally before sending).

## Books

| Book | Started | Equity | Day | Shadow | Gap | Open | Closed |
|---|---|---|---|---|---|---|---|
| 1 Keltner v1 | 15 Oct | $2,024.42 | −$65.43 | — | — | 12 | 2 |
| 2 Range v2.2 | 16 Oct | $2,190.47 | −$0.87 | — | — | 5 | 28 |
| 3 ETF v3 | 16 Oct | $1,897.60 | −$1.45 | — | — | 11 | 9 |
| 4 Death-cross short | 18 Oct | $1,970.08 | −$6.05 | $2,051.34 | **−$81.25** | 7 | 1 |
| 5 Golden-cross long | 19 Oct | $2,000.00 | 0.00 | $2,000.00 | $0.00 | 0 | 0 |
| 6 Range v3 mid | 19 Oct | $2,443.78 | +$4.64 | — | **+$253.31 v v2.2** | 3 | 34 |
| 7 Ignition v1 (NQ) | 19 Oct | $3,736.60 | +$1.46 | $1,902.86 | **+$1,833.74** | 0 | 1 |
| 8 Range v3-IDX | 23 Oct | $2,006.44 | −$4.96 | $2,000.86 | **+$5.58** | 1 | 5 |
| 9 AO saucer BTC/ETH | 27 Oct | $1,990.55 | 0.00 | $2,000.00 | **−$9.45** | 0 | 0 |
| 10 AO saucer v9.1 | 27 Oct | $2,000.00 | 0.00 | $2,000.00 | $0.00 | 0 | 0 |
| 11 MV pivots | 28 Oct | $2,000.00 | 0.00 | $2,000.00 | $0.00 | 0 | 0 |
| 11 EP pivots | 28 Oct | $1,979.39 | 0.00 | $1,997.93 | **−$18.54** | 1 COHR | 0 |
| 12 Daily retest | 1 Nov | $1,891.16 | −$22.02 | $1,913.05 | **−$21.89** | 0 | 1 |
| 13 Combined IG | 1 Nov | £468.76 | — | £509.68 alone | **−£40.92** | — | 10 |
| 14 Revolut X | 1 Nov | £530.36 | −£2.46 | £515.28 twin | **+£15.08** | — | 383 |

Key points. Book 1: gate OFF, no entries; JTO stopped −$36.60, VET timed out
−$28.84; worst day of the month, now only +$24.42 above its start. Book 4: the
random control is $81.25 ahead after 28 days — still has not earned its keep.
Book 5: 27 days with no confirmed cross taken (BTC below its 4h EMA200); v1.1
$1,924.10 v $1,933.88. Book 6: gap over v2.2 widened again on identical days;
v3.1 $2,466.24. Book 7: one NQ trade at breakeven, 56 closed, 84% win;
US-hours $2,582.54 v $2,024.18 (+$558.36), v1.1 $2,390.24 v $1,954.85
(+$435.39). Book 8: the single NQ trip (−1.47%) was the day's loss; Wall St 2,
DAX 2, NQ 1. Books 9/10: trend DOWN on all ten coins, no entries possible;
cloud variant $2,000. Book 11: 13 Nov processed (2,627 daily / 2,714 hourly),
no pivot qualified; cloud variants $2,000. Book 12: MUB stopped at −1.15R, now
flat with nothing open. Book 13: −6.2% from £500, which is also its max
drawdown; Ignition +£4.21, Range ladder −£35.45 (the whole loss, three trips at
−£12 to −£22), news £0; v2 £435.13 at −13.4% DD, £33.63 behind — the US 500 and
FTSE ladders are hurting. Book 14: max DD −3.8%; Revolut X's own prices worth
+£15.08 over the Coinbase twin.

## Past 50 closed trips (win rate / top 5% share of net P&L; benchmark 53% / 81%, doc 73)

Book 1 78 trips 82.1% / 171%. Book 2 1,234 51.0% / 154%. Book 3 297 41.1%, net
negative so concentration not meaningful. Book 6 1,473 75.8% / **42.8%** — the
healthiest in the stack. Book 7 54 85.2% / 57.7%. Book 8 80 66.3% / 172% (net
only +1.3%, so fragile). Book 14 383 72.1% / 52.7%.

## Housekeeping

Not the 1st, so no allocation. Committed `103ef5b` and pushed after a
`pull --rebase` (the IG demo runner had pushed e9acc93 meanwhile). The shallow
pre-seeded clone again reported a false "50 and 50 different commits" divergence
(graft artefact, as doc 196) — reset to origin/main, nothing lost. Dukascopy
transfers were cut off 23 times through the agent proxy; books 7, 8 and 13 each
retried and finished with caches current to 13 Nov, but the run took ~75 min.
