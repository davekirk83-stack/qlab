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
