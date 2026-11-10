# 208 — Near-misses refined (10 Nov 2026)

DK: "refine the ones that failed narrowly; look for superior published versions. Any that failed narrowly we continue to test and work on."
Script: `src/refine_nearmiss.py`, results `runs/gate/refine_nearmiss.txt`. t* = 3.72 (258 ideas).

## Turn of the month: now PASS, in the demo
- Original rule (buy the close of the last business day, hold 3 days, stop 5 ATR) on the **6 markets the runner trades** (US500, NQ, Dow, DAX, FTSE, gold):
  n1854, 69/yr, +0.156 ATR, **t 4.42, 17/27 years +**, last 5y +0.082, last year +0.439, costs x1.5 +0.137, random95 +0.039 → PASS.
- The doc-207 fail (16/27) included Japan 225 and Russell 2000, which we don't trade (both near zero / negative).
- Published McConnell-Xu window (in at day −2) was *worse* (t 1.60): the last day of the month is weak in 2000–2026 data. Day −5 entry t 3.05; exit day 2 or 4 worse than day 3. Kept the original.
- Demo: **TOQ replaced by TOM** (TOM contains every quarter end). 400-day runner replay: TOM 84 trades +£45 (TOQ was 22 trades +£26); book £500 → £653 (was £629).
- Still borderline (17/27 is one year above the bar; 5 indices alone 16/27). On watch.

## Multiple days down
- 6 traded markets: PASS (t 3.89, 18/27). But as one book with RSI(4): 67 trades/yr at +0.182 = 12.2 ATR/yr vs RSI(4) alone 46 × 0.290 = 13.3 ATR/yr. More trades, no more profit → not added. Stays on the list.

## Overnight — data fault found
- Yahoo FTSE "open" equals the prior close on 95% of days (SPX/RUT ~25% before 2010), so earlier overnight tests were partly broken. Re-run without bad opens and at IG's real spreads + buffer:
  every night −0.013; after a down close −0.007; after RSI(2)<10 above 200d +0.015 (t 1.55, 16/26 years). Gross overnight drift (1–5bp) is about equal to one night's IG funding (~2.3bp) + spread. Not tradable on spread bets; stays dead unless a no-funding route appears.

## 12-month / multi-horizon trend (TSMOM)
- 28 markets, monthly, funding charged: 12m only +1.3%/yr t 0.24; published 1/3/12m vol-scaled blend −1.8%/yr. Crisis hedge visible (2008 +13–24%, 2022 +1–19%) but no edge after spread-bet funding on Yahoo continuous futures. WEAK.

## Demo book list now
RSI4, TPS, TOM, SANTA, HALLO (US/EU indices + gold where tested), USCL, GOLDLDN. Runner replay ~360 trades per 400 days (~0.9/day across books).
