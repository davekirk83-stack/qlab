# 204 — Daily books on the IG demo (10 Nov 2026)

DK 04:32: "Help me make money, that's the goal." The books that passed the standard test (docs 200-203) now trade the IG DEMO account
automatically, so they get real fills. `src/ig_daily_books.py`, `.github/workflows/ig-daily.yml`. Demo only (the script refuses IG_MODE=live).

| Book | Rule (same as its backtest) | Markets |
|---|---|---|
| RSI2 (#51) | above 200-day, RSI(2) < 5, below 5-day avg -> buy the close; out on a close above the 5-day avg, 10 days max, stop 3 ATR | US 500, US Tech 100, Wall Street, Germany 40, FTSE 100, gold |
| TPS ladder | above 200-day, RSI(2) < 25 two closes -> rungs 1:2:3:4 on lower closes; out RSI(2) > 70, 30 days, or 15% below avg | same six |
| Turn of quarter (#39) | last business day of the quarter -> hold 3 days, stop 5 ATR | five indices |
| Santa (#37) | first trading day of 22-24 Dec -> hold 7 days, stop 5 ATR | five indices |
| Halloween | month-end before Nov-Apr -> hold 21 days, stop 8 ATR | five indices |
| US close -> Europe (#47) | US 500 closed top 10% of range and +1% -> buy Germany 40 and FTSE 100 at the open, sell at the close, stop 2 ATR | DAX, FTSE |

Jobs: 08:05 London (US close -> Europe entries), 16:10 London (DAX/FTSE exits + entries), 15:40 New York (US indices + gold). "At the close" =
~20 min before the cash close using IG's live price. History from Yahoo; today's bar = Yahoo's previous close x IG's change on the day.

Sizing: 1% of a £500 sub-book at the stop (TPS: whole ladder loses 2% at the kill); 5x exposure cap. IG's minimum (0.01/pt) is often bigger
than that on US Tech 100 and Wall Street, so the demo places the minimum and the sub-book COUNTS each result at the intended size.

Checks before switching on:
- Signals equal the backtest definitions on 2000-2026 data (RSI2 flags 162/162 US 500, 148/148 DAX and gold); today's-bar construction
  reproduces the full-history indicators exactly.
- Replay through the runner's own code, intended size: Nov 2021 - Nov 2023 (incl. the 2022 bear market) £500 -> £533;
  Nov 2025 - Nov 2026 £500 -> £661 (an unusually good year for dip-buying; the long-run backtest averages are much lower). TESTED (backtest).
- The first replay found min stakes made the TPS ladder ~70x the 2% rule on Wall Street / US Tech 100 — fixed by counting at intended size.
- Dry run on GitHub against the demo, 10 Nov 04:42: login, Yahoo data and IG prices all worked; no signals (US 500 RSI(2) 72, gold below its 200-day).

Next scheduled entries known in advance: Halloween at the 30 Nov close; Santa 22 Dec; turn of quarter 31 Dec. Dip books trade when dips come.
Not included yet: trend / 12-month momentum (IG quarterly bets), Double 7s (same family as RSI2), crypto books (Revolut X).
