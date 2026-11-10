# 209 — The other narrow fails (10 Nov 2026)

DK 07:24: "work on those other narrow fails". Script `src/refine_nearmiss2.py`, results `runs/gate/refine_nearmiss2.txt` (t* 3.73, 266 ideas).

## US strong close -> Europe (USCL) — data fault found, real fix being tested
- Book still PASSES on paper (DAX+FTSE open->close: n1153, t 6.76, 24/27 years), but the profit is almost all FTSE (+0.23 ATR/trade) vs DAX +0.03.
- Yahoo's FTSE "open" is the previous close on 95% of days, so the test gave FTSE the overnight jump that a trade at the European open can't get.
  On DAX (clean opens) the open->close part is close to nothing. The real effect is likely the overnight jump itself.
- Fix under test (`src/uscl_timing.py`): buy DAX/FTSE on IG at the US close (IG quotes them out of hours) and sell at the European open or close next day,
  on Dukascopy minutes for the ~250 signal days since 2012, at IG out-of-hours spreads + one night's funding. Download running (Dukascopy throttling).
- Other variants: hold 2 sessions worse (t 3.14); only when US 500 below its 200-day PASS (t 5.63, but same FTSE fault); trading the US indices themselves next day FAILS (−0.047).

## Halloween (HALLO) — still WEAK
- Base (Nov–Apr month-ends, hold 21 days): +0.452 ATR, t 2.91, 17/27 years, but does not beat random 21-day long holds (random95 +0.235 is not the issue; t is).
- + 200-day filter worse (t 2.15); whole-season single hold t 1.76 (5 trades a year). The return is mostly ordinary equity drift. Stays demo-only, WEAK.

## Multiple days down (MDD) — no extra edge
- The MDD dips that RSI(4) does not already catch: +0.072 ATR, t 1.70, last 5y −0.022. MDD's value is entirely the dips RSI(4) already takes. Closed as a separate book.

## Data note
- Because of the FTSE open fault, any "next open" test on FTSE was really a close entry. The live runner uses IG's own prices, so live/demo trading is unaffected.

## Result of the timing test (10 Nov 08:40, `src/uscl_timing.py`, runs/gate/uscl_timing.txt) — USCL CLOSED
Dukascopy DAX minutes on 190 signal days 2013–2026, IG out-of-hours spread + one night's funding:
- buy DAX at the US close (15:50 NY) -> sell at the European open: −0.065 ATR/trade, t −1.56, 5/14 years +
- buy at the US close -> sell at the European close: −0.060, t −1.16
- European open -> close (the old rule, real opens): −0.001, t −0.02
The paper edge was a data artefact: Yahoo's FTSE "open" is the prior 16:30 close, so the old test counted FTSE's move from 16:30 on the
signal day — before the 21:00 US close that defines the signal (look-ahead). Removed from the demo runner; never on live.
