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
