# 222 — The assessment back to 1900 (10 Nov 2026)

DK 11:22 "extend your overall assessment back to 1900"; 11:23 "since 2001 has been a perversion of the stock markets ... modern monetary policy";
11:30 "the modern era is the most relevant, but it is also worth looking back to previous long-term bear markets".
Data: S&P 500 daily 1928–2026 (Yahoo; close-only before 1962), Shiller monthly S&P composite + GS10 1871–Sep 2023 (data_hist/).
Method (`src/hist_study.py`, runs/gate/hist_study.txt, hist_longbear.txt): same rules as our books; ATR from close-to-close changes; decide at a close,
trade at the NEXT close; IG US 500 spread; funding from each era's rate (longs pay rate + 2.5%, shorts earn rate − 2.5%). One market (S&P 500) only.

## Our books by era (mean per trade, t, share of years positive)
| Book | 1928–45 | 1946–81 | 1982–2000 | 2001–26 |
|---|---|---|---|---|
| RSI(4) dip, above 200d | +0.49, 62% | **−0.09, 46%** | +0.96 (t 3.7), 79% | +0.42, 65% |
| TPS ladder, above 200d (% budget) | +0.09, 81% | **−0.04, 54%** | +0.11, 84% | +0.15 (t 3.8), 83% |
| Turn of the month | +0.49 (t 2.4), 72% | +0.49 (t 3.1), 69% | +0.06, 47% | −0.03, 42% |
| Santa | +3.73 (t 5.4), 94% | +1.45, 71% | +0.76, 58% | +0.42, 68% |
| Dips taken BELOW the 200-day (what the regime rule skips) | −0.38 | −0.33 | +0.09 | −0.16 |
| SHORT breakdown below 200d | **+1.54** | **+0.75** | −0.73 | −0.37 |
| SHORT bear-rally fade | −0.45 | −0.03 | +0.44 | +0.21 |
| SHORT TPS short ladder | −0.30 | −0.03 | −0.05 | +0.00 |
| SHORT 50/200 trend | −1.13 | +0.12 | −0.53 | −1.63 |

## What it says
1. **DK's point holds.** The dip books' edge is an era effect: strong since 1982 (falling rates, central banks backstopping every fall), absent in
   1946–81 (high rates, the 1970s bears). If a 1970s-type regime returns, the dip books may stop earning. The live tiers / stops are the protection.
2. **The regime rule (no dips below the 200-day, doc 220) holds in three of four eras** (skipped dips: −0.38, −0.33, −0.16; only 1982–2000 slightly +).
3. **Turn of the month was a strong effect before 1982 and has faded since** on the S&P alone (it holds better across our 6 markets — stays WEAK).
4. **Shorting breakdowns worked in the old long bears** (1928–45 +1.54, 1946–81 +0.75) and has failed since 1982 — exactly the 'modern monetary policy' split.
5. **Monthly 10-month-average timing (long, or flat earning the bond rate) beat buy & hold in every era except 1982–2000 and cut the worst fall
   sharply** (1930–45: 78% -> 22%; 2001–23: 49% -> 19%). Going SHORT below the average made less than going flat in every era.

## Monthly 1871–2023 (total return, per year; worst fall)
| Era | buy & hold | 10-month timing, long/flat | long/short |
|---|---|---|---|
| 1871–1899 | +6.4% (33%) | +7.6% (12%) | +4.6% (33%) |
| 1900–1929 | +9.9% (34%) | +12.1% (34%) | +10.7% (37%) |
| 1930–1945 | +4.4% (78%) | +10.6% (22%) | +8.9% (65%) |
| 1946–1981 | +10.2% (39%) | +11.5% (9%) | +8.9% (25%) |
| 1982–2000 | +16.8% (26%) | +15.8% (15%) | +11.7% (22%) |
| 2001–2023 | +7.4% (49%) | +10.2% (19%) | +9.9% (32%) |
Bear markets since 1900 (>= 20%): 1902–03, 1906–07, 1909–21 (140 months down), 1929–32 (−85%, 267 months to recover), 1961–62, 1968–70, 1973–74
(−43%), 1987, 2000–03, 2007–09 (−51%), 2022.

## A dormant long-bear short (fixed in advance)
Switches on only in an ESTABLISHED long bear: 200-day average falling for 60 days AND >= 15% below the 1-year high (17% of days since 1928: 1930s 54%,
1970s 20%, 2000s 34%, 2010s 0%). Breakdown short (20-day low below the 200-day, exit 10-day high) in that state: n 123, +0.394, t 0.73 — but its
profits come exactly in the big bears (1930–32 +62, 1941–42 +33, 1970 +23, 2001–02 +27, 2008 +19) with small losses in between (2018–23 −12).
Crash-insurance profile, not a statistical edge. Long dips inside an established long bear: −0.08 (avoid; the regime rule already does).
