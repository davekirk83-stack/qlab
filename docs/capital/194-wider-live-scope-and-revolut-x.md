# 194 — Live IG scope widened; Revolut X runner (9 Nov 2026)

DK 17:21: "We *must* increase the trade frequency. There's no use in having books that don't do anything for days on end."
17:22: "That tells me they're not set up properly or not aimed at enough markets." 17:23: **"Yes to all the above."**

## CAP-021 amendment, 9 Nov 2026 (DK "Yes to all the above")
The live £500 IG spread-bet book (CAP-021 as amended 4 Nov) may also run: the Range v3 ladder on **US 500** and **FTSE 100**; the
**spike continuation engine** (doc 191) on **US Tech 100** and **US 500**; the shock pause (doc 190 S1) on the US Tech 100 and FTSE
ladders; sessions from **07:55 London to 17:00 New York** (the ladders through the US lunch; Ignition still skips 12-15 NY).
Unchanged: IG minimum stakes on every order; never more than 2% of the book at risk on one trade; 5x exposure cap; -4% day stop;
-15% from the start or two negative weeks -> back to paper; DK's own GitHub automation, key only in DK's secrets, DK switches it on/off
(IG_LIVE_ENABLED); no other live accounts beyond the Revolut X amendment of 5 Nov; no extra deposits without DK.
Code: `IG_LIVE_CONFIRMED=CAP021-AMENDED-2026-11-09-IG-WIDER-500` (src/ig_mode.py); the 4 Nov string still runs only the original scope.

## What changed
- `.github/workflows/ig-live.yml`: IG_RANGE_INSTR NQ,US500,FTSE; IG_SPIKE NQ,US500; IG_SHOCK_PAUSE NQ,FTSE; IG_GOV_SPLIT 1;
  three back-to-back jobs (07:55 London -> 08:35 NY; 08:40 -> 13:20 NY; 13:25 -> 17:00 NY), each under GitHub's 350-minute limit.
- `src/ig_spike_engine.py`: runs on live only under the 9 Nov string; minimum stake; refuses any signal risking more than 2% of the book.
- Evidence for frequency: demo (5 markets, longer hours) traded 21 times in its first week; live (1 market, ~5.5h/day) twice.

## Revolut X range-long book (approved 5 Nov) — runner next
Paper book 14 (same rules on Revolut X's own candles): 236 closed trades 1-9 Nov, £500 -> £534.70 (+6.9%), worst dip -1.6%.
DK to do: move £500 into Revolut X; create the API key and put it in GitHub secrets (Claude never sees it).

## 9 Nov evening — Revolut X runner built; the Range book's edge is look-ahead (IMPORTANT)
- Keys: DK made the Ed25519 pair (browser page, never seen by Claude) and put REVX_API_KEY / REVX_PRIVATE_KEY in GitHub secrets.
  `revx-live.yml mode=check` -> "KEY CHECK OK" (read-only balances call). Account empty. No USD/GBP pair on Revolut X; GBP pairs are thin
  (1-9 Nov replay: 59 episodes vs 203 on USD), so the plan was USD converted in the Revolut app.
- Runner v1 (`src/revx_live.py`, bought after each bar closed): replay 1-9 Nov -3.5% vs paper book 14's +6.9%.
- Runner v2 (resting post-only bids at the rungs and a resting sell at the mid, priced from the last CLOSED bar): replay 1-9 Nov -0.3%.
- Why: `paperbook6.step` prices bar i's rungs and its mid exit from **bar i's own close** (EMA/bands include C[i]) and then asks whether
  bar i's low touched them. That uses the close before it happens. `src/revx_honest_test.py` (12 months to 30 Oct 2026, 26 coins,
  Revolut X costs, pool 10%/10 open): engine £500 -> £2,420 (maxDD -7%); same rules with orders priced from the previous bar
  £500 -> **£356 (maxDD -30%)**; with bids pre-adjusted for the band moving inside the bar £333. 1-9 Nov on Revolut X candles: engine +7%,
  honest +1%.
- Same check on the IG ladder (`src/ig_ladder_honest_test.py`, both sides, ~1 year, before IG spread): engine NQ +24% / US500 +17% /
  FTSE +17% summed per-episode returns; honest (what `src/ig_range_engine.py` actually does live) NQ 0.0% / US500 -6.1% / FTSE +1.3%.
  Real demo ladder fills 26 Oct - 6 Nov: 14 trades, +£48 (mostly NQ) — too few to separate from zero.
- Consequences: do NOT fund the Revolut X range book (workflow schedule removed; check/dry stay manual). Paper book 14's results and the
  doc 137/173 ladder backtests overstate the edge for the same reason. Ignition and the spike engine decide on closed bars and are not affected.
  The live IG ladders (NQ, and US500/FTSE added today) have no demonstrated edge on honest pricing — DK to decide whether they stay live.
