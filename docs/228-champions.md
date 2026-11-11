# 228: Copying the champions (11 Nov 2026)

DK, 06:47: "copying the techniques of the most successful publicly listed traders… If they are survivors then that is a good thing."

**Method.** Each trader's published signature set-up was coded from their own book: Larry Williams (1987 Robbins World Cup), Linda Raschke, Toby Crabel and Richard Dennis's Turtles.
- **Markets:** daily bars, 2000–2026, on 16 IG markets at IG's real costs.
- **Refinements (fixed in advance):** the trader's own exits, including Williams' "first profitable open"; the 200-day regime; long-only; and choosing markets walk-forward, so each year trades only the markets that were positive in earlier years.
- Connors' RSI(2) and TPS are already live and are not repeated here.

**Script:** `src/champions.py`. **Output:** `runs/gate/champ/`.

| Set-up | Best version | n/yr | Mean R | Years + | Last 5y | Walk-forward markets |
|---|---|---|---|---|---|---|
| **Crabel NR7 breakout** | first profitable open, both sides | 519 | **+0.023, clustered t 3.13** | **18/26** | −0.001 | **+0.041, 15/19 years** |
| Raschke Holy Grail | 5 days, both sides | 14 | +0.053 | 15/26 | +0.005 | +0.078, 10/19 |
| Raschke Holy Grail | 10-day trail, long + 200d | 4 | +0.084 | 8/24 | +0.552 | n = 105, too few |
| Turtles System 1 | 10-day exit, long + 200d | 74 | −0.003 | 14/26 | −0.138 | +0.049, 11/19 |
| Raschke 80-20 | 3 days, both + regime | 273 | +0.012 | 13/26 | +0.007 | +0.038, 11/19 |
| Williams Oops! | first profitable open, both | 410 | +0.007 | 14/26 | −0.014 | +0.004 |
| Raschke Turtle Soup | 5 days, long + 200d | 36 | −0.013 | 13/25 | −0.080 | +0.001 |
| Williams volatility breakout | first profitable open, both + regime | 635 | −0.036 | 7/26 | −0.043 | −0.019 |

**Verdict.**
- **Crabel's NR7** is the strongest copy: real over 26 years (clustered t 3.13, 18 of 26 years positive). Choosing markets walk-forward lifts it to +0.04 R with 15 of 19 years positive. It has gone flat over the last 5 years.
- The **Holy Grail** works long-only in an uptrend recently (+0.55 R over the last 5 years), but on only about 4 trades a year.
- The rest are about breakeven at daily resolution with IG costs.

These are mostly day-trading methods, built for intraday entries and exits on low-cost futures. The next step is to code them on the 5-minute data, as done for AuclairsDad in doc 227:
- Crabel's opening-range breakout following an NR7 day;
- Williams' breakout from the open;
- Raschke's 80-20 and Holy Grail on intraday bars.
