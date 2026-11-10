# 207 — The external reviewer's frequency ideas, tested (10 Nov 2026, 05:15)

Same simulator and checks as docs 202-203 (`src/review_ideas_test.py`, `runs/gate/review_ideas_test.txt`); t* = 3.71 (246 ideas tried).
| Verdict | Idea | Trades/yr | Mean (ATR) | t | Years + | Last 5y | Last yr | Costs x1.5 |
|---|---|---|---|---|---|---|---|---|
| **PASS** | RSI(4) < 25 above 200MA, exit RSI(4) > 55 | 46 | +0.290 | 5.46 | 19/26 | +0.34 | +0.35 | +0.27 |
| **PASS** | RSI(2) < 10 above 200MA, exit > 5MA (Connors base) | 59 | +0.175 | 4.62 | 18/26 | +0.22 | +0.38 | +0.15 |
| PASS except t | MDD: 4 of 5 days down, < 5MA, above 200MA | 57 | +0.121 | 3.40 | 19/27 | +0.18 | +0.36 | +0.10 |
| FAIL (16/27 years = 59%, just under 60%) | Turn of the month: last day -> day 3 | 91 | +0.125 | 3.97 | 16/27 | +0.05 | +0.41 | +0.10 |
| FAIL | Overnight close -> next open: every day / above 200MA / after 2 down days / after RSI(2) < 10 | 108-1985 | -0.03 to -0.05 | negative | 0-7/27 | | | |
Overnight: the published overnight drift is smaller than IG's round-trip cost plus a night's funding on every version. (Yahoo's cash-index
opening prices can be stale, which also weakens this test — but the cost arithmetic alone sinks it.)

At the next open (how the runner trades): RSI(4) n1262 +0.275 t 5.28 19/26; RSI(2) < 10 +0.146 t 3.92; TOM +0.092 t 2.58.
Monthly correlation with the RSI(2) #51 book: RSI(4) 0.72, RSI(2) < 10 0.78, TOM 0.12 — same family except TOM.
**Decision:** the demo's RSI(2) #51 book is replaced by RSI(4) < 25 (same family, stronger at the open, ~60% more trades). One book per
family stays the rule, so RSI(2) < 10 and MDD are not added. Replay of the last 400 days through the runner: RSI4 57 trades vs RSI2 41.
Not testable yet: FX/commodity carry (needs interest-rate history; on IG spread bets the carry is paid through overnight funding minus IG's
admin fee, which takes much of it). 12-month momentum stays WEAK — a demo candidate as a crash diversifier (needs IG quarterly bets).
