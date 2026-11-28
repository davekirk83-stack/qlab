# IG vs paper — daily log

Daily check (doc 189). Tally: both feeds / paper only while runner live / IG only; slippage = IG fill vs IG signal close, negative = against us.

## 2026-11-05 (NY day) — checked 2026-11-06

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-05 New York
  09:30 NY SELL IG only    paper close       nan  IG close   27856.0  taken
  10:50 NY SELL both       paper close   26764.8  IG close   26762.3  taken
  15:05 NY SELL paper only paper close   26781.4  IG close       nan  IG runner was live, its feed gave no signal
  agreement: 1/3 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 09:30 NY side -1: filled 27858.8 vs IG signal close 27856.0 -> -2.8 pts against us; result +110.7 pts (ig_limit)
  IG fill 10:50 NY side -1: filled 26767.7 vs IG signal close 26762.3 -> -5.4 pts against us; result -85.0 pts (ig_stop)
  paper trade 10:50 NY side -1: +0.5 pts (be)
  paper trade 15:05 NY side -1: +0.5 pts (be)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-05 New York
  10:50 NY SELL paper only paper close   26764.8  IG close       nan  IG runner not running then (coverage, not a feed difference)
  15:05 NY SELL paper only paper close   26781.4  IG close       nan  IG runner was live, its feed gave no signal
  agreement: 0/1 signals on both feeds while the IG runner was live (1 paper signals fell outside its sessions)
  paper trade 10:50 NY side -1: +0.5 pts (be)
  paper trade 15:05 NY side -1: +0.5 pts (be)
