# Reporting log — paper books daily run — 2026-10-23

Simulated ledger only. CAP-021 honoured in full: no live order, no brokerage or exchange
account, no credential, no authentication, no committed capital. Nothing was opened and
no key is held.

## Step 0 — kill switch

`pb_halt` row 1: `active=0`, `flatten=1`, no reason, no resume_after. Written to
`runs/HALT.json` as `{"active":0,"reason":"","flatten":1,"resume_after":null}`.
All eight books trading normally.

## Step 0a — investing crash alert

Newest alert in Drive folder *PA Operation > 01 Capital*:
**"CRASH ALERT — AMBER — 2026-10-16"**, dated 16 October 2026 (7 days old, inside the
30-day staleness limit). Level read as AMBER.

Action taken: **none**. AMBER requires no action. The kill switch was already inactive and
was left inactive — no tightening was warranted and an alert may never loosen or clear a
halt. The folder contains only that alert plus the protocol file; no newer file exists.

Alert content for the record: trend UP (S&P ~7,780 above its 10-month average ~7,050-7,100),
US 10-year at edge (~5.1-5.3%), credit calm; breadth at a 10-year low, regional banks -9%
vs trend, UK 30-year gilt above 6%, US CPI 3.7%, oil ~$95 after a Hormuz mine incident.
Fed-printing exit trigger not met.

## Step 0b — queued writes

`runs/pending_d1_2026-10-22.sql` applied: one statement, finding 112 (liquidation cascades
via the OI proxy — no signal). File removed from the repo and the deletion committed.
No write-limit refusals today.

## The eight books

All started at $2,000. Figures are the books' own simulated equity.

| Book | Started | Equity | Day | Since start | Closed today | Open |
|---|---|---|---|---|---|---|
| Keltner v1 | 15 Oct | $2,015.69 | $0.00 | +$15.69 | 0 | 4 |
| Range v2.2 | 16 Oct | $1,941.71 | -$11.01 | -$58.29 | 21 | 14 |
| ETF v3 | 16 Oct | $1,989.79 | -$16.70 | -$10.21 | 30 | 9 |
| Death-cross short v1 | 18 Oct | $2,000.00 | $0.00 | $0.00 | 0 | 3 |
| Golden-cross long v1 | 19 Oct | $2,000.00 | $0.00 | $0.00 | 0 | 0 |
| Range v3 mid-target | 19 Oct | $2,039.77 | -$3.46 | +$39.77 | 34 | 2 |
| Ignition v1 (NQ) | 19 Oct | $2,372.90 | +$313.04 | +$372.90 | 12 total | 0 |
| Range v3-IDX (IG) | 23 Oct | $2,003.88 | +$3.88 | +$3.88 | 7 | 1 |

### Keltner v1

`ingest_daily.py` rebuilt `data_daily/` from Coinbase (403 USD products listed, 301 series
written, median history 2.7 years). No signals, nothing taken, nothing dropped, nothing
closed. Four positions still open: CTXUSD (16 Oct), BIGTIMEUSD (18 Oct), COOKIEUSD and
MINAUSD (both 22 Oct). Equity unchanged for the sixth day running.

### Range v2.2

27 products as expected. 21 trips closed, 14 positions open. Exits: regime 12, target sale
7, break 1, time cap 1. Best ARBUSD long +1.90%, AEROUSD long +1.47%, DOTUSD long +1.46%.
Worst DOTUSD short -3.40% (stop/break), LINKUSD short -1.92%, INJUSD short -1.84%.
The pattern of the day was a long-side ladder paying out around 00:00-02:00 UTC and the
short side then being taken out by the regime switch.

### ETF v3

32 instruments. 30 trips closed, 9 carried. Exits: break 21, target sale 6, regime 3 — the
heaviest break count the book has had, and the reason it gave back $16.70. Best SLX short
+2.10%, XME short +1.46%, XLB long +1.22%. Worst SLV long -2.30%, FXI long -1.82%,
SLX long -1.74%. Metals and miners cut both ways on the same day. Still the only book whose
edge/timeframe combination has no backtest — the forward record is the whole evidence base.

### Death-cross short v1

25 alts. Nothing closed on any day since it started five days ago. Three shorts now open,
each with its time-matched random shadow short at the same bar. Real $2,000.00, shadow
$2,000.00, gap **$0.00** — no verdict available, and none should be read into a book with
zero closed trips.

### Golden-cross long v1

All 27 coins. Nothing open, nothing closed since it started. The confirmed-cross filter
(ribbon open > 0.5 ATR, close above EMA20, within 20 bars of the cross, BTC above its
4-hour EMA200) has not been satisfied once in four days. Real $2,000.00, shadow $2,000.00,
gap **$0.00**.

### Range v3 mid-target (vs Range v2.2)

The comparison is the point: **v3 $2,039.77 vs v2.2 $1,941.71 — gap +$98.05 to v3**, on
identical coins, switch, cooldown, ladder and stop, differing only in exiting every lot at
the mid EMA instead of the three-step scale-out. v3 gave back $3.46 against v2.2's $11.01,
so the gap widened again (from +$90.51 yesterday). 34 trips closed, 2 open. Exits: target
sale 23, regime 10, break 1 — against v2.2's regime-dominated 12. The mid-EMA exit keeps
getting paid before the switch takes the position away; that is the whole of the difference.

