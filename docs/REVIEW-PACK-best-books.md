# Trading books — review pack for an independent reviewer (10 Nov 2026)

## What I'm asking you to do

Please **try to break these results**. I'm not asking for an opinion on whether the ideas sound good. They were built and tested by one AI (Claude) that has made testing errors before (listed below). Specifically:

1. Look for **look-ahead bias**: any decision that uses a price not known at the moment of the trade.
2. Look for **overfitting**. 240 ideas were tried; are the survivors just the lucky ones?
3. Check whether the **costs, funding and fills** are realistic for an IG spread-bet account (UK) and Revolut X (crypto spot).
4. Check whether the **sizing and risk rules** make sense for a £500 account.
5. Say which books you would trust, which you would not, and why.
6. If you can, **reproduce** one or two results from the rules and code below with free daily data (e.g. Yahoo Finance).

## The account and its rules

- Live: £500 on IG UK (spread bets on indices and gold), run automatically by GitHub Actions. Separately approved, but not yet funded for these books: £500 on Revolut X (crypto spot, long only, no leverage).
- Limits:
  - risk at most 2% of the book per trade;
  - total exposure at most 5x the book;
  - a −4% day stops trading for the day;
  - a −15% drawdown, or two negative weeks, sends the book back to paper trading.
- IG's minimum stake is £0.01 per point. On a £500 book that minimum is sometimes *bigger* than the 2% risk limit allows, for example wide-stop trades on US Tech 100 and Wall Street.
- Goal: steady profit across many markets and books. The owner's eventual target is income. Honest view: the edges below are small per trade, so meaningful income needs more capital once the books are proven.

## Errors already found in this project (please check they haven't crept back)

| Error | What happened | Fix |
|---|---|---|
| Look-ahead in a 15-minute range "ladder" | Each bar's limit orders were priced from **that same bar's close** | Book switched off; it was losing when tested honestly |
| Overlapping trades counted | An intraday "spike" test booked new signals while the previous trade was still open | Re-tested one position at a time; edge roughly halved (now WEAK) |
| Inflated units | Results in R with very tight stops exaggerated small moves | All results now in ATR at entry |
| Calendar look-ahead | Turn-of-month detection used the next bar's month | Uses business-month-end offsets known in advance |
| Stale cross-market closes | Weekly reversal across indices used Friday closes from different time zones | Rejected after a same-close-time check |
| Sizing in a replay | Minimum stakes made a ladder ~70x the 2% rule | Results now counted at the size the rules intend |

## How every idea was tested (one fixed method)

**Daily data.** 2000–2026 from Yahoo, covering 7 equity indices (S&P 500, Nasdaq-100, Dow, Russell 2000, DAX, FTSE 100, Nikkei 225), gold, silver, oil, copper, natural gas, 5 FX pairs and the US 10-year note. Crypto uses Coinbase data from 2021 to 2026.

**Simulator** (code in the appendix):
- decisions only on a closed daily bar;
- entry at that close, or at the next open, or same-day open→close only when the signal is known before the open;
- the stop is checked first in every bar, and a gap through the stop fills at the open;
- one position per market at a time;
- costs per market (IG-like: indices 0.02% per side, gold 0.03%, crypto spot 0.2%);
- IG overnight funding of about 6% a year on held index and commodity positions.

**Units.** Profit per trade in ATR(20) at entry.

**Rating** (fixed before running):
- **t\*** = multiple-testing threshold (Šidák) for all ideas tried so far. It is 3.70 with 240 ideas tried.
- **A:** t ≥ t\*, ≥ 60% of years positive, last 5 years positive, still positive at 1.5x costs.
- **B:** t ≥ 2, ≥ 55% of years positive, last 5 years positive.
- **C:** mean > 0. **F:** mean ≤ 0.

**Checks on A/B ideas:**
- beat the 95th percentile of 200 random-entry runs (same markets, counts and exits);
- 1.5x costs;
- the last 365 days;
- ≥ 60% of years positive;
- the t\* above.

**Look-ahead detector** (intraday gate): signals recomputed on data cut at 25 random points must match the full-data signals.

**"Fallow" check.** Would skipping a book's historically bad months, weekdays or VIX levels have helped *out of sample*? The skip list is chosen only from earlier years, and adopted only if it raises later profit and keeps ≥ 50% of trades.

**Confidence labels:**
- **MEASURED** = real fills.
- **TESTED** = an honest backtest that held on data not used to build it.
- **WEAK** = honest but few trades, uneven, or fails one test.
- **FAILED.**

---

## The best books

### Family 1: buying short, sharp dips in rising markets (daily)

