# 197 — Section 1 paper books: 2026-11-13 run (all fourteen advanced)

NOTE: this log lives in the repo because the claude.ai Project refused the write
— the Project is at its maximum size. DK needs to clear space there; until then
the daily logs cannot be filed in the Project.

**Date:** 2026-11-13 (scheduled run, 07:23 UTC)
**Mandate:** CAP-021 unchanged and unbreached — simulated ledger only. No live
order, no broker or exchange account, no credential, no committed capital.

## Step 0 — kill switch

D1 `dk-capital`, `pb_halt` id=1: active=0, reason NULL, resume_after NULL,
flatten=1 (moot while inactive). Books clear to run. runs/HALT.json written.

## Step 0a — investing crash alert

Newest status file in Drive PA Operation > 01 Capital:
"CRASH ALERT — AMBER — 2026-10-16" (modified 2026-10-16, 28 days old). Still the
only CRASH ALERT file in the folder. Level AMBER -> no action taken. Nothing
tightened, nothing loosened.

ACTION NEEDED BEFORE 2026-11-15 — two days away. Rule (c): never act on a level
older than 30 days, treat a stale file as unreadable. Rule (a): an unreadable
level is treated as EXIT. The file turns 30 days old on 15 Nov 2026. From that
run onward, with no newer file published, this task is obliged to write
pb_halt active=1, flatten=1 and flatten every paper book for 14 days. Flagged in
docs 195 and 196, unchanged.

## Step 0b — queued writes

No runs/pending_d1_*.sql. Nothing queued.

## Setup notes

- Shallow-clone "divergence" again (as doc 196): local main (7afdde9, 11 Nov) vs
  origin/main (3f71f9f, 13 Nov) reported no common ancestor and "50 and 50
  different commits"; graft artefact, not a rewritten history. Origin held
  yesterday's full run (cd4d605) and all twelve state files with correct start
  dates, so local main was reset to origin/main. Nothing lost or replayed.
- Dukascopy was flaky but served every day in the end. First attempt at book 7
  hit 19 consecutive ws_closed_mid_exchange resets through the egress proxy; a
  direct probe of a known-good historical file failed three times. The books'
  own five-attempt retry got through: book 7 pulled 12 Nov (231 bars), book 8
  pulled Wall Street and Germany 40 to 12 Nov 23:55, book 13 v2 pulled US 500
  and FTSE 100 to 12 Nov 23:55. All instruments current to yesterday's close.
  Cost about 50 minutes across books 7, 8 and 13.

## Results

| Book | Today | Yesterday | Shadow / peer | Gap |
|---|---|---|---|---|
| 1 Keltner v1 | $2,089.85 | $2,138.56 | — | — |
| 2 Range v2.2 | $2,191.34 | $2,212.94 | — | — |
| 3 ETF v3 | $1,899.05 | $1,905.80 | — | — |
| 4 Death-cross short | $1,976.13 | $1,976.13 | shadow $2,047.49 | -$71.36 |
| 5 Golden-cross long | $2,000.00 | $2,000.00 | shadow $2,000.00 | $0.00 |
| 5 — v1.1 | $1,924.10 | $1,924.10 | shadow $1,933.88 | -$9.78 |
| 6 Range v3 mid-target | $2,439.14 | $2,489.76 | v2.2 $2,191.34 | +$247.80 |
| 6 — v3.1 | $2,447.23 | $2,470.72 | book 6 $2,439.14 | -$8.09 |
| 7 Ignition v1 | $3,735.14 | $3,494.94 | shadow $1,890.04 | +$1,845.10 |
| 7 — US-hours | $2,582.54 | $2,343.80 | shadow $2,024.18 | +$558.36 |
| 7 — v1.1 | $2,390.24 | $2,151.50 | shadow $1,954.85 | +$435.39 |
| 8 Range v3-IDX | $2,011.40 | $2,009.64 | shadow $2,000.15 | +$11.25 |
| 9 AO saucer BTC/ETH | $1,990.55 | $1,990.55 | shadow $2,000.00 | -$9.45 |
| 10 AO v9.1 (10 coins) | $2,000.00 | $2,000.00 | shadow $2,000.00 | $0.00 |
| 10 — cloud variant | $2,000.00 | $2,000.00 | book 10 $2,000.00 | $0.00 |
| 11 Stock pivots MV | $2,000.00 | $2,000.00 | shadow $2,000.00 | $0.00 |
| 11 Stock pivots EP | $1,979.39 | $2,025.87 | shadow $1,997.93 | -$18.54 |
| 11 — cloud variants | MV $2,000.00 / EP $2,000.00 | — | — | — |
| 12 Daily retest | $1,913.18 | $1,958.05 | shadow $1,913.05 | +$0.13 |
| 13 Combined IG | £490.32 | £492.66 | Ignition alone £509.68 | -£19.36 |
| 13 — v2 | £453.65 | £449.62 | book 13 £490.32 | -£36.67 |
| 14 Revolut X | £532.82 | £540.10 | Coinbase twin £517.13 | +£15.69 |

### Day's activity

- Keltner v1: -$48.71, worst book of the day in money. Three closed — HBAR
  stopped -$25.27 (-16.2%), KSM stopped -$28.53 (-18.3%), GFI target +$5.09.
  Nothing opened; index gate OFF (0.359 vs 200-day mean 0.375). 14 of 40 open,
  down from 17.
- Range v2.2: -$21.60. 56 closed, 3 open. Losses are the 02:00-03:00 UTC regime
  cluster this morning (AAVE, AERO, ARB, AVAX, DOGE, DOT, ETH, HBAR, LINK, LTC,
  ONDO, SOL, SUI, UNI, XRP all out within the hour); winners were short-side
  scale-outs (ZRO +4.1% and +4.0%, NEAR +2.6%, QNT +2.4%).