```

Day: ig_demo both 1 / paper-only-while-live 1 / IG-only 1, slippage mean -4.1 pts (2 fills: -2.8, -5.4). ig_live both 0 / paper-only-while-live 1 / IG-only 0, no fills (1 paper signal outside session).

Running tally (from 2026-11-05): ig_demo agree 1/3, mean slippage -4.1 pts over 2 fills; ig_live agree 0/1, no fills.

Flag: ig_live missed the 15:05 NY SELL that paper took (runner live, its feed gave no signal).

## 2026-11-06 (NY day) — checked 2026-11-07

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-06 New York
  no Ignition signal on either feed — agree

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-06 New York
  no Ignition signal on either feed — agree
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 0, no fills. ig_live both 0 / paper-only-while-live 0 / IG-only 0, no fills.

Running tally (from 2026-11-05): ig_demo agree 1/3, mean slippage -4.1 pts over 2 fills; ig_live agree 0/1, no fills.

## 2026-11-09 (NY day) — checked 2026-11-10

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-09 New York
  no Ignition signal on either feed — agree

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-09 New York
  09:40 NY BUY  IG only    paper close       nan  IG close   27568.6  taken
  17:35 NY BUY  IG only    paper close       nan  IG close   27937.4  cooloff
  agreement: 0/2 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 09:40 NY side +1: filled 27568.0 vs IG signal close 27568.6 -> -0.6 pts against us; result +32.7 pts (ig_limit)
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 0, no fills (note: no ig_demo bars files for 2026-11-09 — the demo NQ runner does not appear to have run that day, so "agree" here is empty coverage). ig_live both 0 / paper-only-while-live 0 / IG-only 2 (1 taken, 1 cooloff), slippage -0.6 pts over 1 fill (negative = filled better than the signal close).

Caveat: the paper feed (data_nq_cache/nq_5m.csv) has gaps on 2026-11-09 UTC — no bars 09:00–09:55, 14:00–15:55 and 21:15–22:55 UTC. The 14:00–15:55 UTC hole is 09:00–10:55 NY, which covers the live 09:40 NY BUY, so the "IG only" taken trade is a paper data gap, not a feed disagreement. ig_vs_paper.py marks the day "covered" if any bar exists, so it does not flag such holes.

Running tally (from 2026-11-05): ig_demo agree 1/3, mean slippage -4.1 pts over 2 fills; ig_live agree 0/3 (2 of the 3 misses fall in the 9 Nov paper data gap), mean slippage -0.6 pts over 1 fill.

Flag: ig_live took a live BUY at 09:40 NY (+32.7 pts) with no paper counterpart — paper feed missing those bars.

## 2026-11-10 (NY day) — checked 2026-11-11

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-10 New York
  no Ignition signal on either feed — agree

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-10 New York
  12:35 NY SELL IG only    paper close       nan  IG close   27452.7  lunch
  agreement: 0/1 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 0, no fills. ig_live both 0 / paper-only-while-live 0 / IG-only 1 (lunch skip, not taken), no fills.

Caveat: paper feed has gaps on 2026-11-10 UTC — no bars 16:00–16:55 UTC (11:00–11:55 NY) and 21:15–22:55 UTC. The 12:35 NY (17:35 UTC) bar itself is present on paper, so this IG-only signal is a feed difference, though the hour-earlier hole may affect paper's indicator state. Not a taken trade.

Running tally (from 2026-11-05): ig_demo agree 1/3, mean slippage -4.1 pts over 2 fills; ig_live agree 0/4 (2 of the 4 misses fall in the 9 Nov paper data gap; none of the 4 is a live-vs-paper disagreement on a trade paper took), mean slippage -0.6 pts over 1 fill.

## 2026-11-11 (NY day) — checked 2026-11-12

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-11 New York
  04:40 NY BUY  IG only    paper close       nan  IG close   28191.7  taken
  06:50 NY BUY  IG only    paper close       nan  IG close   28282.2  taken
  21:25 NY SELL IG only    paper close       nan  IG close   28225.1  ad_tue_wed
  21:35 NY SELL IG only    paper close       nan  IG close   28216.0  ad_tue_wed
  agreement: 0/4 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 04:40 NY side +1: filled 28193.3 vs IG signal close 28191.7 -> +1.6 pts against us; result +2.2 pts (ig_limit)
  IG fill 06:50 NY side +1: filled 28283.4 vs IG signal close 28282.2 -> +1.2 pts against us; result -2.3 pts (ig_stop)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-11 New York
  no Ignition signal on either feed — agree
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 4 (2 taken, 2 ad_tue_wed skips), slippage +1.4 pts mean over 2 fills (against us). ig_live both 0 / paper-only-while-live 0 / IG-only 0, no fills.

Caveat: paper feed gaps on 2026-11-11 UTC — no bars 12:00–13:55 UTC (07:00–08:55 NY) and 21:15–22:55 UTC. The two taken demo BUYs (09:40 and 11:50 UTC) both have paper bars present (paper closes 28193.6 and 28284.1, within ~2 pts of IG), so those two are genuine feed disagreements — paper produced no signal on the same bars. The two 21:25/21:35 NY SELLs fall on 12 Nov UTC (02:25/02:35), which the paper file does not yet cover, so they are coverage, not disagreement.

Running tally (from 2026-11-05): ig_demo agree 1/7, mean slippage -1.35 pts over 4 fills; ig_live agree 0/4 (none a disagreement on a trade paper took), mean slippage -0.6 pts over 1 fill. Combined 1/11 signals — past the 10-signal mark and below 50%.

## 2026-11-12 (NY day) — checked 2026-11-13

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-12 New York
  02:40 NY SELL IG only    paper close       nan  IG close   28075.3  taken
  10:50 NY BUY  both       paper close   28348.8  IG close   28348.9  cooloff
  11:05 NY BUY  IG only    paper close       nan  IG close   28502.9  cooloff
  17:10 NY SELL IG only    paper close       nan  IG close   28283.5  ad_no_regime
  23:55 NY SELL IG only    paper close       nan  IG close   28271.2  ad_no_regime
  agreement: 1/5 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 02:40 NY side -1: filled 28072.2 vs IG signal close 28075.3 -> +3.1 pts against us; result -7.7 pts (session_end)
  paper trade 10:50 NY side +1: +119.4 pts (be)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-12 New York
  10:50 NY BUY  paper only paper close   28348.8  IG close       nan  IG runner not running then (coverage, not a feed difference)
  14:20 NY SELL IG only    paper close       nan  IG close   28315.4  lunch
  agreement: 0/1 signals on both feeds while the IG runner was live (1 paper signals fell outside its sessions)
  IG fill 10:50 NY side +1: filled 28346.9 vs IG signal close 28348.5 -> -1.6 pts against us; result +10.7 pts (ig_limit)
  paper trade 10:50 NY side +1: +119.4 pts (be)
```

