# Trading books — review pack v2 for an independent reviewer (10 Nov 2026, 10:30)

## What I'm asking you to do

Please **try to break these results and the live set-up**. They were built and tested by one AI (Claude), which has made testing errors before (listed below). This is the second review: the first reviewer's points have been acted on, and the list of what changed is below. Specifically:

1. Look for **look-ahead bias**: any decision that uses a price not known at the time of the trade.
2. Look for **overfitting**. 276 ideas have now been tried; are the survivors just the lucky ones?
3. Check that the **costs, funding and fills** are realistic for IG UK spread bets and Revolut X crypto spot.
4. Check the **live risk rules**, especially the exceptions that let some trades risk more than 2% on a £500 book.
5. Say what you would trust, cut or change, and why.
6. If you can, **reproduce** one result from the rules and code in the appendix.

## What changed since the first review (and why)

| Reviewer's point | What we did | Result |
|---|---|---|
| Entering "at the close" is optimistic (decided 20 min early) | Dip books now decide on the **final daily close and trade at the next open** (entries and exits) | RSI(2) t 4.14, TPS t 4.85 at next open — still pass |
| Min stake vs 2% risk | Live **skips** any trade the minimum stake would push over its risk limit (never oversized), with two deliberate exceptions (see risk rules) | |
| 7 indices + gold not independent | **6% cap on total risk across the five equity indices** at once | |
| Reviewer's frequency ideas (RSI(4), RSI(2)<10, MDD, TOM, overnight) | All tested through the same checks | RSI(4) replaced RSI(2) as the dip book (more trades, higher t) |
| Cut WEAK books from live | Live = only the books below marked LIVE; WEAK stays demo | |

## New errors found since the first review (please check)

| Error | What happened | Fix |
|---|---|---|
| **Yahoo FTSE "open" is the previous close on 95% of days** (S&P 500 and Russell ~25% before 2010) | Any next-open or overnight test on FTSE was really a close entry. Worse: the "US strong close → Europe" book counted FTSE's move from 16:30 on the signal day, **before** the 21:00 US close that defines the signal (look-ahead) | That book is **closed** (on real DAX prices it loses). Overnight tests re-run without bad opens |
| Replay ignored the account-wide exposure cap | An earlier TPS replay let ladders exceed the 5x cap | Replays now enforce it; numbers below are the corrected ones |

Earlier errors (still guarded): same-bar-close look-ahead in a 15-minute ladder (book off), overlapping trades counted in an intraday test, R units with tight stops, calendar month look-ahead, stale cross-market closes, oversizing from minimum stakes.

## How every idea is tested (unchanged method)

- **Data:** daily Yahoo 2000–2026 (7 equity indices, gold, other commodities, FX, US 10-year), crypto from Coinbase/Revolut X. Intraday 5-minute bars, 7–14 months only.
- **Simulator** (appendix): decisions on closed bars only; entry at that close, next open, or same-day open→close only when known before the open; stop checked first, gaps fill at the open; one position per market; costs per side indices 0.02%, gold 0.03%, crypto 0.2%; IG funding ~6% a year.
- **Units:** profit per trade in ATR(20) at entry.
- **Checks:** t against the Šidák multiple-testing bar t\* (3.74 with 276 ideas); ≥ 60% of years positive; last 5 years and last year positive; still positive at 1.5x costs; beats the 95th percentile of random entries with the same exits.
- **Labels:** MEASURED (real fills), TESTED (honest backtest, held out of sample), WEAK (small, uneven or fails one check), FAILED.

---

## The live set-up (IG UK spread bets, £500 pot, GitHub Actions; owner switches it on/off)

### Books trading live (daily, decided on closed bars)

**1. RSI(4) dip** — TESTED. Replaces RSI(2)<5 after the first review.
- Entry: close above its 200-day average and RSI(4) < 25 → buy at the next open. Exit: RSI(4) > 55 (traded next open), or 10 days. Stop 3 ATR.
- 8 markets: n 1208 (46/yr), +0.290 ATR, **t 5.46**, 19/26 years +, last 5 years +0.337, last year +0.350, 1.5x costs +0.266, random 95th +0.043. Next-open version t 5.28.
- Correlation with the old RSI(2) book 0.72.

**2. TPS scale-in ladder** (Connors & Alvarez 2009) — TESTED.
- Above the 200-day and RSI(2) < 25 on two closes → buy 10% of the budget; each lower close adds 20/30/40%; exit RSI(2) > 70, 30 days, or 15% under average cost.
- 7 indices + gold: 1558 episodes, +0.19% of budget per episode, **t 5.0**, 89% won, 21/26 years +. Next open t 4.85.
- **Live exception:** at £500 even IG's minimum stake (0.01/pt) makes a full ladder risk ~20% of the pot. The owner chose to run it anyway at the minimum stake with its own **£100 book stop** (closed + open TPS P&L), which **restarts automatically** once the US 500 closes back above its 200-day average.

