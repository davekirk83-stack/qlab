# Reporting log — 21 Nov 2026 — Section 1, fourteen paper books

Simulated ledger only (CAP-021). No live order, no account, no credential, no capital.
NOTE: this log could not be written to the Claude project — the project is at its maximum
size and refused the write. Kept here in the repo instead.

## Safeguards

- Investing crash alert: AMBER. Newest file in PA Operation > 01 Capital is
  "CRASH ALERT — AMBER — 2026-10-16" (the 16 Oct baseline), 36 days old. Under the rule DK
  changed on 16 Nov, age does not make a file unreadable — the crash watch only files a new
  alert when the level changes — so the level stands and no action was taken. Flagged because
  it is past 30 days.
- Kill switch: OFF. pb_halt active=0, cleared 16 Nov by DK's decision after the stale-file EXIT.
  All fourteen books traded normally. HALT.json written to match.
- No queued pending_d1_*.sql files were waiting.
- Repo note: origin/main had been force-updated since this container last synced (local HEAD was
  18 Nov). Reset to origin/main, confirmed on branch main before running. All twelve state files
  present with their "started" dates — none missing, none recreated.

## The books

| # | Book | Today | Yesterday | Since start |
|---|---|---|---|---|
| 1 | Keltner v1 | $1,681.87 | $1,909.85 | -$318.13 |
| 2 | Range v2.2 | $2,305.27 | $2,355.53 | +$305.27 |
| 3 | ETF v3 | $1,848.60 | $1,877.15 | -$151.40 |
| 4 | Death-cross short | $2,583.48 | $2,583.48 | +$583.48 |
| 5 | Golden-cross long | $2,000.00 | $2,000.00 | flat |
| 6 | Range v3 mid-target | $2,716.51 | $2,739.78 | +$716.51 |
| 7 | Ignition v1 (NQ) | $4,565.68 | $4,578.96 | +$2,565.68 |
| 8 | Range v3-IDX | $1,994.33 | $2,001.71 | -$5.67 |
| 9 | AO saucer BTC/ETH | $1,990.55 | $1,990.55 | -$9.45 |
| 10 | AO saucer v9.1 (10) | $2,000.00 | $2,000.00 | flat |
| 11 | Stock pivots MV / EP | $2,000.00 / $1,996.32 | same | flat / -$3.68 |
| 12 | Daily retest | $1,891.16 | $1,891.16 | -$108.84 |
| 13 | Combined IG (GBP500) | GBP467.50 | — | -GBP32.50 |
| 14 | Revolut X (GBP500) | GBP552.49 | GBP554.45 | +GBP52.49 |

### Detail

- Book 1 lost $227.98 — its last six positions all closed at once (five stops: RLC, ARKM, ORCA,
  TOSHI, DOT; one 30-day time cap: ALT). Completely flat now, trend gate still OFF.
- Book 2 closed 34 episodes: 8 sold at target (+13.5% of return summed), 17 regime, 7 break,
  2 stopped. Flat overnight.
- Book 3 closed 19 (5 sold, 7 regime, 5 break, 2 stop) and holds 7: USO and UNG short, XLE, DBA,
  CORN, UUP and FXE long — all opened 20 Nov.
- Book 4: real $2,583.48 vs shadow $2,242.37 — gap +$341.11. No entries, nothing open.
- Book 5: still has never taken a confirmed golden cross (0 closed); real and shadow both
  $2,000.00, gap $0. v1.1 variant $1,924.10 vs shadow $1,933.88 — gap -$9.79 on 4 trips.
- Book 6 vs Book 2: $2,716.51 against $2,305.27 — mid-target is +$411.24 ahead; that gap is the
  result. Its own v3.1 variant is $2,783.96, i.e. v3 is $67.44 behind v3.1.
- Book 7: real $4,565.68, shadow $1,724.04, gap +$2,841.64, nothing open, 71 closed at an 83%
  win rate. Yesterday: +84.6 points trailed out at breakeven, then two stops (-45.7, -45.5),
  net -6.6 points. Variants: US-hours $3,172.08 vs shadow $2,069.80 (gap +$1,102.28); v1.1
  $2,927.90 vs shadow $1,948.86 (gap +$979.04). Bars current to 20 Nov 21:10 UTC.