Day: ig_demo both 1 / paper-only-while-live 0 / IG-only 4 (1 taken, 3 skips), slippage +3.1 pts over 1 fill (against us). ig_live both 0 (script) / paper-only-while-live 0 / IG-only 1 (lunch skip), slippage -1.6 pts over 1 fill (in our favour).

Flag — script/runner mismatch: the script labels the ig_live 10:50 NY BUY "paper only, runner not running", but runs/ig_live/trades.csv shows the live runner opened that BUY at 15:50 UTC (IG signal close 28348.55, filled 28346.90). The bar is missing from runs/ig_live/signals.csv (only the 19:20 UTC lunch row is logged for 12 Nov), so the script's coverage test misfires. In substance live and paper agreed on this trade (same bar, same side, closes 0.25 pt apart). Outcome differed sharply: live +10.7 pts (ig_limit) vs paper +119.4 pts (be).

Running tally (from 2026-11-05): ig_demo agree 2/12, mean slippage -0.46 pts over 5 fills; ig_live agree 0/5 by script (1/6 counting the 10:50 BUY both runners took), mean slippage -1.1 pts over 2 fills. Combined 2/17 by script (3/18 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-13 (NY day) — checked 2026-11-14

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-13 New York
  04:45 NY SELL IG only    paper close       nan  IG close   28228.3  taken
  agreement: 0/1 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-13 New York
  no Ignition signal on either feed — agree
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 1; no fill. ig_live no signal on either feed (agree); no fill. Slippage: no fills today.

Notes: the paper feed has the 09:45 UTC bar (close 28229.3 vs IG 28228.3, 1 pt apart) but produced no signal, so this is a genuine feed disagreement, not coverage. The demo SELL is logged "taken" in runs/ig_demo/signals.csv, but the demo run log (commit 9cd53e5) says "SIGNAL SELL skipped — book exposure already at the 5x cap"; no row in runs/ig_demo/trades.csv and state.json ntr 0. So no order was placed — the signals.csv "taken" label is wrong for cap skips.

Running tally (from 2026-11-05): ig_demo agree 2/13, mean slippage -0.46 pts over 5 fills; ig_live agree 0/5 by script (1/6 counting the 12 Nov 10:50 BUY both runners took; no-signal days add nothing), mean slippage -1.1 pts over 2 fills. Combined 2/18 by script (3/19 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-16 (NY day) — checked 2026-11-17

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-16 New York
  14:30 NY SELL IG only    paper close       nan  IG close   27229.6  lunch
  16:50 NY SELL IG only    paper close       nan  IG close   27161.4  taken
  agreement: 0/2 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-16 New York
  16:50 NY SELL IG only    paper close       nan  IG close   27160.7  taken
  18:15 NY SELL IG only    paper close       nan  IG close   27212.1  ad_no_regime
  18:35 NY SELL IG only    paper close       nan  IG close   27131.8  ad_no_regime
  agreement: 0/3 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 16:50 NY side -1: filled 27159.2 vs IG signal close 27160.7 -> +1.5 pts against us; result -51.7 pts (ig_stop)
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 2 (1 "taken", 1 lunch skip); no demo fill (no row in runs/ig_demo/trades.csv for 16 Nov). ig_live both 0 / paper-only-while-live 0 / IG-only 3 (1 taken, 2 ad_no_regime skips); slippage +1.5 pts over 1 fill (against us).

Flag — taken live trade with no paper counterpart: the live 16:50 NY SELL (21:50 UTC) was filled and stopped for -51.7 pts. data_nq_cache/nq_5m.csv has no bars from 21:15 to 22:55 UTC on 16 Nov (21:10 then 23:00; the 22:00–23:00 UTC hour is the normal CME halt, but 21:15–21:55 is a paper-feed gap). So the paper record could not have seen this bar — a paper-data coverage hole, not a confirmed signal difference. The demo "taken" 21:50 SELL has no trade row, consistent with the cap-skip mislabel noted on 13 Nov.

Running tally (from 2026-11-05): ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 0/8 by script (1/9 counting the 12 Nov 10:50 BUY both runners took), mean slippage -0.23 pts over 3 fills. Combined 2/23 by script (3/24 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-17 (NY day) — checked 2026-11-18

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-17 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-17 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```

Comparison not possible: data_nq_cache/nq_5m.csv still ends 2026-11-16 23:55 UTC at 09:05 UTC on 18 Nov (re-pulled after a 10-minute wait). The last "paper books" commit touching it is 4d4a4c8 (17 Nov); today only "paper books 15-16" (d9c0409) landed, which does not touch the NQ cache — so the 18 Nov 07:23 paper run appears not to have pushed bars.

IG side only (for the record, not scored): ig_demo logged no 17 Nov signals. ig_live logged 6 signals — 04:25 UTC SELL taken; 05:00, 08:15 UTC SELL and 22:05, 22:25, 22:40 UTC BUY all skipped ad_tue_wed.
Live fill 04:25 UTC SELL: filled 27255.40 vs IG signal close 27258.30 -> +2.9 pts against us; result -45.9 pts (ig_stop). Within the 10-pt threshold.

Running tally (from 2026-11-05), unchanged pending paper bars for 17 Nov: ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 0/8 by script (1/9 adjusted), mean slippage -0.23 pts over 3 scored fills (0.55 pts over 4 including today's unscored +2.9). Combined 2/23 by script (3/24 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-17 (NY day, catch-up) and 2026-11-18 (NY day) — checked 2026-11-19

Paper bars now run to 2026-11-18 23:55 UTC, so 17 Nov is scored as well.

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-17 New York
  no Ignition signal on either feed — agree

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-17 New York
  00:00 NY SELL IG only    paper close       nan  IG close   27258.7  ad_tue_wed
  03:15 NY SELL IG only    paper close       nan  IG close   27194.0  ad_tue_wed
  17:05 NY BUY  IG only    paper close       nan  IG close   27092.6  ad_tue_wed
  17:25 NY BUY  IG only    paper close       nan  IG close   27150.6  ad_tue_wed
  17:40 NY BUY  IG only    paper close       nan  IG close   27327.8  ad_tue_wed
  agreement: 0/5 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)

IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-18 New York
  no Ignition signal on either feed — agree

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-18 New York
  00:10 NY BUY  IG only    paper close       nan  IG close   27123.4  ad_tue_wed
  agreement: 0/1 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
```

17 Nov: ig_demo both 0 / paper-only 0 / IG-only 0. ig_live both 0 / paper-only-while-live 0 / IG-only 5 (all ad_tue_wed skips, none taken). The 04:25 UTC live SELL fill noted on 18 Nov is 23:25 NY on 16 Nov, so it is not in this NY day.
18 Nov: ig_demo both 0 / paper-only 0 / IG-only 0. ig_live both 0 / paper-only-while-live 0 / IG-only 1 (ad_tue_wed skip). No fills on either runner (no 18 Nov rows in runs/ig_*/trades.csv).

Running tally (from 2026-11-05): ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 0/14 by script (1/15 adjusted), mean slippage -0.23 pts over 3 scored fills (0.55 over 4 incl. the unscored 16 Nov 23:25 NY +2.9). Combined 2/29 by script (3/30 adjusted) — still below 50% past the 10-signal mark. Every unmatched signal in these two days is IG-only and was skipped by the ad_tue_wed filter, i.e. the paper feed printed no Ignition signal at all. (Sign convention: positive slippage = against us.)

## 2026-11-19 (NY day) — checked 2026-11-20

Paper bars run to 2026-11-19 23:55 UTC.

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-19 New York
  11:50 NY SELL paper only paper close   27051.5  IG close       nan  IG runner not running then (coverage, not a feed difference)
  agreement: 0/0 signals on both feeds while the IG runner was live (1 paper signals fell outside its sessions)
  paper trade 11:50 NY side -1: +268.8 pts (be)

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-19 New York
  08:05 NY BUY  IG only    paper close       nan  IG close   27719.2  ad_no_coil
  10:30 NY SELL IG only    paper close       nan  IG close   27145.0  ad_no_regime
  11:50 NY SELL both       paper close   27051.5  IG close   27050.5  ad_no_coil
  18:20 NY SELL IG only    paper close       nan  IG close   26428.0  ad_no_coil
  agreement: 1/4 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  paper trade 11:50 NY side -1: +268.8 pts (be)
```

Day: ig_demo both 0 / paper-only-while-live 0 / IG-only 0 (runner down — see below). ig_live both 1 / paper-only-while-live 0 / IG-only 3 (all filter skips, none taken). No Ignition fills on either runner (no 19 Nov rows in runs/ig_*/trades.csv), so no slippage today.

Flag — taken-trade disagreement: the 11:50 NY (16:50 UTC) SELL printed on both feeds (closes 1 pt apart) and paper took it for +268.8 pts, but ig_live skipped it on the ad_no_coil filter. Feeds agree; the live add-on filter is what dropped a paper-taken winner.

Flag — demo runner down: no ig_demo commit since 2026-11-16 21:59 UTC (4e27a5e) and no demo bars after 16 Nov. runs/ig_demo/last_error.txt holds a traceback ending `error.public-api.exceeded-account-historical-data-allowance`. The 17/18 Nov demo "no signal on either feed — agree" lines above therefore reflect no demo coverage, not agreement.

Side note (not Ignition): ig_live spike engine SELL NQ 17:00 UTC, 26712.3 -> 26941.1, -228.8 pts (-£13.73), ig_stop_or_limit.

Running tally (from 2026-11-05): ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 1/18 by script (2/19 adjusted), mean slippage -0.23 pts over 3 scored fills. Combined 3/33 by script (4/34 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-20 (NY day) — checked 2026-11-21 09:05 UTC

Paper bars still end 2026-11-19 23:55 UTC: the Saturday paper run had not pushed by 09:03 UTC (waited 10 min and pulled again, as specified). The comparison could not be run yet.

```
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-20 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update

IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-20 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```

IG side only (from runs/ig_live/signals.csv and trades.csv), not compared with paper:
- ig_live printed 5 Ignition signals: 07:15 UTC SELL taken, 07:55 UTC SELL taken, 10:45 SELL ad_no_regime, 17:00 SELL ad_no_coil, 20:50 SELL ad_no_coil.
- Live fills: 07:15 SELL signal close 26244.3, fill 26236.9 → slippage +7.4 pts, exit ig_limit +46.5 pts. 07:55 SELL signal close 26307.3, fill 26304.4 → slippage +2.9 pts, exit ig_stop −65.7 pts. Neither more than 10 pts worse.
- ig_demo: still no commit since 2026-11-16 21:59 UTC; last_error.txt still ends `error.public-api.exceeded-account-historical-data-allowance`.

Day tally: pending (paper feed missing) — to be scored by the next run, or by rerunning `python src/ig_vs_paper.py 2026-11-20 ig_live` once the paper bars land.

Running tally (from 2026-11-05), agreement unchanged pending 20 Nov: ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 1/18 by script (2/19 adjusted), mean slippage +1.91 pts over 5 scored fills (+2.07 over all 6 incl. 17 Nov 04:25 UTC). Combined 3/33 by script (4/34 adjusted) — still below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-23 (NY day) — checked 2026-11-24 09:10 UTC; also re-scores 2026-11-20

Paper bars (data_nq_cache/nq_5m.csv) still end 2026-11-22 23:55 UTC. Waited 10 min and pulled again: unchanged. Today's "paper books 2026-11-24" commit (08:08 UTC) did not advance the NQ cache, so 23 Nov cannot be compared yet.

```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-23 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-23 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```

IG side only for 23 Nov (not compared with paper):
- ig_live: 4 Ignition signals (02:15, 22:00, 22:05, 22:10 UTC SELL), all skipped ad_no_regime. No Ignition fills.
- ig_demo: runner is back (signals logged 23 Nov; last demo commit 2026-11-24 07:24 UTC). 8 signals: 13:30 UTC SELL ad_no_coil; 21:50 UTC BUY **taken** (close 26748.40); 22:15–22:55 UTC six BUYs ad_no_regime. The 21:50 taken signal has no row in runs/ig_demo/trades.csv and state.json has reset for 24 Nov, so no fill or result could be scored.

Re-run of 2026-11-20 now that the paper bars cover it:

```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-20 New York
  02:15 NY SELL IG only    paper close       nan  IG close   26244.3  taken
  02:55 NY SELL IG only    paper close       nan  IG close   26307.3  taken
  05:45 NY SELL IG only    paper close       nan  IG close   26229.2  ad_no_regime
  12:00 NY SELL IG only    paper close       nan  IG close   25473.9  ad_no_coil
  15:50 NY SELL IG only    paper close       nan  IG close   25062.3  ad_no_coil
  agreement: 0/5 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
  IG fill 02:15 NY side -1: filled 26236.9 vs IG signal close 26244.3 -> +7.4 pts against us; result +46.5 pts (ig_limit)
  IG fill 02:55 NY side -1: filled 26304.4 vs IG signal close 26307.3 -> +2.9 pts against us; result -65.7 pts (ig_stop)
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-20 New York
  no Ignition signal on either feed — agree
```

20 Nov: ig_live both 0 / paper-only-while-live 0 / IG-only 5. Flag — taken-trade disagreement: ig_live took two live SELLs (02:15 and 02:55 NY, net −19.2 pts) that the paper feed never signalled. Neither fill was more than 10 pts worse than its signal.

Running tally (from 2026-11-05): ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 1/23 by script (2/24 adjusted), mean slippage +1.91 pts over 5 scored fills. Combined 3/38 by script (4/39 adjusted) — below 50% past the 10-signal mark. 23 Nov pending paper bars. (Sign convention: positive slippage = against us.)

## 2026-11-24 (NY day) — checked 2026-11-25 ~09:20 UTC; 23 Nov still pending

Paper bars (data_nq_cache/nq_5m.csv) still end 2026-11-22 23:55 UTC (last data_nq_cache commit 2026-11-23 14:44 UTC). Waited 10 min and pulled again: unchanged. No "paper books" daily commit since 2026-11-23 08:57 UTC, so neither 23 nor 24 Nov can be compared — paper feed now three NY days behind.

```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-24 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-24 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-23 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-23 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```

IG side only for 24 Nov NY (from signals.csv; not compared with paper):
- ig_live: 6 Ignition signals — SELL 08:25, 10:45 UTC; BUY 22:25, 22:30 UTC; SELL 01:15, 03:45 UTC (25 Nov) — all skipped ad_tue_wed. No rows in trades.csv for 23–25 Nov; no fills.
- ig_demo: 5 Ignition SELL signals — 08:25, 08:55, 10:45, 12:00, 13:25 UTC — all skipped ad_tue_wed. No fills. Demo runner active (last commit 2026-11-25 06:08 UTC).
- Both runners' last_error.txt end `error.public-api.exceeded-account-historical-data-allowance` (IG historical-data allowance).

Day tally: pending (paper feed missing). No taken trades on either IG book, so no slippage to add.

Running tally (from 2026-11-05), unchanged: ig_demo agree 2/15, mean slippage -0.46 pts over 5 fills; ig_live agree 1/23 by script (2/24 adjusted), mean slippage +1.91 pts over 5 scored fills as carried in the 23 Nov entry (note: unclear from the log whether the 20 Nov live fills, +7.4 and +2.9, are inside that figure; if not, it would be +2.84 over 7 — to be reconciled). Combined 3/38 by script (4/39 adjusted) — below 50% past the 10-signal mark. 23 and 24 Nov pending paper bars. (Sign convention: positive slippage = against us.)

## 2026-11-23 and 2026-11-24 (NY days, now compared); 2026-11-25 pending — checked 2026-11-26 ~09:15 UTC

Paper bars now end 2026-11-24 23:55 UTC (paper books commit 2026-11-25 09:38 UTC). Waited 10 min and pulled again: no 25 Nov bars, so 25 Nov stays pending.

```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-23 New York
  17:00 NY SELL IG only    paper close       nan  IG close   26749.7  ad_no_regime
  17:05 NY SELL IG only    paper close       nan  IG close   26741.8  ad_no_regime
  17:10 NY SELL IG only    paper close       nan  IG close   26744.5  ad_no_regime
  19:30 NY SELL IG only    paper close       nan  IG close   26722.0  ad_no_coil
  agreement: 0/4 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-23 New York
  08:30 NY SELL IG only    paper close       nan  IG close   25846.2  ad_no_coil
  16:50 NY BUY  IG only    paper close       nan  IG close   26748.4  taken
  17:15 NY BUY  IG only    paper close       nan  IG close   26756.8  ad_no_regime
  17:20 NY BUY  IG only    paper close       nan  IG close   26760.7  ad_no_regime
  17:25 NY BUY  IG only    paper close       nan  IG close   26768.0  ad_no_regime
  17:30 NY BUY  IG only    paper close       nan  IG close   26775.5  ad_no_regime
  17:35 NY BUY  IG only    paper close       nan  IG close   26787.9  ad_no_regime
  17:55 NY BUY  IG only    paper close       nan  IG close   26796.5  ad_no_regime
  agreement: 0/8 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-24 New York
  03:25 NY SELL IG only    paper close       nan  IG close   26645.2  ad_tue_wed
  05:45 NY SELL IG only    paper close       nan  IG close   26259.0  ad_tue_wed
  17:25 NY BUY  IG only    paper close       nan  IG close   26254.2  ad_tue_wed
  17:30 NY BUY  IG only    paper close       nan  IG close   26264.0  ad_tue_wed
  20:15 NY SELL IG only    paper close       nan  IG close   26124.2  ad_tue_wed
  22:45 NY SELL IG only    paper close       nan  IG close   25928.6  ad_tue_wed
  agreement: 0/6 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-24 New York
  03:25 NY SELL IG only    paper close       nan  IG close   26645.3  ad_tue_wed
  03:55 NY SELL IG only    paper close       nan  IG close   26537.8  ad_tue_wed
  05:45 NY SELL IG only    paper close       nan  IG close   26257.4  ad_tue_wed
  07:00 NY SELL IG only    paper close       nan  IG close   26298.8  ad_tue_wed
  08:25 NY SELL IG only    paper close       nan  IG close   26140.0  ad_tue_wed
  agreement: 0/5 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-25 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-25 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```

23 Nov: ig_live both 0 / paper-only-while-live 0 / IG-only 4 (none taken). ig_demo both 0 / paper-only 0 / IG-only 8; one marked taken (BUY 16:50 NY) but runs/ig_demo/trades.csv has no row after 12 Nov, so no fill recorded — possibly blocked by the IG error below. Demo only, not live.
24 Nov: ig_live both 0 / paper-only 0 / IG-only 6; ig_demo both 0 / paper-only 0 / IG-only 5. All skipped ad_tue_wed. No fills.
Both runners' last_error.txt still end `error.public-api.exceeded-account-historical-data-allowance`.

Slippage reconciled from runs/ig_live/trades.csv (fills since 5 Nov, (IG fill − IG signal close) × side): -0.6, -1.6, +1.5, +2.9, +7.4, +2.9 → mean +2.07 pts over 6 fills (includes the two 20 Nov fills). No new fills on 23–24 Nov on either book.

Running tally (from 2026-11-05): ig_demo agree 2/28, mean slippage -0.46 pts over 5 fills; ig_live agree 1/33 by script (2/34 adjusted), mean slippage +2.07 pts over 6 fills. Combined 3/61 by script (4/62 adjusted) — below 50% past the 10-signal mark. 25 Nov pending paper bars. (Sign convention: positive slippage = against us.)

## 2026-11-25 (NY) — checked 2026-11-27 (26 Nov Thanksgiving: no paper bars, cash closed)
```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-25 New York
  09:30 NY SELL IG only    paper close       nan  IG close   25157.5  ad_tue_wed
  09:40 NY SELL IG only    paper close       nan  IG close   25010.9  ad_tue_wed
  17:15 NY BUY  IG only    paper close       nan  IG close   25969.3  ad_tue_wed
  17:25 NY BUY  IG only    paper close       nan  IG close   25979.7  ad_tue_wed
  17:30 NY BUY  IG only    paper close       nan  IG close   25991.8  ad_tue_wed
  17:35 NY BUY  IG only    paper close       nan  IG close   26006.0  ad_tue_wed
  17:45 NY BUY  IG only    paper close       nan  IG close   26018.2  ad_tue_wed
  17:50 NY BUY  IG only    paper close       nan  IG close   26023.7  ad_tue_wed
  18:50 NY BUY  IG only    paper close       nan  IG close   26069.5  ad_tue_wed
  agreement: 0/9 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-25 New York
  00:20 NY SELL IG only    paper close       nan  IG close   25850.4  ad_tue_wed
  06:50 NY SELL IG only    paper close       nan  IG close   25511.2  ad_tue_wed
  09:30 NY SELL IG only    paper close       nan  IG close   25160.8  ad_tue_wed
  17:15 NY BUY  IG only    paper close       nan  IG close   25969.3  ad_tue_wed
  17:30 NY BUY  IG only    paper close       nan  IG close   25989.2  ad_tue_wed
  17:35 NY BUY  IG only    paper close       nan  IG close   26003.3  ad_tue_wed
  17:40 NY BUY  IG only    paper close       nan  IG close   26008.1  ad_tue_wed
  17:45 NY BUY  IG only    paper close       nan  IG close   26015.4  ad_tue_wed
  agreement: 0/8 signals on both feeds while the IG runner was live (0 paper signals fell outside its sessions)
```

25 Nov: ig_live both 0 / paper-only-while-live 0 / IG-only 9; ig_demo both 0 / paper-only 0 / IG-only 8. All skipped ad_tue_wed. No fills on either book (ig_live trades.csv last row 20 Nov, ig_demo 12 Nov).
Both runners' last_error.txt still end `error.public-api.exceeded-account-historical-data-allowance`.

Running tally (from 2026-11-05): ig_demo agree 2/36, mean slippage -0.46 pts over 5 fills; ig_live agree 1/42 by script (2/43 adjusted), mean slippage +2.07 pts over 6 fills. Combined 3/78 by script (4/79 adjusted) — below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)

## 2026-11-27 (NY) — checked 2026-11-28 ~09:05 UTC (paper bars not yet pushed)
```
IGNITION v1.1 — paper feed vs IG (ig_live), 2026-11-27 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
IGNITION v1.1 — paper feed vs IG (ig_demo), 2026-11-27 New York
  paper feed has no bars for this day yet — run after the 07:23 paper update
```
data_nq_cache/nq_5m.csv still ends 2026-11-26 23:55 UTC after a 10-minute wait and re-pull (the paper run has pushed ~09:17 UTC on recent days). Agreement for 27 Nov pending.

New fills on 27 Nov from trades.csv:
- ig_live: BUY opened 04:30 UTC, paper_entry 26700.30, IG fill 26701.30 (+1.0 pts), exit 26742.50 ig_limit, +41.20 pts.
- ig_live: BUY opened 20:15 UTC, paper_entry 26705.50, IG fill 26706.90 (+1.4 pts), exit 26704.90 session_end, -2.00 pts.
- ig_demo: BUY opened 2026-11-27T02:49, paper_entry nan, IG fill 26627.70, exit 26652.60 ig_limit, +24.90 pts — no signal price recorded, so no slippage figure.
Both runners' last_error.txt still end `error.public-api.exceeded-account-historical-data-allowance`.

Running tally (from 2026-11-05; 27 Nov signals not yet counted): ig_demo agree 2/36, mean slippage -0.46 pts over 5 fills; ig_live agree 1/42 by script (2/43 adjusted), mean slippage +1.86 pts over 8 fills (-0.6, -1.6, +1.5, +2.9, +7.4, +2.9, +1.0, +1.4). Combined 3/78 by script (4/79 adjusted) — below 50% past the 10-signal mark. (Sign convention: positive slippage = against us.)