**A. RSI(2) dip (#51)** — **TESTED (backtest)**
- **Markets:** 7 indices plus gold.
- **Entry:** close above its 200-day average, RSI(2) < 5, and close below its 5-day average → buy at the close.
- **Exit:** at the first close above the 5-day average, or after 10 days.
- **Stop:** 3 ATR.

| Trades | Mean (ATR) | t | Years + | Last 5 years | Last year | Random 95th | 1.5x costs |
|---|---|---|---|---|---|---|---|
| 752 | +0.245 | 4.35 | 19/26 | +0.36 | +0.70 | +0.06 | +0.22 |

**B. TPS scale-in ladder (Connors & Alvarez, 2009)** — **TESTED (backtest)**
- **Entry:** above the 200-day and RSI(2) < 25 on two closes in a row → buy 10% of the episode budget at the close.
- **Adding:** each later close below the last entry adds 20%, then 30%, then 40%.
- **Exit:** at the close when RSI(2) > 70, after 30 days, or on a close 15% below the average cost.

| Version | Episodes | Mean per episode (% of budget) | t | Win | Worst | Years + | Last year |
|---|---|---|---|---|---|---|---|
| 7 indices + gold (IG) | 1558 | +0.19% | 5.0 | 89% | −19% | 21/26 | +0.42% |
| 10 coins, spot (Revolut X) | 295 | +1.18% | 3.3 | 89% | −23% | 3/5 | +0.12% |
| Coins, all-in at once (comparison) | 300 | +0.43% | 0.9 | 61% | −31% | 3/5 | |

- All nearby settings were positive (RSI 20/30, max 20/45 days, kill at −10%/−20%).
- On 9 other markets (commodities, FX, bonds) it doesn't work: −0.01% per episode.

**C. Stochastic %K(5) < 10 (#61)** — **TESTED (backtest)**
- **Rule:** above the 200-day; exit when %K > 50.
- **Results:** 1,774 trades, +0.169 ATR, t 4.48, 18 of 26 years positive.

**D. Related dip-buyers.** These all pass every check except t\*: Connors R3, the Bollinger/z-score dip, cumulative RSI(2) and Double 7s. Monthly correlation between RSI(2) and Double 7s is 0.69, so they are largely the same trade.

### Family 2: calendar effects (daily, known in advance)

| Book | Rule | Trades | Mean (ATR) | t | Years + | Random 95th | Last year | Label |
|---|---|---|---|---|---|---|---|---|
| Turn of the quarter (#39) | Buy the close of the last business day of the quarter, hold 3 days, stop 5 ATR (7 indices) | 689 | +0.25 | 4.27 | 22/27 | +0.04 | +1.08 | TESTED |
| Santa rally (#37) | Buy the close of the first trading day of 22–24 Dec, hold 7 days, stop 5 ATR | 174 | +0.50 | 4.20 | 20/26 | +0.20 | +0.62 | TESTED |
| Halloween (Bouman & Jacobsen 2002) | Long indices month by month Nov–Apr only, stop 8 ATR | 668 | +0.48 | 3.56 | 19/27 | n/a | | WEAK (only just clears t\*) |

### Family 3: cross-market

**E. US strong close → Europe next day (#47)** — **TESTED (backtest)**
- **Signal:** the S&P 500 closed in the top 10% of its day's range and up more than 1%.
- **Trade:** next day, buy DAX and FTSE at the open, sell at the close. Stop 2 ATR.

| Trades | Mean (ATR) | t | Years + | Last 5 years | Random 95th | 1.5x costs | Last year |
|---|---|---|---|---|---|---|---|
| 1140 | +0.112 | 5.99 | 22/27 | +0.005 | +0.01 | +0.10 | +0.03 |

*Concern: the last 5 years are close to zero.*

**F. Stocks down 5 days while bonds rise → long US index 5 days (#84)** — WEAK (passes all except t\*): 1,565 trades, +0.10 ATR, 17 of 27 years positive.

### Family 4: trend (daily, IG quarterly bets) — WEAK

- **Trend 100-day:** 16 of 27 years positive. A month-and-VIX "fallow" switch helped out of sample (+290 → +372), but the last 5 years without the switch are negative.
- **12-month time-series momentum** (Moskowitz, Ooi & Pedersen 2012), 18 markets: 16 of 27 years positive. Skipping Feb, May and Jul helped out of sample (+274 → +326).

### Family 5: crypto (spot)

- **G. Crypto 7-day-high breakout above the 50-day, exit at the 5-day low (#96):** WEAK (passes all except t\*). 694 trades, +0.357 ATR, 5 of 6 years positive, last year +0.04.
- **H. BTC crowd contrarian:** WEAK. When the Binance long/short ratio is in its top or bottom 10% of 90 days, fade it for 3 days. 202 trades, +0.23 ATR, t 2.1, 4 of 5 years positive. Skipping weekends helped out of sample.

### Family 6: intraday (5-minute bars; history only 7–14 months, so all WEAK)

- **Ignition v1.1, US Tech 100** (live at minimum stakes):
  - **Signal:** an expansion bar (range ≥ 1.25x the prior 20 bars), order-flow delta share ≥ 0.05, and the higher-timeframe EMA20/50 agreeing.
  - **Trade:** enter on the next bar; stop 45 points; move to breakeven at +15; trail 1 ATR.
  - **Results:** US hours 87 trades, +0.33 ATR, WEAK (fails only on t). All hours: +4.5 / +2.6 points per trade (development / holdout), about 670 trades a year.
- **"AuclairsDad" stack** (a regime filter plus a coil setup plus the Ignition trigger): +5.0 / +3.5 points per trade. Skipping Tuesday and Wednesday helped out of sample. WEAK.
- **Gold London Asian-range breakout:**
  - **Range:** the 01:00–06:00 UTC range, if 0.3–1.6% of price.
  - **Entry:** a stop order 0.02% beyond the side nearer the price.
  - **Exits:** stop at the other side (capped at 0.6%), target 2.5x risk, flat at 19:00 UTC.
  - **Results:** 104 trades, about +8 points per trade, WEAK (7 months of data).
- Five years of minute data is downloading to re-test these.

### What failed (for context)

Candlestick patterns, daily breakout and trend systems after IG costs and funding (Turtle, Donchian, Keltner, MA crosses), weekday effects, most cross-asset triggers, crypto weekday/weekend effects, dip-buying in FX and commodities, opening-range breakouts on indices, and liquidity-sweep fades on BTC (every year negative).

## Combined daily books (backtest, risk-balanced, 2001–2026)

- About 60% of months positive and 18 of 26 years positive.
- Worst 12 months: −38 ATR, against −134 for the worst single book.
- Recent years: 2022 −20 ATR, 2023 +11, 2024 +27, 2025 +54, 2026 so far −4.
- **Replay through the actual live code** (£500, intended sizes):
  - Nov 2021 – Nov 2023: £500 → £533.
  - Nov 2025 – Nov 2026: £500 → £661.
  - Backtest, not real fills.

## Live record so far (MEASURED)

IG live since 5 Nov at minimum stakes: £500 → £493.67.
- One ladder trade lost £6.65; that was the look-ahead book, now off.
- One Ignition trade made +£0.33.

The daily books above started on the IG demo on 10 Nov.

---

## Appendix: the shared simulator and indicators (Python, verbatim)

```python
COST = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003}  # per side
# ATR(20) = 20-day mean of true range; RSI(n) uses Wilder-style EWM with alpha = 1/n
def rsi(c, n):
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def run(k, entry, side=1, exit_=None, maxd=10, stop=3.0, how="C", fund=True):
    """entry/exit_: boolean Series known at that bar's close. how: C = enter at the close, O = next open,
    OC = same-day open->close (entry known before that day's open)."""
    d = D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = entry.reindex(d.index).fillna(False).values.astype(bool)
    X = exit_.reindex(d.index).fillna(False).values.astype(bool) if exit_ is not None else np.zeros(len(d), bool)
    S = side.reindex(d.index).fillna(0).values if isinstance(side, pd.Series) else np.full(len(d), side)
    cost = COST.get(k, 0.002); fy = (0.06 if fund and k in COST else 0.0) / 365 * 1.4
    out = []; i = 0; n = len(C)
    while i < n - 1:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0 or S[i] == 0: i += 1; continue
        s = int(S[i])
        if how == "OC":
            e = O[i]; st = e - s * stop * A[i]; px = C[i]
            if (s == 1 and L[i] <= st) or (s == -1 and H[i] >= st): px = st
            out.append((d.index[i], (s * (px - e) - cost * e * 2) / A[i])); i += 1; continue
        j0 = i if how == "C" else i + 1
        e = C[i] if how == "C" else O[i + 1]; st = e - s * stop * A[i]; j = j0 + (1 if how == "C" else 0); px = None
        while j < n:
            if (s == 1 and L[j] <= st) or (s == -1 and H[j] >= st):
                px = (min(st, O[j]) if s == 1 else max(st, O[j])) if j > j0 else st; break
            if X[j] or (j - j0) >= maxd: px = C[j]; break
            j += 1
        if px is None: break
        pnl = s * (px - e) - cost * e * 2 - fy * e * (j - j0)
        out.append((d.index[i], pnl / A[i])); i = j + 1 if how == "C" else j
    return out

# Example rules
up200 = lambda d: d.close > d.close.rolling(200).mean()
ma = lambda c, n: c.rolling(n).mean()
# #51 RSI(2) dip
run(k, up200(d) & (rsi(d.close, 2) < 5) & (d.close < ma(d.close, 5)), 1, d.close > ma(d.close, 5), 10)
# #39 turn of the quarter
bqe = pd.Series(d.index == (d.index + pd.offsets.BQuarterEnd(0)), index=d.index); run(k, bqe, 1, None, 3, stop=5)
# #37 Santa rally
s = pd.Series((d.index.month == 12) & (d.index.day >= 22) & (d.index.day <= 24) & (d.index.dayofweek < 5), index=d.index)
run(k, s & ~s.shift(1, fill_value=False), 1, None, 7, stop=5)
# #47 US strong close -> DAX/FTSE next day open->close
strong = ((spx.close - spx.low) / (spx.high - spx.low) > 0.9) & (spx.close.pct_change() > 0.01)
run(k, strong.shift(1).reindex(D[k].index).fillna(False), 1, how="OC", stop=2)
```

**Questions we'd most like answered:**
- Is entering "at the close" realistic when the live runner decides about 20 minutes before the close using the live price?
- Is IG's overnight funding (about 6% a year) high enough?
- Are 7 indices plus gold really independent enough to count as separate evidence?
- What would you cut first?