- Book 8: real $1,994.33, shadow $1,999.99, gap -$5.66. Three episodes closed — Wall Street 1
  (+0.39%), Nasdaq 2 (+0.69% sold, -2.56% regime), Germany 40 none. All bars current to 20 Nov.
- Book 9: real $1,990.55, shadow $2,000.00, gap -$9.45. BTC and ETH both trend DOWN, nothing
  open, no saucer signal.
- Book 10: real and shadow both $2,000.00 (gap $0, still no trade since 27 Oct). All ten coins
  trend DOWN, nothing open; $9.45 ahead of book 9 purely by staying out. Cloud variant $2,000.00.
- Book 11: MV real $2,000.00 / shadow $2,000.00 (gap $0, 0 trips). EP real $1,996.32 / shadow
  $1,985.43 (gap +$10.89, 7 trips). Nothing open; both cloud variants $2,000.00. Yahoo gave
  2,630 daily and 2,717 hourly stocks — no throttling — and the 20 Nov session was processed.
- Book 12: real $1,891.16 unchanged, shadow $1,873.73 (shadow lost $19.81 on an EWJ trade stopped
  at -1.05R). Gap +$17.43. Still holding TLT and IEF; nothing real opened or closed. Data
  complete: 27 coins, 60 ETFs.
- Book 13 (GBP500 pool): GBP467.50, max drawdown -7.7%, 16 closed. Ignition +GBP19.46 (4 trips),
  Range ladder -GBP51.97 (12 trips), news-day fade nothing (0 trips). Ignition alone at the same
  risk would be GBP525.84, so pooling is -GBP58.34 — that gap is the result, and it is the Range
  ladder on the Nasdaq doing the damage, including a -GBP38.91 trade held 15:15 to 20:45 on
  20 Nov and closed on regime. Variant v2 (plus US 500 and FTSE ladders): GBP413.80, max
  drawdown -17.6%, 41 closed — IGN +GBP11.33, RNG -GBP65.78, NEWS GBP0, US 500 ladder -GBP29.43,
  FTSE ladder -GBP2.32. v2 is GBP53.70 behind book 13: the two extra markets are still costing
  money and doubling the drawdown.
- Book 14 (GBP500): GBP552.49 over 586 episodes, max drawdown -5.2%. The Coinbase twin on
  identical rules made GBP540.18 over 621 episodes, so Revolut X is GBP12.31 ahead — the venue's
  prices are not costing anything, and RX got there on 35 fewer episodes. All 26 coins fetched
  cleanly, no stale data.

## Books past 50 closed trips — against Hyperliquid's 53% win / 81% from top 5% (doc 73)

- Book 1 — 90 trips, win 73.3%. Net negative, so the concentration share means nothing yet.
- Book 2 — 1,533 trips, win 52.1%. Top 5% produced 121% of the net: everything outside that
  sliver is net negative. Worse concentration than the benchmark.
- Book 3 — 375 trips, win 38.9%. Net negative, concentration not meaningful.
- Book 6 — 3,515 trip rows (the table pools v3 and v3.1), win 79.8%, top 5% = 32.4%. Better than
  the benchmark on both counts.
- Book 7 — 69 trips, win 84.1%, top 5% = 60.0%.
- Book 8 — 101 trips, win 65.3%. Net a shade below flat, so the share is not meaningful.
- Book 14 — 586 trips (Revolut X side), win 73.0%, top 5% = 49.4%.

Under 50 closed trips: books 4 (18), 5 (0), 9 (1), 10 (0), 11 (7), 12 (5), 13 (16).

## Allocation

Not the 1st of the month. Step 4 skipped, no bucket write.

## Housekeeping

- All fourteen SQL files applied to D1 in full: 7 + 35 + 20 + 1 + 3 + 73 + 4 + 6 + 3 + 6 + 8 + 4
  + 22 + 1,211 statements. Book 14's 1,211 were loaded in file order and verified (1,207 trade
  rows, 586 Revolut X and 621 Coinbase, sums matching the file). No write refused, no daily-limit
  error, no pending file left over.
- Books 7, 8 and 13 each exceed the 10-minute foreground limit while pulling Dukascopy, so they
  were run as background jobs and polled. Book 7's first attempt was killed by the timeout and
  restarted in the background; nothing was lost.
- Committed and pushed to main. The push needed one rebase — the IG demo runner had pushed in the
  meantime — and then succeeded; origin/main confirmed to match local.
- The Claude project refused this log: it is at its maximum size. DK needs to clear space there.
