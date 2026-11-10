# 217 — The standard test v3 + permanent research register; Donchian market-condition study (10 Nov 2026)

DK 10:46: "This should all be part of our new standardised testing system." 10:47: for Donchian, "a better system to know when it would most
safely apply, and when not, in terms of market conditions."

## The standard test (`src/standard_test.py`) — every book, every time
Builder contract: signals decided on the close, traded at the NEXT OPEN (entries and exits), stops on every bar, gaps fill at the open.
PASS needs all six: (1) same-day-clustered t >= t* (Šidák, n = every idea in the register); (2) year-block bootstrap 95% CI above zero;
(3) >= 60% of FULL years positive; (4) last 5 years and last 12 months positive; (5) positive at 1.5x costs; (6) beats the 95th percentile
of random entries. WEAK = positive with 2–5 passing but t or random failing. Always reported: walk-forward 'worst periods' switches
(month, weekday, VIX band, market, 3-year 'paradigm' switch; chosen from earlier years only, adopted only if they raise the out-of-sample
total and keep >= 50% of trades) and the portfolio test (risk-matched, vs the core: correlation, combined mean, worst 12 months, result in
the core's 10 worst months). Promotion needs PASS + improves the portfolio.
Every run appends a row to `runs/research_register.csv` (276 ideas before the register; t* grows with it).

## First entries
| Book | Verdict | clustered t | notes |
|---|---|---|---|
| RSI(4) dip, next open in/out | **PASS** | 4.07 | CI [+0.118, +0.422], 18/25 full years |
| Turn of the month, 6 markets | WEAK | 2.47 | positive everywhere else; adds to the portfolio (doc 216) — stays live, labelled WEAK |

## Donchian 55 long — when does it work? (IG-tradable markets, no crypto; one fixed threshold per condition)
| Condition at the signal | n | mean ATR | full years + | last 5y | verdict |
|---|---|---|---|---|---|
| no filter | 1014 | −0.106 | 8/26 | −0.036 | FAIL |
| trend efficiency ER(60) > 0.30 | 303 | +0.034 | 8/25 | +0.629 | FAIL |
| ADX(14) > 25 | 616 | −0.149 | 12/26 | +0.102 | FAIL |
| 12-month momentum > 0 | 884 | −0.089 | 7/26 | +0.029 | FAIL |
| ATR below its 1-year median | 736 | −0.162 | 7/25 | −0.030 | FAIL |
| ATR above its 1-year median | 570 | −0.096 | 9/25 | +0.181 | FAIL |
| breadth > 60% of markets above 200-day | 826 | −0.022 | 8/24 | −0.020 | FAIL |
| breadth < 40% | 143 | −0.341 | 6/23 | +0.204 | FAIL |
Crypto spot (10 coins, Oct 2021–): +1.48 ATR/trade, n 101, t 1.98, 2/4 full years, random-entry 95th +1.30 (crypto's own drift explains most of it).
Conclusion: on the markets IG can trade, no market-condition filter turns Donchian into an edge; its 2023–25 gains came from crypto, silver and gold
trends. Watch list: re-run yearly through the standard test (register keeps the history).
