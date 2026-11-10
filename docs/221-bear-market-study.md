# 221 — Study: corrections, crashes and bear markets, and the short side (10 Nov 2026)

DK 11:17: "open up a study focusing specifically on corrections, crashes and bear markets, and how to improve our shorting books."
`src/bear_study.py` (runs/gate/bear_study.txt, bear_study_gated.txt). New data: US fed funds monthly 1999–2026 (data_daily/FEDFUNDS.csv) for
REAL IG short funding: a short is credited the benchmark minus the 2.5% admin fee (pays when rates < 2.5%, earns when above).

## A. What bear markets look like (drawdowns >= 10% from a closing high, 2000–2026)
- US 500: 8 episodes — bears 2000–02 (−49%, 637 days down, 1,166 to recover), 2007–09 (−57%), 2022 (−25%, 195 days); crash 2020 (−34% in 23 days,
  recovered in 103); corrections 2015–16, 2018 (x2), 2025 (−19% in 34 days, back in 55).
- US Tech 100: 17 episodes incl. 2000–02 (−83%, 3,292 days to recover), 2022 (−36%), crashes 2020 and 2025; a −14.7% correction is under way now (since 6 Oct).
- DAX 10, Wall St 9, FTSE 8 episodes (FTSE 2018–20 bear −37%).
- **Key facts for shorting:** bear markets last 6–30 months but contain violent rallies (biggest rally inside the fall: 14–53% in bears);
  crashes are fast (20–35 days) and recover fast (2–6 months); corrections recover in 1–5 months. Shorts must survive those rallies and be quick in crashes.

## B. Short books (rules fixed in advance, next-open in/out, IG spreads, real short funding) — standard test
| Book | n | mean | clustered t | full years + | last 5y | by regime (US 500 at signal) | verdict |
|---|---|---|---|---|---|---|---|
| B1 bear-rally fade (below 200d, RSI(4) > 75) | 472 | +0.044 ATR | 0.51 | 10/23 | −0.207 | BEAR +0.05, SHOCK +0.31, BULL-CALM −0.42 | FAIL |
| B2 trend short (50/200 cross) | 103 | −0.641 | −3.17 | 5/22 | −0.746 | loses in every regime | FAIL |
| B3 breakdown short (20-day low below 200d) | 470 | −0.378 | −2.33 | 4/26 | −0.994 | BEAR +0.24, SHOCK −0.81, BULL −0.9/−1.0 | FAIL |
| B4 crash continuation (−6% week, VIX > 25, 3 days) | 463 | −0.227 | −2.01 | 4/19 | −0.265 | crashes snap back | FAIL |
| B5 failed rally (3 up closes into the 20d avg) | 542 | −0.064 | −0.89 | 11/23 | −0.018 | | FAIL |
| B6 TPS short ladder below 200d | 748 | +0.158% | 1.78 | 15/25 | −0.566 | SHOCK +0.77, BULL −0.2/−0.25 | FAIL (adds to portfolio) |

## D. Gated to the US 500 itself being below its 200-day (mirror of the long-side regime rule, doc 220)
| Book | n | mean | clustered t | full years + | last 5y | portfolio | verdict |
|---|---|---|---|---|---|---|---|
| G1 bear-rally fade | 355 | +0.133 ATR | 1.30 | 11/19 | −0.056 | +12 in the core's 10 worst months | FAIL |
| G3 breakdown short | 362 | −0.230 | −1.10 | 4/22 | −1.132 | | FAIL |
| **G6 TPS short ladder** | 569 | **+0.283%** | 2.58 | **15/22** | −0.821 | **ADDS: mean/month +3.25 vs +2.22, worst 12m −48 vs −57** | WEAK-ish: fails t, last 5y and random (random shorts in the same regime earn the same) |
G6 by year: 2001 +43, 2008 +88, 2011 +37 … but 2023 −10, 2025 −24, 2026 −32 — the recent V-shaped recoveries punish shorts.

## Conclusions
1. Shorting index downtrends only works in old-style long bears (2000–02, 2008, 2011). Since 2020 every sell-off has reversed fast (2020, 2022 rallies,
   2025, 2026): every short book lost in the last 5 years.
2. What a short earns in a bear regime is mostly 'being short while the US 500 is below its 200-day' (random entries do as well) — a regime bet,
   not a timing edge.
3. The best use of bad markets for us is already in place: the dip books earn most in SHOCK / nervous regimes (+0.6 to +0.7 ATR) and now sit out
   BEAR regimes (doc 220).
4. Candidate for demo measurement only: G6 (TPS short ladder while the US 500 is below its 200-day) — the one short that improves the portfolio.

## On the demo (DK 11:21 "Yes please")
`TPSS` book in `src/ig_daily_books.py`, DEMO ONLY (the live book list comes from config/live_pot.json, which does not include it): short ladder
mirror of TPS — market below its 200-day AND US 500 below its 200-day, RSI(2) > 75 on two closes -> short 10% of the budget at the next open;
each higher close adds 20/30/40%; exit RSI(2) < 30, 30 days, or 15% above the average short price; catastrophic stop 20% above entry.
Shorts now supported in the runner (direction SELL, closed with BUY, P&L by side). Replay of the demo runner 2019–26: 179 short rungs, −£42 at
intended size (2020 +0.7, 2022 −1, 2023 −7, 2025 −15, 2026 −20) — consistent with the study: recent sell-offs reversed fast. Measuring forward.