- ETF v3: -$6.75. 17 closed, 9 open. XME -1.77% long then +0.86% short; CPER
  -1.58%, USO -1.07%, EWZ -0.93%.
- Death-cross short: nothing closed or opened. Holds 8 shorts. Still $71.36
  behind its shadow — the control is winning.
- Golden-cross long: never traded (BTC 4-hour EMA200 gate). Its v1.1 variant
  closed one shadow trip (XRP -4.0% on the hold cap), so the gap narrowed to
  -$9.78.
- Range v3: -$50.62, its worst day. 60 closed, 2 open. Still +$247.80 over
  v2.2 but the gap narrowed from $276.82 — v2.2 lost less for the second day
  running. v3.1 lost less again (-$23.49) and is now $8.09 ahead of v3.
- Ignition v1: +$240.20, the day's one large gain anywhere. Two trades on 12 Nov:
  +0.73 points (breakeven) and +119.37 points — its biggest trip yet, $238.74 at
  $2 a point. Nothing open. Bars to 12 Nov 23:55 UTC. Both variants took it:
  US-hours +$238.74, v1.1 +$238.74.
- Range v3-IDX: +$1.76. 5 closed — Wall Street 3 winners (+0.10%, +0.29%,
  +0.23%), Germany 40 1 winner (+0.16%), US Tech 100 1 regime exit (-0.44%). One
  Wall Street position open. All three instruments current to 12 Nov.
- AO saucer books: BTC and ETH trends both still DOWN, no entries, nothing
  closed. 10-coin book found nothing either. Book 10 is $9.45 ahead of book 9
  only because book 9 took one losing trip and book 10 has never traded.
- Stock pivots: -$46.48 on EP, its first real losses. Three closed — WRBY
  +1.03R (breakeven trail), CRWV -1.54R (stop), NBIS -4.08R (stop, a -23.3%
  overnight gap, the worst single trip the stock books have had). EP now holds
  COHR only. MV found no qualifying pivot and has never traded. The shadow lost
  less (STGW +0.16R, WING +0.04R, TER -1.32R), so EP is now $18.54 BEHIND its
  control, having been $16.71 ahead yesterday. 2,632 daily stocks, no throttling.
- Daily retest: -$44.87. Two closed, both stops — EMB -1.09R, HYG -1.22R.
  Nothing opened. Holds MUB. The shadow lost almost the same (BND -1.27R), so
  real and shadow are level at +$0.13. 27 coins and 60 ETFs loaded.
- Combined IG: -£2.34 to £490.32. Since 1 Nov: Ignition +£4.21 (3 closed), Range
  ladder -£13.90 (6 closed), news fade nothing. Max drawdown -4.6%. Ignition
  alone at the same risk would be £509.68, so the pool is £19.36 worse than the
  single engine — the gap widened from £7.41 because yesterday's big Ignition
  trade was taken at a smaller size inside the pool (margin £49 against the
  ladder's £74). v2 gained £4.03 but is £36.67 behind book 13 with nearly three
  times the drawdown (-11.6%); the US 500 ladder (-£22.13) and FTSE ladder
  (-£7.66) remain the damage.
- Revolut X: -£7.28 to £532.82, 365 episodes, max drawdown -3.1%. The Coinbase
  twin lost twice as much (-£14.28 to £517.13), so the venue gap widened in
  Revolut X's favour to +£15.69.

### Books past 50 closed trips (doc 73 benchmark: 53% win / 81% top-5% share)

| Book | Closed | Win rate | Share of gains from top 5% |
|---|---|---|---|
| 1 Keltner v1 | 76 | 84.2% | 8.5% |
| 2 Range v2.2 | 1,206 | 51.2% | 22.3% |
| 3 ETF v3 | 288 | 41.0% | 31.8% |
| 6 Range v3 | 1,439 | 76.2% | 15.6% |
| 7 Ignition v1 | 53 | 84.9% | 31.9% |
| 8 Range v3-IDX | 75 | 66.7% | 17.5% |
| 14 Revolut X | 365 | 73.7% | 15.5% |

All computed from D1. Every one remains far less top-heavy than the Hyperliquid
winners' 81%. Ignition's concentration actually fell (43.2% -> 31.9%) despite
the +119-point trade, because that trade also lifted the total pool of gains.

### Running record since each book started

Books 1-12 from $2,000; books 13 and 14 from £500.

1 Keltner +$89.85 (15 Oct) · 2 Range v2.2 +$191.34 (16 Oct) · 3 ETF v3 -$100.95
(16 Oct) · 4 Death-cross -$23.87 (18 Oct) · 5 Golden-cross $0.00 (19 Oct) ·
6 Range v3 +$439.14 (19 Oct) · 7 Ignition +$1,735.14 (19 Oct) · 8 Range v3-IDX
+$11.40 (23 Oct) · 9 AO BTC/ETH -$9.45 (27 Oct) · 10 AO v9.1 $0.00 (27 Oct) ·
11 MV $0.00 / EP -$20.61 (28 Oct) · 12 Daily retest -$86.82 (1 Nov) ·
13 Combined IG -£9.68 (1 Nov) · 14 Revolut X +£32.82 (1 Nov).

### Step 4 — monthly allocation

Not the 1st. Skipped.

### Step 6 — memory saved

Pushed to main as cc6dc8b (after a rebase onto the IG daily runner's 26290f4).
All twelve state files, all fourteen SQL files, HALT.json, buckets.json and the
four data caches are in that commit. 1,029 statements applied to D1 across the
fourteen books (755 for book 14 alone); no write refused, no quota error, so
nothing queued.