### Ignition v1 on the Nasdaq-100

Dukascopy served the missing Globex day; bars current to 2026-10-22 22:55 UTC. The book
replays from its start date every run, so the record is reproducible and the shadow is
re-drawn each run.

Real **$2,372.90**, shadow **$2,011.34**, gap **+$361.56**. 12 closed trips, win rate 92%,
no trade open. Six trades on 22 Oct, every one exited on the breakeven-moved stop: +92.16,
+59.36, +3.29, +0.74, +0.49 and +0.48 points — at $2 a point, +$313.04, which is the whole
of the day's move. The two large ones were the 16:30 and 14:25 UTC entries.

Registered variants from the same replay:

- US-hours candidate (IG): real $2,304.98, shadow $2,146.44, gap **+$158.54**, 4 closed.
- v1.1 (doc 108, live from 22 Oct — no 16-18 UTC entries, stop max(45, 1.5 ATR)):
  real $2,119.68, shadow $2,093.40, gap **+$26.28**, 2 closed.

Note the tension worth watching: v1.1's 16-18 UTC exclusion would have skipped the 16:30
entry that produced +92.16 points. One day is not evidence either way, but the rule's cost
side is now visible.

### Range v3-IDX on IG's index markets — first recorded day

The Range v3 engine unchanged on Wall Street and Germany 40 (all hours) and US Tech 100
(New York hours only), at IG spread-bet costs. All three instruments current to yesterday:
Wall Street and Germany 40 to 2026-10-22 23:45 UTC (15-min bars), US Tech 100 to
2026-10-22 22:45 UTC.

Real **$2,003.88**, shadow **$1,998.79**, gap **+$5.09**. 7 episodes closed — Wall Street 1,
Germany 40 1, US Tech 100 5 — and one Wall Street long open. The two index legs both lost
small (Wall Street long -0.14% on the regime switch, Germany 40 long -0.35% on a break);
all five US Tech 100 episodes were winners, four on the mid-EMA target sale and one on the
regime switch. On seven trips this is a starting reading, not a result.

Data note: the Germany 40 Dukascopy pull stalled for roughly 20 minutes (the agent proxy
logged repeated `ws_closed_mid_exchange` failures against `datafeed.dukascopy.com`) before
completing inside its 25-minute subprocess budget. No retry was issued. Gold (XAUUSD) is
cached in `data_ig_cache/` but is not in this book's traded set.

## Consistent-winner comparison (doc 73: 53% win rate, 81% of P&L from top 5%)

Books past 50 closed trips:

| Book | Trips | Win rate | Top 5% share of gross profit |
|---|---|---|---|
| Range v2.2 | 345 | 46.1% | 24.6% |
| Range v3 mid-target | 229 | 75.1% | 16.1% |
| ETF v3 | 81 | 50.6% | 33.4% |

Ignition v1 (12 trips) and Range v3-IDX (7 trips) are both below the 50-trip threshold.

All three measured books remain a different shape from the Hyperliquid winners: far less
concentrated in outliers. ETF v3's concentration rose from 27.3% to 33.4% as its break-heavy
day thinned the gross-profit base. Range v3's hit rate is holding at three-quarters while
its outlier dependence falls — the opposite profile to the winners, and the thing to keep
testing against a trending week rather than this chop.

## Step 4 — allocation

Not the 1st of the month. Skipped.

## Step 6 — memory saved

Commit `1dd99f3` "paper books 2026-10-23", 46 files, pushed to `main`. The first push was
rejected because the IG demo runner had pushed `114631b` (rule 179) in the meantime;
`git pull --rebase` then push succeeded on the retry. All eight state files, today's eight
SQL files, the refreshed `data_15m_cache/`, `data_nq_cache/nq_5m.csv` and `data_ig_cache/`
are in the repo, and yesterday's pending SQL file is removed. Tomorrow's run will continue
from here, not replay today.

## Notes for the Head of Capital

- Ignition v1's +$361.56 gap over its shadow on 12 trips with a 92% win rate is the
  strongest reading any book has produced, but every single exit has been the
  breakeven-moved stop — the 9-ATR target has never been reached. The book is being paid
  by the breakeven mechanic, not by the thesis it was built on. Worth knowing before the
  go-live criteria (doc 93) are applied to it.
- v1.1's 16-18 UTC exclusion would have cost the single largest trade of the record. The
  rule was registered on two weeks of evidence; it now has one day against it.
- Range v3's lead over v2.2 is +$98.05 after five days and has widened every day, on down
  days as well as up. The mechanism is legible (target sale vs regime exit), which is the
  more useful fact than the figure.
- Death-cross (five days) and Golden-cross (four days) still have zero closed trips between
  them. As flagged yesterday, if this persists past a fortnight the question is signal
  frequency, not edge.
- The Dukascopy feed is becoming the slow step: the three index pulls took roughly 45
  minutes of wall clock today, one of them stalled. If Range v3-IDX is to run daily, the
  pull wants a shorter incremental window than 2026-04-15 onward.
