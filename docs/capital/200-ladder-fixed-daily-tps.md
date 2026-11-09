# 200 — The ladder, fixed: a daily scale-in ladder (Connors TPS) passes (9 Nov 2026, 23:10)

DK 23:03: "I still think we can fix our range / ladder book with more work. Look online for other examples of this kind and how they are made
to work." What the working published ladders share, and our 15-min ladder lacked:
1. **The right timeframe** — mean reversion exists on DAILY equity-index bars (Connors & Alvarez; our own RSI(2)/Double 7s results), not on
   15-min bars after costs (doc 194-195).
2. **A regime gate** — only above the 200-day average (grid literature: Taranto 2020 — the ruin case is a steady trend through the levels).
3. **Finite, restartable episodes with a kill rule** (Taranto; Quantpedia grid primer) — exit on RSI(2) > 70, max 30 days, -15% on average cost.

Rules (TPS, Connors & Alvarez 2009): above the 200-day and RSI(2) < 25 two closes running -> buy 10% of the episode budget at the close;
each later close below the last entry adds 20%, 30%, 40%; exit at the close when RSI(2) > 70. Decisions on the close that just printed, filled
at that close + costs. Code `src/ladder_daily_tps.py`, results `runs/gate/ladder_daily_tps.txt`.

| Version | Episodes | Mean per episode (of budget) | t | Win | Worst | Years + | Last 5y | Last year |
|---|---|---|---|---|---|---|---|---|
| **TPS ladder, 7 indices + gold (IG)** | 1558 (60/yr) | +0.19% | **5.0** | 89% | -19% | **21/26** | +0.24% | +0.42% |
| same entry, all-in at once | 1558 | +0.28% | 4.9 | 70% | -20% | 20/26 | +0.44% | +0.72% |
| **TPS ladder, 10 coins spot (Revolut X)** | 295 (59/yr) | **+1.18%** | 3.3 | 89% | -23% | 3/5 | +1.18% | +0.12% |
| coins, all-in at once | 300 | +0.43% | 0.9 | 61% | -31% | 3/5 | | |
Neighbourhood (RSI 20/30, max 20/45 days, kill -10/-20%): every variant positive on both indices and coins (t 2.6 - 5.4).
- On indices the full-sample t (5.0) clears the multiple-testing bar (3.5) — the first ladder to do so; 21 of 26 years positive.
- On coins the LADDER is what makes it work (all-in: +0.43%, t 0.9; ladder: +1.18%, t 3.3) — the scale-in is the edge there. Spot,
  long only: fits the Revolut X approval of 5 Nov (10% of the book per episode, at most 10 open) — a candidate to fund instead of the dead
  15-min range book, after a dry run.
Sources: Connors & Alvarez, *High Probability ETF Trading* (2009) via TuringTrader's TPS page; Taranto & Khan (2020) via MQL5 article 21833;
Quantpedia "A Primer on Grid Trading Strategy".
