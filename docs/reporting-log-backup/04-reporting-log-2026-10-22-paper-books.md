# Reporting log — paper books daily run — 2026-10-22

Simulated ledger only. CAP-021 honoured in full: no live order, no brokerage or exchange
account, no credential, no committed capital. Nothing was opened and no key is held.

## Step 0 — kill switch

`pb_halt` row 1: `active=0`, flatten=1, no reason, no resume_after. Written to
`runs/HALT.json` as `{"active":0,"reason":"","flatten":1,"resume_after":null}`.
All seven books trading normally.

## Step 0a — investing crash alert

Newest alert in Drive folder *PA Operation > 01 Capital*:
**"CRASH ALERT — AMBER — 2026-10-16"**, dated 16 October 2026 (6 days old, inside the
30-day staleness limit). Level read as AMBER.

Action taken: **none**. AMBER requires no action. The kill switch was already inactive
and was left inactive — no tightening was warranted and no loosening is ever permitted
by an alert. Folder contained only that alert plus the protocol file; no newer file exists.

Alert content for the record: trend UP, US 10-year at edge (~5.1-5.3%), credit calm;
breadth at a 10-year low, regional banks -9% vs trend, UK 30-year gilt above 6%, US CPI
3.7%, oil ~$95. Fed-printing exit trigger not met.

## Step 0b — queued writes

`runs/pending_d1_2026-10-21.sql` applied in order, all five statements:

- three `ALTER TABLE pb7_equity ADD COLUMN` for `equity_v11`, `shadow_v11`, `closed_v11`
- finding 108 (Ignition v1: where it loses, and v1.1)
- rule 178 (Ignition v1.1: no entries 16:00-18:59 UTC, stop = max(45 pts, 1.5 x ATR20))

File removed from the repo and the deletion committed. No write-limit refusals today.

## The seven books

All started at $2,000. Figures are the books' own simulated equity.

| Book | Started | Equity | Day | Since start | Closed today | Open |
|---|---|---|---|---|---|---|
| Keltner v1 | 15 Oct | $2,015.69 | $0.00 | +$15.69 | 0 | 4 |
| Range v2.2 | 16 Oct | $1,952.72 | -$11.21 | -$47.28 | 58 | 0 |
| ETF v3 | 16 Oct | $2,006.49 | +$3.34 | +$6.49 | 18 | 27 |
| Death-cross short v1 | 18 Oct | $2,000.00 | $0.00 | $0.00 | 0 | 1 |
| Golden-cross long v1 | 19 Oct | $2,000.00 | $0.00 | $0.00 | 0 | 0 |
| Range v3 mid-target | 19 Oct | $2,043.23 | -$4.97 | +$43.23 | 64 | 1 |
| Ignition v1 (NQ) | 19 Oct | $2,059.86 | — (replayed) | +$59.86 | 6 total | 0 |

### Keltner v1

`ingest_daily.py` rebuilt `data_daily/` from Coinbase (403 USD products listed, 301 series
written, median history 3.9 years, 119 products with 4+ years). Universe 265 products,
0 new candles beyond what was already cached. Gate ON (index 0.461 vs 200-day mean 0.370).

3 signals, 2 taken (COOKIEUSD at 0.009225, MINAUSD at 0.0718), 1 dropped (CTXUSD — already
held since 16 Oct). Nothing closed. Four positions now open: CTXUSD (16 Oct),
BIGTIMEUSD (18 Oct), COOKIEUSD and MINAUSD (today).

### Range v2.2

27 products as expected. Closed 58 round trips and ended the day completely flat — no
open positions, which is unusual for this book and reflects the regime switch firing
across the universe. Exit reasons: regime 25, target sale 20, time cap 8, break 4, stop 1.

Worst two trips: STRKUSD short -4.43% (break), ZECUSD short -4.48% (stop). Best:
UNIUSD long +2.38%, ZROUSD long +2.35%, AVAXUSD long +2.04%.

### ETF v3

