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
