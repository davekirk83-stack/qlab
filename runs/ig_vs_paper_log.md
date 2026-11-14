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
