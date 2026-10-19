# 92 — Ignition v1: AuclairsDad's engine on twelve months of Nasdaq, registered as a paper book (19 Oct 2026)

Closes the loop opened in doc 84 and reopened in doc 87 at DK's insistence (*"push further on him… it's in an area we are not currently operating and would help diversify our books"*). Built from his own blueprint and panel (doc 90). Code `src/coil.py` (study), `src/paperbook7.py` (the book); logs `runs/coil_nq_12mo.log`, `runs/flow_nq4_12mo.log`, `runs/ignition_dd.log`.

## Data
Dukascopy USATECHIDXUSD ticks, 15 Oct 2025 – 16 Oct 2026: 331,102 minutes → 66,250 five-minute bars, all sessions. Activity = tick count; flow = tick-rule delta (his is bar-level bid/ask volume from Sierra — same resolution, better provenance). Cost = half the quoted CFD spread each way, ~1.1 pts round trip (his future ~0.5).

## Twelve months, 5-minute bars, his gates, his exit stack (stop 45 / BE +15 / trail 1 ATR / target 9 ATR / cap 3h), governors (8/day, 3-bar cooloff, 200-pt daily cap), 5 random controls per trade
| row | n | pts/tr | t | win | PF | random | edge | months >0 | half 1 / half 2 |
|---|---|---|---|---|---|---|---|---|---|
| coil + ignition + delta share + HTF (the panel verbatim) | 272 | +2.77 | 1.3 | 74% | 1.25 | +1.54 | +1.2 | 62% | +4.1 / +1.5 |
| **ignition + delta share + HTF (no coil)** | **694** | **+3.60** | **2.6** | **74%** | **1.32** | +0.58 | **+3.0** | **85%** | **+3.1 / +4.1** |
| + channel break | 101 | +7.67 | 2.1 | 76% | 1.78 | −2.07 | +9.7 | 85% | +8.2 / +7.1 |
| raw conviction (bid/ask ≥ 1.19) + HTF | 234 | +6.08 | 2.4 | 76% | 1.63 | +1.16 | +4.9 | 69% | +5.5 / +6.6 |
| raw conviction + ignition | 87 | +8.69 | 2.1 | 77% | 2.03 | −0.14 | +8.8 | 77% | +12.1 / +5.4 |
| without HTF (both ways) | 421 | +1.73 | 1.1 | 73% | 1.15 | −1.14 | +2.9 | 69% | |
| without delta share | 1,342 | +1.24 | 1.3 | 72% | 1.10 | +0.81 | +0.4 | 85% | +2.5 / 0.0 |
| counter-HTF (fade) | 203 | −0.32 | −0.1 | 72% | 0.97 | +0.33 | −0.6 | 46% | |
| HTF + candle only | 2,193 | +1.22 | 1.8 | 74% | 1.11 | +0.71 | +0.5 | 69% | +2.5 / 0.0 |

The literal coil row weakened over the year (March–July 2026 lost); the coil only thins the trade. **Ignition + delta share + HTF alignment is the engine**: ~2 trades a day, +3.6 pts net of CFD cost (≈ +4.2 at his futures cost), PF 1.32, both halves positive, 11 of 13 months. Direction is everything: counter-HTF loses, no-HTF is random, no-delta-share is a tenth of the edge. His own long-run figures are +3.75–7.7 pts/trade at PF 1.20–1.48 — reproduced from his blueprint on his market. The 1-minute regression-regime stack from doc 90 did **not** hold on twelve months (loose stack +1.6, t 1.0; breakout path flat) and is dropped.

## The same engine on crypto (doc 90): equal to random on 18 perps with true taker delta. His edge is NQ-specific — no overlap with our books.

## Ignition v1 as a book (full replay from 15 Oct 2025, 1 MNQ-equivalent, $2/pt, $2,000)
695 trades over 254 trading days (2.7/day); **+3.59 pts/trade, 74% win, shadow +0.35 → gap +3.24**; $2,000 → $6,994; **max drawdown −30.7%**, worst day −227 pts (−$455); 10 of 13 months positive; longs +2.6 (431), shorts +5.2 (264); exits 73% breakeven, 23% stop, 3% cap; avg win +19.9, avg loss −43.2, median trade +5.6; top 5% of trades carry 135% of P&L (fat right tail from the trail and cap — rule 166 is not tripped because the median trade is positive, but the shape is noted). The −31% drawdown is the sizing: a 45-point stop on one MNQ is $90, 4.5% of the stack per trade; this is a paper ledger and the stack is a dial, but a live version would need a bigger stack or a smaller risk unit.

## Registration — "Ignition v1" (finding 157 → PROMISING, running)
`src/paperbook7.py`, state `runs/paper7_state.json`, D1 `pb7_equity` / `pb7_trades`, bars `data_nq_cache/nq_5m.csv` (committed, 12 months, 6 MB). Started 19 Oct 2026 at $2,000; watermark run clean. **Anti-leak by construction (his step 11): the book is a full replay from its start date over the committed cache every morning**, so a recalc and the live record cannot differ; a trade still open at the end of data is reported open, never booked. Each run pulls the missing Globex days from Dukascopy (yesterday is complete by 07:23 London), appends, replays. Shadow: 5 random completed bars from the trailing 30 days per real entry, same side, same stack; the verdict is REAL minus SHADOW; PASS at 300 trades (≈5 months). Kill switch: flatten=1 blocks all, flatten=2 blocks longs. Not in the monthly allocation until it passes. STEP 3e of the 07:23 task from 20 Oct.

## Method notes recorded
- Import a trader's own description before building anything (two wrong reconstructions in docs 84/86 cost a day).
- A market-specific edge is still an edge: his book diversifies ours precisely because it lives where ours do not.
- Rule 168: when an imported engine has several gates, run the ablation table on the full sample before choosing the registered form; register the row that held in both halves, not the one that matched the source's screenshot.