**3. Turn of the month (TOM)** — TESTED, borderline. Replaces turn-of-quarter (which it contains).
- Buy at the close of the last business day of each month, hold 3 days, stop 5 ATR.
- On the **6 markets traded** (US 500, US Tech 100, Wall St, DAX, FTSE, gold): n 1854 (69/yr), +0.156 ATR, **t 4.42**, **17/27 years +**, last 5 years +0.082, last year +0.439, 1.5x costs +0.137, random 95th +0.039.
- On all 8 markets (adding Japan 225 and Russell 2000, both weak) it was 16/27 years (fails the 60% bar). **Please judge whether using the traded set is fair or cherry-picking.**
- The published McConnell–Xu window (in at day −2) was clearly worse (t 1.60): the last day of the month is weak in 2000–2026 data.

**4. Santa rally** — TESTED. Buy the close of the first trading day of 22–24 Dec, hold 7 days, stop 5 ATR. n 174, +0.50 ATR, t 4.20, 20/26 years +.

**Also live, at minimum stakes, labelled WEAK** (owner's choice, as real-fill measurement): intraday **Ignition v1.1** on US Tech 100 (expansion bar + order-flow delta + trend agreement; 45-point stop) and a **spike-continuation engine** on US Tech 100 / US 500. Only 7–14 months of data; five years of minute data is being downloaded to re-test them.

### Live risk rules (one config file; every limit is a share of the pot)

- Pot = £500 + the owner's net deposits + all books' trading P&L since start. **Deposits and withdrawals are read from IG's transaction history and never count as profit or loss.**
- **Risk per trade 2%**, sized from the pot.
- **Minimum-stake fallback:** if IG's minimum stake would risk more than 2% at the normal stop, the trade retries with a **2 ATR stop**. Tested: the edge barely changes (RSI(4) on US Tech 100 / Wall St +0.288 vs +0.290; TOM +0.180 vs +0.175).
- **Exceptions (owner's decision):** US Tech 100 and Wall Street trades may risk **up to 3.5%** at the minimum stake (about 2.6–2.7% today). These end automatically when the pot reaches £1,000.
- **Total exposure ≤ 5x the pot**, counting every open position on the account (both live runners share it).
- **Equity-index risk cap 6%** of the pot at once.
- **Day stop −4% and floor −15%** of the pot, measured on the whole account (both runners), **excluding TPS**, which has its own stop.
- **Risk tiers by pot size** (aggressive early, less as it grows):

| Pot from | Risk per trade | TPS |
|---|---|---|
| £0 | 2% | minimum stake allowed; stop £100 |
| £1,000 | 2% | stop 10% of pot |
| £2,500 | 1.5% | stop 7.5% of pot |
| £5,000 | 1% | sized normally (no minimum-stake exception); stop 5% |

### Backtest of the live set-up (replayed through the actual live code, Nov 2019 – Nov 2026)

All live daily books, IG minimum stake 0.01/pt, 5x cap enforced, TPS with its £100 stop and auto-restart:

| | Total | Lowest balance | Worst month | Max drawdown |
|---|---|---|---|---|
| **Live set-up** | **£500 → £1,604 (+£1,104)** | £382 | −£218 | £266 |
| Same, TPS stop £200 (never triggers) | +£1,010 | £321 | −£214 | £217 |
| Same, TPS stop £100 with no restart | +£263 | £382 | −£125 | £150 |
| Without TPS | +£367–447 | £470–486 | −£28 to −£97 | £71–100 |
| TPS re-bought immediately at 2x size after the stop ("double down") | +£852 | £275 | | |

- By year (live set-up): 2020 +£1, 2021 +£173, 2022 −£12, 2023 +£118, 2024 +£104, 2025 +£281, 2026 so far +£434.
- **Capital use:** a position open on 57% of days (71% in the last year); average exposure ~1x the pot of the 5x allowed (median 0.4–0.7x).
- **Higher risk per trade:** 3% instead of 2% added almost nothing (+£1,120 vs +£1,104, caps bind on busy days); 4% hit the −15% floor in 2022.
- **Next 36 trading days** (all 36-day windows since 2019): median +£23 (since 2024: +£43), 80% between −£37 and +£90, worst −£190.

### Revolut X (separate £500, approved for a crypto book; built as a dry run, not live)

**TPS coin ladder** — same rules as TPS, 10 coins (BTC ETH SOL XRP DOGE AVAX LINK ADA LTC DOT), daily UTC candles, 10% of the book per episode, at most 10 open, market orders (0.09% taker + 0.1% slippage).
- Earlier test (Coinbase 2021–26): 295 episodes, +1.18% per episode, t 3.3, 89% won, 3/5 years. The ladder is what works: all-in at once t 0.9.
- Replay through the runner on Revolut X candles, Aug 2024 – Nov 2026: £500 → £657, 150 episodes, 91% won, worst −$13, max drawdown 4.5%. 2025 +£130, 2026 −£1.

---

## Tested since the first review and NOT used

| Idea | Result |
|---|---|
| RSI(2) < 10 (Connors base) | PASS (t 4.62) but 0.78 correlated with RSI(4) — same trade |
| Multiple days down (MDD) | Passes on the traded markets (t 3.89); the dips RSI(4) misses have no edge (t 1.70); combining adds trades, not profit |
| Overnight close→open (4 filters) | FAIL. Gross drift 1–5 bp/night ≈ one night's IG funding (~2.3 bp) + spread, even at IG's real spreads |
| Daily close-position fade (from a CPI-day post) | FAIL on every day (−0.024 ATR, t −4.4); on FOMC days 50% |
| CPI-day fade itself | 17/21 wins 2025-26 but 17/36 in 2022-24: a small-sample run; CPI history before 2022 not reachable to test |
| US strong close → Europe | CLOSED: FTSE look-ahead artefact; on DAX minute data buying at the US close loses (−0.065 ATR, 5/14 years) |
| Halloween, 3 variants | WEAK (t ≤ 2.9): mostly ordinary market drift |
| 12-month / 1-3-12-month vol-scaled trend, 28 markets, with spread-bet funding | No edge (+1.3% / −1.8% a year); helps in crashes (2008, 2022) |
| US Tech 100 / Wall St dip signals traded on the US 500 | No edge on the extra days |

---

## Questions we most want answered

1. **TPS at the minimum stake on £500**: each ladder can risk ~20% of the pot; protected by a £100 book stop with auto-restart above the 200-day. Sensible, or reckless?
2. Is moving to a **2 ATR stop** when the minimum stake doesn't fit a fair change, given the tested edge barely moves?
3. **TOM on the traded markets only** (17/27 years) vs all 8 (16/27): fair or cherry-picking?
4. Are **Yahoo daily prices** good enough given the FTSE open fault? What else might be broken?
5. With capital idle ~30–40% of days and exposure ~1x of 5x, what would you add to use it better, without stacking the same equity-dip risk?
6. Anything in the **live rules** (deposits, tiers, exceptions, shared caps) that could fail in practice?

---

## Appendix A: the shared simulator (Python, verbatim)

```python
COST = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003}  # per side
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

up200 = lambda d: d.close > d.close.rolling(200).mean()
# RSI(4) dip, next-open version
run(k, up200(d) & (rsi(d.close, 4) < 25), 1, rsi(d.close, 4) > 55, 10, stop=3, how="O")
# Turn of the month
bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); run(k, bme, 1, None, 3, stop=5)
# Santa rally
s = pd.Series((d.index.month == 12) & (d.index.day >= 22) & (d.index.day <= 24) & (d.index.dayofweek < 5), index=d.index)
run(k, s & ~s.shift(1, fill_value=False), 1, None, 7, stop=5)
```

## Appendix B: TPS ladder (episode measured as % of its budget)

```python
def tps(d, cost, fund_yr, rsi_in=25, maxd=30, kill=0.15, ladder=(0.1, 0.2, 0.3, 0.4)):
    C = d.close.values; r = rsi(d.close, 2).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 1:
        if not (C[i] > ma[i] and r[i] < rsi_in and r[i - 1] < rsi_in): i += 1; continue
        qty, spent, last, k, j0 = 0.0, 0.0, None, 0, i; j = i
        while j < n:
            if k < len(ladder) and (last is None or C[j] < last):
                w = ladder[k]; qty += w / (C[j] * (1 + cost)); spent += w; last = C[j]; k += 1
            avg = spent / qty
            if (r[j] > 70 or (j - j0) >= maxd or C[j] <= avg * (1 - kill)) and j > j0:
                val = qty * C[j] * (1 - cost) - spent * fund_yr / 365 * 1.4 * (j - j0) * 0.5
                out.append((d.index[j0], val - spent, spent, j - j0)); break
            j += 1
        i = j + 1
    return out
```

*All figures are backtests unless marked MEASURED. Live real-money record so far: IG £500 → £493.67 (5–9 Nov, minimum stakes, intraday books). The daily books go live from 10 Nov.*
