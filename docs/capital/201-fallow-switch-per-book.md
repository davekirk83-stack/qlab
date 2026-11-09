# 201 — Worst periods per book, and whether switching them off helps (9 Nov 2026, 23:15)

DK 23:09: "Every book should be studied for its worst periods/timeframes and adjusted accordingly, to suit optimal periods and conditions."
Method (`src/condition_switch.py`, `runs/gate/condition_switch.txt`): conditions known in advance — month, weekday, VIX band at the previous
close, and the New York hour for intraday books. Walk-forward: for each year (daily books) or month (intraday books) the conditions to skip
are chosen only from earlier periods (bucket >= 15 earlier trades with a negative average; >= 8 earlier years / 4 months). Then that period is
traded with the switch, and compared with trading every signal.

| Book | Every signal: total / periods + / last 5 | With the switch | Verdict | Switched off now |
|---|---|---|---|---|
| TPS ladder indices+gold | +222 / 15 of 18 / +77 | +100 / 15 of 18 / +58 | worse — run always | (Feb, Jul) |
| TPS ladder coins (monthly WF) | +417 / 24 of 31 | +313 / 22 of 31 | worse — run always | |
| RSI(2) pullback | +183 / 13 of 18 / +91 | +105 / 14 of 18 / +25 | worse — run always | |
| Double 7s | +197 / 12 of 18 / +53 | +62 / 9 of 18 / -21 | worse — run always | |
| 12-month momentum | +274 / 10 of 19 / +91 | +197 / 9 of 19 / +41 | worse — run always | |
| Halloween Nov-Apr | +309 / 14 of 19 / +87 | +118 / 12 of 19 / +57 | worse — run always | |
| **Trend 100-day (IG quarterly)** | +290 / 11 of 19 / **-95** | **+332** / 11 of 19 / **+39** | **better — use the switch** | Oct, Dec, Feb, Mar, Apr; Thursdays; VIX 15-20 and > 30 |
| **AuclairsDad Ignition (regime+coil), all hours** | +22 / 6 of 10 | **+27 / 7 of 10** | **slightly better — use it** | 02:00 NY hour; Tue, Wed; VIX 20-30 |
| Ignition v1.1 US hours | +18 / 7 of 10 | +14 / 7 of 10 | no gain — run always | |
| Gold London breakout | 3 months of walk-forward only | — | too early | |
Units: ATR units per trade summed (TPS: % of episode budget summed).

**Finding:** for most books the "bad months / days / VIX levels" seen in hindsight are noise — choosing them from the past and skipping
them in the future gives LESS money, not more. Only the trend book (and, a little, the AuclairsDad stack) has bad conditions that repeat.
Those two get their switches; every other book runs every signal. Re-check yearly as history grows (intraday books need more data —
5 years of gold and US Tech 100 minute data is downloading).
