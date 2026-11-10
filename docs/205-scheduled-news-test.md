# 205 — Scheduled news through the standard test (10 Nov 2026, 05:05)

DK 04:56: "you're not reacting to the news each day ... it's like being blind to the trading environment."
Code `src/events_test.py`, results `runs/gate/events_test.txt`. Events known in advance: 214 scheduled Fed (FOMC) decision days 2000-2026
(`runs/fomc_dates.txt`, from eco3min.fr) and US jobs-report days (first Friday — an approximation). Same honest daily simulator as docs 202-203.

## 1. Pre-Fed drift as a book (Lucca & Moench 2015): buy US indices at the close before a Fed day, sell at the Fed-day close — FAILED
Pooled n856 +0.081 ATR (t 2.8) vs -0.036 on an average day — but it is all 2000-2012 (+0.20); 2013-2026 about zero (-0.08 to +0.08),
last 3 years negative on all four indices (-0.07 to -0.35). The published effect has faded since publication.

## 2. Should the daily books avoid Fed / jobs days? — NO
First cut ("an event fell inside the trade") showed the dip-buyers losing on event trades (e.g. Stochastic -0.39 vs +0.25). That was a
MEASUREMENT ARTEFACT, caught before use: losing trades are held longer, so they contain more event days. Re-tested with what is known
at entry ("a Fed or jobs day is due within 1/2/3/5 trading days"):
| Book | Event within 1-3 days of entry vs not | Walk-forward 'skip' (out of sample) |
|---|---|---|
| RSI2 #51 | +0.11 to +0.25 vs +0.24 to +0.27 — no consistent difference | worse in every version (+184 -> +168 to +180) |
| Stochastic #61 | -0.06 to +0.11 vs +0.18 to +0.20 | worse (+299 -> +252 to +271) |
| Double 7s | -0.07 to -0.21 vs +0.15 to +0.19, both halves | 1-day window only: +253 -> +268 (+6%); others worse — too small to trust |
| Turn of quarter | better with an event near (+0.36 vs +0.21) | no change |
| US close -> Europe | about the same | no change |
Verdict: scheduled news is not a reason to switch any running book off; the books keep trading through it. (The dip-buyers are in effect
the system's reaction to news: they buy the sell-offs that news causes, in rising markets.)

## Unscheduled news (wars, tariffs, crashes)
No clean headline history to test against, so it cannot be a profit rule. Shocks do show up in prices and VIX, and doc 201 found that
skipping high-VIX periods does not help the dip books either.
