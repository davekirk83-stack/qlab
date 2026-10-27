# Paper books run — 2026-10-20

Simulated ledger only (CAP-021). No live order, account, credential or capital.

## Kill switch and crash alert
- `pb_halt`: active=0. HALT.json written as `{"active":0,"reason":null,"flatten":1,"resume_after":null}`.
- Newest crash alert: **"CRASH ALERT — AMBER — 2026-10-16"** (file dated 16 Oct 2026, 4 days old, within the 30-day staleness limit). Level AMBER → no action taken, no halt written.

## Queued writes (STEP 0b)
`runs/pending_d1_2026-10-18.sql` applied. Its early statements (pb4 tables, books rows, findings 150/151, rules 161/162) were already in D1 from a prior run and re-applied idempotently.

**Schema mismatch found.** Several statements named columns the live tables do not have:
- `rules(id,rule,source,date)` and `rules(id,d,rule,doc)` — live schema is `rules(id, rule, why, doc, added)`.
- `findings(id, d, title, detail, status, doc)` — live schema is `findings(doc, title, date, verdict, superseded_by, summary)`.

The same text was written to the correct columns (source/d → doc and added; detail → summary; status → verdict) rather than dropping the record. **The SQL generator in `src/` should be corrected so future queued files apply verbatim.** File removed from the repo after applying.

## Book results (all started at $2,000)

| Book | Started | Equity | Day | Closed today | Open | Since start |
|---|---|---|---|---|---|---|
| Keltner v1 | 15 Oct | $2,015.69 | $0.00 | 0 | 2 | +$15.69 |
| Range v2.2 | 16 Oct | $2,009.08 | +$42.17 | 35 | 15 | +$9.08 |
| ETF v3 | 16 Oct | $1,997.51 | −$0.08 | 3 | 18 | −$2.49 |
| Death-cross short v1 | 18 Oct | $2,000.00 (shadow $2,000.00) | $0.00 | 0 | 0 | gap $0.00 |
| Golden-cross long v1 | 19 Oct | $2,000.00 (shadow $2,000.00) | $0.00 | 0 | 0 | gap $0.00 |
| Range v3 mid-target | 19 Oct | $2,066.37 | +$66.37 | 59 | 1 | +$66.37 |
| Ignition v1 (NQ) | 19 Oct | **did not run** | — | — | — | — |

- Keltner v1: gate ON (index 0.450 vs 200d mean 0.367), 0 signals. Open: CTXUSD (16 Oct), BIGTIMEUSD (18 Oct).
- ETF v3 closes: UNG long on regime (−0.53%), CPER long sold at target (+0.34%), XLU short on regime (+0.14%).
- Death-cross and Golden-cross: no qualifying setup since registration; real minus shadow is exactly zero, so no evidence either way yet.

### Range v3 vs Range v2.2
Raw equities are not comparable (v3 started three days later). On **the one day both books covered**, v3 +$66.37 against v2.2 +$42.17 → **v3 ahead by $24.20**. One day; the test needs 300 trips each.

## Shape check at 50+ closed trips (doc 73 benchmark: 53% win / 81% top-5% share)

- **Range v2.2 — 207 trips: win rate 47.8%, top 5% of trips (11 of 207) carry ~498% of all P&L.** Sum of returns across all trips is +0.0665; the top 11 alone sum to +0.3317. Median trip is negative. This is the exact pattern **rule 166** rejects ("top 5% carrying more than 100% of P&L and a negative median trade is not a book for this mandate, whatever its t-statistic"). Flagged for the Head of Capital; no change made to the book — amending a running book's spec is not authorised here.
- **Range v3 — 59 trips: win rate 96.6%, top 5% (3 of 59) carry 11.7% of P&L** (+0.0516 of +0.4425). Healthy shape, but only one day old.

## Ignition v1 failure — root cause

`data_nq_cache/` is **not in the repository**. `.gitignore` contains `data*/` and `*.csv` with an exception only for `data_15m_cache/*.csv.gz`, so `data_nq_cache/nq_5m.csv` has never been committable — and because STEP 6's `git add` runs with `2>/dev/null`, the omission was silent.

With an empty cache, `paperbook7.py` began rebuilding the full 12 months from Dukascopy: it pulled 2025-10-15 (255 bars) and was still on the next day 17 minutes later — roughly **70 hours** for a year of Globex days. Actions taken:
- Stopped the run.
- `runs/paper7_state.json` left untouched (started 2026-10-19, equity $2,000). No fresh state file created, no D1 row written, no figure invented.
- Added a `.gitignore` exception for `data_nq_cache/` so the cache persists once it exists.

**Still needed:** a one-off seeding run (or the cache supplied directly) to build `data_nq_cache/nq_5m.csv` before the book can report. Until then the Ignition forward record does not advance. Decision for the Head of Capital — note that the book replays from its start date every run, so its record is not corrupted by the gap, only paused.

## Allocation
Not the 1st of the month — STEP 4 skipped.

## Commit
`3558300 paper books 2026-10-20` — pushed to `davekirk83-stack/qlab` successfully. Includes six state files, six SQL files, HALT.json, the 27 updated 15-minute caches, the `.gitignore` fix, and the removal of the applied pending file.
