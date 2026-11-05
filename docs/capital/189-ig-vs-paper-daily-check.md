# 189 — Small fixes to the IG runners, and the daily IG-vs-paper check (5 Nov 2026)

(Kept in the qlab repo because the project store was full on 5 Nov 2026: 2,000,355 / 2,000,000.)

DK 08:51: "For our books, are there any tweaks or improvements you would make now, however small or marginal?"
08:54: "1 and 3 yes". 08:55: "Also yes to the range long book". Item 2 (a separate daily trade count per engine) is waiting: DK asked for it to be explained.

## Fix 1 — the daily loss figure mixed points and pounds (2ac7fb5)
- **The fault:** Ignition added its results in points and the ladders added theirs in £, all into one figure.
  - Example, 4 Nov: the day showed −59.7. That was −56.1 pts from Ignition plus −£3.62 from the FTSE ladder.
- **The fix:** `IG_GOV_SPLIT=1` gives the ladders their own £ figure (`dpl_rng`, £200/day cap). Ignition stays in points (200-pt cap).
- **Scope:** demo only; the live workflow is unchanged. The −4% book day stop was never affected.

## Fix 3 — daily check that IG trades what the paper record says (2ac7fb5)
- **What the runner now logs:** every Ignition signal goes to `runs/<book>/signals.csv`, with its outcome:
  - taken, lunch, governor, cooloff, book_day_stop, fomc_blackout, outside_us_hours.
  - This is logging only, and it runs on live too.
- **The check, `src/ig_vs_paper.py`:** compares the paper feed (Dukascopy) with IG's bars for each New York day, matched within 10 minutes.
  - It separates coverage gaps (runner not running) from real feed differences.
  - It reports each fill against the IG signal close.
- **Scheduled task `trig_017uyHg1jLCkZx2UXVsDBFUb`:** runs Tue–Sat at 08:53 London and appends to `runs/ig_vs_paper_log.md`.
- **When it messages DK:**
  - a live fill more than 10 pts worse than its signal;
  - live and paper disagree on a taken trade;
  - an error;
  - agreement under 50% after 10 or more signals.
- **First look, 26 Oct – 4 Nov:**
  - 6 signals came in while the runner was live; 2 matched, 3 were on paper only and 1 was on IG only (4 Nov 15:50 NY).
  - Slippage was +0.9, −1.1 and +21.1 pts.
  - Before 5 Nov, skipped signals were not logged, so some "paper only" cases may simply be signals the runner skipped.
  - The feeds can differ because Ignition uses volume and delta, and IG's volume is a tick count.

## Checked, not changed
- **No Ignition entries just before the close?** No. On a year of data, entries from 15:45 to 16:00 NY average +23.5 pts (14 trades), and the last 30 minutes are positive in both halves.

## Book 14 (Range longs on Revolut X) live — DK "yes", 08:55
- **Paper record so far:** £525.47 from £500 since 1 Nov; 109 episodes; 83.5% wins; max drawdown −0.6%. Revolut X's own prices came out +£4.61 better than Coinbase.
- **What it needs:**
  1. A CAP-021 amendment in DK's own words. "No crypto live trading" currently stands.
  2. A £500 deposit. Revolut X balances were all zero on 5 Nov.
  3. A trading API key, held only in DK's GitHub secrets.
  4. A Revolut X live runner with the IG-style guards, proven in dry-run first.

## CAP-021 AMENDED for Revolut X — DK "Yes", 5 Nov 2026 09:12
> CAP-021 amended for Revolut X: a live book of £500 may run the Range long book (spot, long only) on DK's Revolut X account through DK's own GitHub automation, key held only in DK's GitHub secrets, switched on and off by DK. Limits: 10% of the book per episode, at most 10 open, −15% from start or two negative weeks → back to paper. No leverage, no other crypto venues.
Next: Claude builds the Revolut X runner (dry-run first); DK deposits £500 and creates the trading key when the runner is ready.

## Fix 2 — separate daily trade counts, DK "8 per book?" (5 Nov 09:13)
The 8-a-day limit is ours (from AuclairsDad's governor design), not IG's. Ignition's busiest day in a year of v1.1 was 3 trades (61 one-trade days, 9 two, 1 three) — the limit is a runaway fuse, not a return driver. Claude suggested 4 per engine; DK asked for 8 per book. Done on the demo under IG_GOV_SPLIT=1: Ignition keeps its own 8 ("ntr"), each ladder market has its own 8 ("ntr_<market>"). Live unchanged until the demo shows fixes 1 and 2 working.

## LIVE — DK switched it on, 5 Nov 2026 ~16:26 London
DK created the repo variable IG_LIVE_ENABLED=true (after the link route failed; done via Settings → Secrets and variables → Actions → Variables → New repository variable). Today's earlier live crons (13:53, 14:24, 14:33, 14:58 UTC) had skipped. First live session: run 42080396125, started 18:02 UTC, in progress, minimum stakes, to 22:00 UK. Review scheduled 22:20 (trig_01VBQRmyarMjV8qJvsNkQy5M). Context: Nasdaq futures −4.7% on the day; BTC $81,131 (4 Nov) → $75,568 (5 Nov 15:53).

## First live session review + demo faults found (5 Nov 22:20)
LIVE (run 42080396125, 18:02–22:00 UK): logged in to the live spread-bet account, US Tech 100 TRADEABLE at min £0.01/pt, streamed all session, ladder seeded from the runner's own IG bars; no Ignition signal, no ladder episode (NQ chopped 26,500–27,060; ladder regime off) — no orders, book £500.00, no errors. The "MARKET subscription error 21 Invalid group" line is harmless (the CHART feed is what's used).
DEMO faults, fixed (commit below):
1. IG's historical-data allowance ran out on the demo at 14:03 (error.public-api.exceeded-account-historical-data-allowance) — 5 ladder markets x 300 bars x several jobs a day. With no IG history the Dukascopy cache could not be aligned to IG's level (offsets ran +38 to +100 pips today), and the USD/JPY ladder sold at market ~60 pips off its band at 14:15. Fix: fall back to today's own logged IG bars; if none, the instrument is DISABLED for that session (no new episodes). Stub-tested both paths. Live is unaffected (its one ladder uses the runner's own bars).
2. 'Runner' object has no attribute 'news' on the first tick (08:15, 18:05): the stream can tick before __init__ sets it. Fixed with a class default.
3. USD/JPY "working order rejected: ATTACHED_ORDER_LEVEL_ERROR" once (08:30) — attached stop/limit level refused; to investigate.
FX SPREADS on the demo, London hours today: GBP/USD mean 1.33 pips (median 1.40) vs 0.9 assumed; USD/JPY 1.00 vs 0.7 assumed — both ~45-50% wider. The FX ladders were cost-sensitive (doc 182); re-test at these spreads before any live use.