32 instruments. 18 trips closed, 27 positions carried overnight and into the weekend as
the spec allows. Exits: 11 target sales, 4 regime, 3 break. Best VXX long +1.43%,
worst UNG long -1.32%. Still the only book whose edge/timeframe combination has no
backtest — the forward record is the whole evidence base.

### Death-cross short v1

25 alts. Nothing closed on any day since it started four days ago. One short open on
ARBUSD since 20 Oct 12:00, with its time-matched shadow short on ICPUSD opened at the
same bar. Real $2,000.00, shadow $2,000.00, gap **$0.00** — no verdict available yet,
and none should be read into a book with zero closed trips.

### Golden-cross long v1

All 27 coins. Nothing open, nothing closed since it started. The confirmed-cross filter
(ribbon open > 0.5 ATR, close above EMA20, within 20 bars, BTC above its 4-hour EMA200)
has not been satisfied. Real $2,000.00, shadow $2,000.00, gap **$0.00**.

### Range v3 mid-target (vs Range v2.2)

The comparison is the point: **v3 $2,043.23 vs v2.2 $1,952.72 — gap +$90.51 to v3**, on
identical coins, switch, cooldown, ladder and stop, differing only in exiting every lot
at the mid EMA instead of the three-step scale-out. v3 gave back $4.97 yesterday while
v2.2 gave back $11.21, so the gap widened again. 64 trips closed, 1 open.
v3's exits skew heavily to the target sale (45 of 64) where v2.2's skew to the regime
switch — the mid-EMA exit is getting paid before the switch takes it away.

### Ignition v1 on the Nasdaq-100

Dukascopy served the missing Globex days; bars current to 2026-10-21 23:55 UTC.
The book replays from its start date every run, so its whole record is reproducible and
the shadow is re-drawn each time.

Real **$2,059.86**, shadow **$1,990.32**, gap **+$69.54**. 6 closed trips, no trade open.
Two trades on 21 Oct, both exited on the breakeven-moved stop: +72.71 pts and +0.74 pts
(at $2 a point, +$146.90 together). Yesterday's recorded real equity was $1,912.96, so
those two trades account for the whole move.

Both registered variants are at $2,000.00 with zero closed trips: the US-hours candidate
and v1.1 (live from today under rule 178).

## Consistent-winner comparison (doc 73: 53% win rate, 81% of P&L from top 5%)

Books past 50 closed trips:

| Book | Trips | Win rate | Top 5% share of gross profit |
|---|---|---|---|
| Range v2.2 | 324 | 46.6% | 24.7% |
| Range v3 mid-target | 195 | 76.4% | 15.4% |
| ETF v3 | 51 | 58.8% | 27.3% |

All three are a different shape from the Hyperliquid winners: far less concentrated in
outliers, and in v3's case a much higher hit rate. That is not yet evidence of a better
edge — these are grinding books with small average trips, and the winners' 81%
concentration is what pays for their drawdowns. Worth watching whether v3's 76% hit rate
survives a trending week.

## Step 4 — allocation

Not the 1st of the month. Skipped.

## Step 6 — memory saved

Commit `42997ab` "paper books 2026-10-22", 43 files, pushed to `main` on first attempt.
All seven state files, today's seven SQL files, `runs/HALT.json`, the refreshed
`data_15m_cache/` (27 coins) and `data_nq_cache/nq_5m.csv` are in the repo. Yesterday's
pending SQL file removed. Tomorrow's run will continue from here, not replay today.

## Notes for the Head of Capital

- Range v2.2 ending flat with 58 closes in a day is the widest regime-switch sweep the
  book has had. If that recurs, the 6-hour cooldown (doc 74) is doing a lot of work and
  may be worth measuring separately.
- Range v3's lead is now $90.51 on four days and widening on down days as well as up.
  It is early, but the direction has been one-way so far.
- Death-cross and Golden-cross have produced no closed trips in four and three days
  respectively. Neither has a readable result; if that persists past a fortnight the
  question is signal frequency, not edge.
