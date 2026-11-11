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

## Part 2: intraday, the way the champions traded (11 Nov, morning)

**Set-up.**
- **Data:** 5-minute bars, cash session only.
- **Costs:** IG's spread as the round-trip cost.
- **Exits:** flat by the session close.
- **Markets:** US Tech 100, US 500 and USD/JPY have about 1 year of data. Wall Street, Germany 40 and gold (IG prices) have about 7 months. Gold from Dukascopy covers 2021–2026.
- **R** is the session's 10-day average range.

**Scripts:** `src/champions_intraday.py` and `src/champions_intraday_refine.py`. **Output:** `runs/gate/champ/intraday_*`.

### Larry Williams' volatility breakout works intraday
**Rules:**
- **Entry:** buy stop at the open + k × the previous session's range, and sell stop at the open − k × that range.
- **Stop:** the other side of the bracket.
- **Exit:** at the close.

**US Tech 100.** Positive at every k with the bracket stop:

| k | n/yr | Pts/trade | R | Win | First 60% / last 40% | Months + |
|---|---|---|---|---|---|---|
| 0.3 | 242 | +18.8 | +0.056 | 51% | +0.076 / +0.027 | 10/14 |
| **0.4** | 211 | **+37.1** | **+0.095 (t 2.47)** | **60%** | +0.113 / +0.069 | 9/14 |
| 0.5 | 195 | +28.8 | +0.075 | 55% | +0.073 / +0.078 | 10/14 |
| 0.6 | 172 | +20.3 | +0.053 | 52% | +0.059 / +0.044 | 7/14 |
| 0.7 | 148 | +18.3 | +0.056 | 48% | +0.082 / +0.018 | 9/14 |

**USD/JPY.** Positive at every k, and both halves positive at every k: +0.085 to +0.108 R, with k 0.5 giving 182 trades a year at +0.092 R.

**Other markets:**
- US 500: positive only around k 0.5 (+0.053 R).
- Wall Street and Germany 40: mixed, with only 7 months of data.
- Gold 2021–26: flat.

### Other set-ups
- **Crabel's stretch breakout** fails with his tight stop at the open (17% win). With the stop at twice the stretch it turns positive on US Tech 100: +11 to +18 points, 46–54% win, both halves positive, 11 of 14 months positive at 2×.
- **Crabel's 30-minute opening-range breakout and his NR4/NR7 filters** come out small positive on GBP/USD, USD/JPY and gold. That is a good sign, but the samples are small.
- **Raschke's 80-20** does not work intraday at these stops.

**Next:** build the Williams breakout into the IG demo runner on US Tech 100 and USD/JPY. It would use bracket working orders at the open, a one-cancels-the-other fill, and flat at the close. That is about 375 trades a year between the two markets.
