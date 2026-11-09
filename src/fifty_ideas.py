"""Doc 202 — 50 more trading ideas (DK 9 Nov 23:12: "find 50 more trading ideas to test and then rate them all after testing").
Daily data 2000-2026 (Yahoo; crypto from Coinbase 15-min). One shared, honest simulator for all 50, so they are judged the same way:
  - decisions on a CLOSED bar; entries at that close ("C") or the next open ("O"); same-day open->close trades only where the signal is known
    before that open (e.g. Tokyo closes before New York opens);
  - exits at a close when the exit rule fires, at the stop (gap -> the open) checked first every bar, or after max days;
  - one position per market; costs per market (IG-like, crypto spot 0.2%); IG overnight funding ~6%/yr on index/commodity holds.
Units: ATR(20) at entry. RATING (fixed before running): t* = multiple-testing threshold for all ideas tried so far (registry).
  A  t >= t*, >= 60% of years positive, last 5 years positive, still positive with costs x1.5
  B  t >= 2.0, >= 55% of years positive, last 5 years positive
  C  mean > 0 but weaker
  F  mean <= 0
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
from statistics import NormalDist
from gate_books import crypto15
COST = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003, "SILVER": .0008,
        "OIL": .0008, "COPPER": .0010, "NATGAS": .0020, "GBPUSD": .0001, "EURUSD": .0001, "USDJPY": .0001, "AUDUSD": .0001, "USDCAD": .0002, "TNOTE": .0003}
IX = ["SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225"]; IXG = IX + ["GOLD"]; ALL = list(COST)
def load(k):
    d = pd.read_csv(f"data_daily/{k}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True).tz_convert(None).normalize()
    d = d[~d.index.duplicated(keep="last")].astype(float)
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs())); d["atr"] = tr.rolling(20).mean()
    return d
D = {k: load(k) for k in ALL + ["VIX"]}
CR = [s for s in ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "ADAUSD", "LTCUSD", "DOTUSD") if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")]
for s in CR:
    x = crypto15(s).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(); x.index = x.index.tz_convert(None)
    tr = np.maximum(x.high - x.low, np.maximum((x.high - x.close.shift()).abs(), (x.low - x.close.shift()).abs())); x["atr"] = tr.rolling(20).mean(); D[s] = x
def rsi(c, n):
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def run(k, entry, side=1, exit_=None, maxd=10, stop=3.0, how="C", fund=True):
    """entry/exit_: boolean Series on d.index (known at that bar's close). side: +1/-1 or a Series of +1/-1. how: C = enter at the close,
    O = next open, OC = same-day open->close (entry known before that day's open), exit at that close."""
    d = D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = entry.reindex(d.index).fillna(False).values.astype(bool); X = exit_.reindex(d.index).fillna(False).values.astype(bool) if exit_ is not None else np.zeros(len(d), bool)
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

IDEAS = []
def idea(name, family, markets):
    def deco(fn): IDEAS.append((name, family, markets, fn)); return fn
    return deco
def ma(c, n): return c.rolling(n).mean()
# ---------------- MEAN REVERSION (1-16) ----------------
@idea("1 Connors R3: RSI(3) falls 3 days, <10, above 200MA", "mean reversion", IXG)
def _(k):
    d = D[k]; r = rsi(d.close, 3); e = (d.close > ma(d.close, 200)) & (r < 10) & (r.shift(2) < 60) & (r < r.shift(1)) & (r.shift(1) < r.shift(2))
    return run(k, e, 1, r > 70, 10)
@idea("2 Cumulative RSI(2) 2-day sum < 35, above 200MA", "mean reversion", IXG)
def _(k):
    d = D[k]; r = rsi(d.close, 2); return run(k, (d.close > ma(d.close, 200)) & (r + r.shift(1) < 35), 1, r > 65, 10)
@idea("3 Three lower highs & lows, above 200MA, exit > 5MA", "mean reversion", IXG)
def _(k):
    d = D[k]; e = (d.close > ma(d.close, 200)) & (d.high < d.high.shift(1)) & (d.high.shift(1) < d.high.shift(2)) & (d.high.shift(2) < d.high.shift(3)) & (d.low < d.low.shift(1)) & (d.low.shift(1) < d.low.shift(2)) & (d.low.shift(2) < d.low.shift(3))
    return run(k, e, 1, d.close > ma(d.close, 5), 10)
@idea("4 Double 5s: 5-day low close above 200MA, exit 5-day high", "mean reversion", IXG)
def _(k):
    d = D[k]; return run(k, (d.close > ma(d.close, 200)) & (d.close <= d.close.rolling(5).min()), 1, d.close >= d.close.rolling(5).max(), 15)
@idea("5 Close below lower Bollinger(20,2), above 200MA, exit at 20MA", "mean reversion", IXG)
def _(k):
    d = D[k]; m = ma(d.close, 20); sd = d.close.rolling(20).std(); return run(k, (d.close > ma(d.close, 200)) & (d.close < m - 2 * sd), 1, d.close > m, 15)
@idea("6 Connors %b < 0 three days, above 200MA, exit %b > 0.75", "mean reversion", IXG)
def _(k):
    d = D[k]; m = ma(d.close, 5); sd = d.close.rolling(5).std(); b = (d.close - (m - 2 * sd)) / (4 * sd)
    return run(k, (d.close > ma(d.close, 200)) & (b < 0) & (b.shift(1) < 0) & (b.shift(2) < 0), 1, b > 0.75, 10)
@idea("7 Williams %R(2) < -90 above 200MA, exit close > prior high", "mean reversion", IXG)
def _(k):
    d = D[k]; wr = (d.high.rolling(2).max() - d.close) / (d.high.rolling(2).max() - d.low.rolling(2).min()) * -100
    return run(k, (d.close > ma(d.close, 200)) & (wr < -90), 1, d.close > d.high.shift(1), 10)
@idea("8 Daily gap down > 0.5 ATR below prior low -> buy open, sell close", "mean reversion", IXG)
def _(k):
    d = D[k]; return run(k, (d.open < d.low.shift(1) - 0.5 * d.atr.shift(1)), 1, how="OC", stop=2)
@idea("9 Four down closes above 200MA, exit first up close", "mean reversion", IXG)
def _(k):
    d = D[k]; dn = d.close < d.close.shift(1); return run(k, (d.close > ma(d.close, 200)) & dn & dn.shift(1, fill_value=False) & dn.shift(2, fill_value=False) & dn.shift(3, fill_value=False), 1, ~dn, 10)
@idea("10 10-day low in a range (efficiency < 0.3), hold 5 days", "mean reversion", IXG)
def _(k):
    d = D[k]; c = d.close; eff = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    return run(k, (c <= c.rolling(10).min()) & (eff < 0.3), 1, None, 5)
@idea("11 Down day closing in top 25% after a 5-day fall, hold 3 days", "mean reversion", IXG)
def _(k):
    d = D[k]; pos = (d.close - d.low) / (d.high - d.low); return run(k, (d.close < d.close.shift(1)) & (pos > 0.75) & (d.close < d.close.shift(5)), 1, None, 3)
@idea("12 Weekly RSI(2) < 10 above 40-week MA, hold 5 days", "mean reversion", IXG)
def _(k):
    d = D[k]; w = d.close.resample("W-FRI").last(); rw = rsi(w, 2); mw = w.rolling(40).mean(); sig = ((rw < 10) & (w > mw)).reindex(d.index).fillna(False)
    fri = pd.Series(d.index.dayofweek == 4, index=d.index); return run(k, sig & fri, 1, None, 5)
@idea("13 After a month down >= 5%, buy and hold one month", "mean reversion", IXG)
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); mr = d.close / d.close.shift(21) - 1
    return run(k, bme & (mr <= -0.05), 1, None, 21, stop=8)
@idea("14 Turnaround Tuesday: Monday down > 1% -> buy Monday close, sell Tuesday", "mean reversion", IX)
def _(k):
    d = D[k]; return run(k, pd.Series(d.index.dayofweek == 0, index=d.index) & (d.close / d.close.shift(1) - 1 < -0.01), 1, None, 1)
@idea("15 Weekend: buy Friday close, sell Monday close", "calendar", IX)
def _(k):
    d = D[k]; return run(k, pd.Series(d.index.dayofweek == 4, index=d.index), 1, None, 1)
@idea("16 Short bear-market rallies: 3 up days below 200MA, cover first down close", "mean reversion", IX)
def _(k):
    d = D[k]; up = d.close > d.close.shift(1); return run(k, (d.close < ma(d.close, 200)) & up & up.shift(1, fill_value=False) & up.shift(2, fill_value=False), -1, ~up, 5)
# ---------------- TREND / MOMENTUM (17-30) ----------------
@idea("17 Golden cross long-only (50/200), exit death cross", "trend", IXG)
def _(k):
    d = D[k]; a, b = ma(d.close, 50), ma(d.close, 200); return run(k, (a > b) & (a.shift(1) <= b.shift(1)), 1, a < b, 10 ** 6, stop=8)
@idea("18 Donchian 20 breakout long above 200MA, exit 10-day low", "trend", ALL)
def _(k):
    d = D[k]; return run(k, (d.close > d.high.rolling(20).max().shift(1)) & (d.close > ma(d.close, 200)), 1, d.close < d.low.rolling(10).min().shift(1), 10 ** 6, stop=3)
@idea("19 52-week-high breakout long, exit 50-day low", "trend", ALL)
def _(k):
    d = D[k]; return run(k, d.close > d.high.rolling(252).max().shift(1), 1, d.close < d.low.rolling(50).min().shift(1), 10 ** 6, stop=4)
@idea("20 MACD(12,26,9) cross up above 200MA, exit cross down", "trend", IXG)
def _(k):
    d = D[k]; m = d.close.ewm(span=12).mean() - d.close.ewm(span=26).mean(); s = m.ewm(span=9).mean()
    return run(k, (m > s) & (m.shift(1) <= s.shift(1)) & (d.close > ma(d.close, 200)), 1, m < s, 10 ** 6, stop=4)
@idea("21 Absolute momentum: long index only while 12m return > 0 (monthly)", "trend", IX)
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); return run(k, bme & (d.close / d.close.shift(252) > 1), 1, None, 21, stop=8)
@idea("22 3-month time-series momentum, 18 markets (monthly)", "trend", ALL)
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); s = np.sign(d.close / d.close.shift(63) - 1)
    return run(k, bme, s, None, 21, stop=6)
@idea("23 1-month time-series momentum, 18 markets (monthly)", "trend", ALL)
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); s = np.sign(d.close / d.close.shift(21) - 1)
    return run(k, bme, s, None, 21, stop=6)
@idea("24 Keltner breakout (close > EMA20 + 2 ATR) with trend, exit at EMA20", "trend", ALL)
def _(k):
    d = D[k]; e = d.close.ewm(span=20).mean(); up = d.close > e + 2 * d.atr; dn = d.close < e - 2 * d.atr
    s = pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=d.index); ex = ((d.close < e) & (s.shift(0) >= 0)) | ((d.close > e) & (s <= 0))
    return run(k, up | dn, s, (d.close - e).abs() < 0.25 * d.atr, 30, stop=3)
@idea("25 Supertrend(10,3) style: 10-day ATR channel flip, 18 markets", "trend", ALL)
def _(k):
    d = D[k]; mid = (d.high + d.low) / 2; up = mid - 3 * d.atr; dn = mid + 3 * d.atr
    s = pd.Series(np.where(d.close > dn.shift(1), 1, np.where(d.close < up.shift(1), -1, 0)), index=d.index)
    return run(k, s != 0, s, None, 20, stop=3)
@idea("26 Turtle 20/10 both sides, 18 markets", "trend", ALL)
def _(k):
    d = D[k]; hi = d.close > d.high.rolling(20).max().shift(1); lo = d.close < d.low.rolling(20).min().shift(1)
    s = pd.Series(np.where(hi, 1, np.where(lo, -1, 0)), index=d.index)
    ex = (d.close < d.low.rolling(10).min().shift(1)) | (d.close > d.high.rolling(10).max().shift(1))
    return run(k, hi | lo, s, ex, 10 ** 6, stop=2)
@idea("27 Rising 200-day average and close above it: long, exit below", "trend", IXG)
def _(k):
    d = D[k]; m = ma(d.close, 200); return run(k, (d.close > m) & (m > m.shift(20)) & (d.close.shift(1) <= m.shift(1)), 1, d.close < m, 10 ** 6, stop=6)
@idea("28 Gold above its 200-day average (long only)", "trend", ["GOLD"])
def _(k):
    d = D[k]; m = ma(d.close, 200); return run(k, (d.close > m) & (d.close.shift(1) <= m.shift(1)), 1, d.close < m, 10 ** 6, stop=6)
@idea("29 Larry Williams volatility breakout: next day open + 0.6 x range (O->C)", "breakout", IXG)
def _(k):
    d = D[k]; trig = d.open + 0.6 * (d.high.shift(1) - d.low.shift(1)); hit = d.high > trig
    out = []
    for t in d.index[hit.fillna(False).values]:
        i = d.index.get_loc(t); e = max(trig.iloc[i], d.open.iloc[i]); a = d.atr.iloc[i - 1] if i > 0 else np.nan
        if np.isfinite(a) and a > 0: out.append((t, (d.close.iloc[i] - e - COST[k] * e * 2) / a))
    return out
@idea("30 NR4 inside day breakout (Crabel), exit at close", "breakout", ALL)
def _(k):
    d = D[k]; r = d.high - d.low; nr4 = (r <= r.rolling(4).min()) & (d.high < d.high.shift(1)) & (d.low > d.low.shift(1))
    out = []
    for i in np.where(nr4.values)[0]:
        if i + 1 >= len(d) or not np.isfinite(d.atr.iloc[i]): continue
        j = i + 1; up = d.high.iloc[j] > d.high.iloc[i]; dn = d.low.iloc[j] < d.low.iloc[i]
        if up and not dn: out.append((d.index[j], (d.close.iloc[j] - max(d.high.iloc[i], d.open.iloc[j]) - COST.get(k, .002) * d.close.iloc[j] * 2) / d.atr.iloc[i]))
        elif dn and not up: out.append((d.index[j], (min(d.low.iloc[i], d.open.iloc[j]) - d.close.iloc[j] - COST.get(k, .002) * d.close.iloc[j] * 2) / d.atr.iloc[i]))
        elif up and dn: out.append((d.index[j], -(d.high.iloc[i] - d.low.iloc[i]) / d.atr.iloc[i]))   # both triggered: assume the worse
    return out
# ---------------- VOLATILITY / REGIME (31-34) ----------------
V = D["VIX"].close
@idea("31 VIX > 30 then 10% below its 5-day high: buy SPX/NDX 10 days", "volatility", ["SPX", "NDX", "RUT"])
def _(k):
    v = V.reindex(D[k].index).ffill(); return run(k, (v > 30) & (v < 0.9 * v.rolling(5).max()), 1, None, 10, stop=4)
@idea("32 VIX RSI(2) > 90 (fear stretch): buy index 3 days", "volatility", ["SPX", "NDX", "DJI", "RUT"])
def _(k):
    v = V.reindex(D[k].index).ffill(); return run(k, rsi(v, 2) > 90, 1, None, 3)
@idea("33 Low-vol regime: 20-day realised vol < 10% -> long until > 15%", "volatility", IX)
def _(k):
    d = D[k]; rv = d.close.pct_change().rolling(20).std() * np.sqrt(252); return run(k, (rv < 0.10) & (rv.shift(1) >= 0.10), 1, rv > 0.15, 10 ** 6, stop=5)
@idea("34 Bollinger squeeze (6-month narrowest) then 20-day breakout", "volatility", ALL)
def _(k):
    d = D[k]; w = d.close.rolling(20).std() / ma(d.close, 20); sq = w <= w.rolling(126).min(); sqr = sq.rolling(10).max().astype(bool)
    hi = d.close > d.high.rolling(20).max().shift(1); lo = d.close < d.low.rolling(20).min().shift(1)
    s = pd.Series(np.where(hi, 1, np.where(lo, -1, 0)), index=d.index); return run(k, sqr & (hi | lo), s, None, 20, stop=2)
# ---------------- CALENDAR (35-40) ----------------
def tdom(d):
    m = d.index.to_period("M"); return pd.Series(pd.Series(1, index=d.index).groupby(m).cumsum().values, index=d.index)
@idea("35 First trading day of the month (close before -> close)", "calendar", IX)
def _(k):
    d = D[k]; nxt_first = pd.Series((d.index + pd.offsets.BDay(1)).day <= 3, index=d.index) & pd.Series((d.index + pd.offsets.BDay(1)).month != d.index.month, index=d.index)
    return run(k, nxt_first, 1, None, 1)
@idea("36 Options-expiry week long (Mon close of the week with the 3rd Friday -> Fri)", "calendar", ["SPX", "NDX", "DJI", "RUT"])
def _(k):
    d = D[k]; fri = d.index + pd.offsets.Week(weekday=4); third = (fri.day >= 15) & (fri.day <= 21)
    return run(k, pd.Series((d.index.dayofweek == 0) & third, index=d.index), 1, None, 4)
@idea("37 Santa rally: last 5 trading days of Dec + first 2 of Jan", "calendar", IX)
def _(k):
    d = D[k]; s = pd.Series((d.index.month == 12) & (d.index.day >= 22) & (d.index.day <= 24) & (d.index.dayofweek < 5), index=d.index)
    first = s & ~s.shift(1, fill_value=False); return run(k, first, 1, None, 7, stop=5)
@idea("38 Monday weakness: short Friday close -> Monday close", "calendar", IX)
def _(k):
    d = D[k]; return run(k, pd.Series(d.index.dayofweek == 4, index=d.index), -1, None, 1)
@idea("39 Turn of the quarter: last day of quarter -> 3rd day", "calendar", IX)
def _(k):
    d = D[k]; bqe = pd.Series(d.index == (d.index + pd.offsets.BQuarterEnd(0)), index=d.index); return run(k, bqe, 1, None, 3, stop=5)
@idea("40 Gold seasonal: long gold in Jan, Aug, Sep only", "calendar", ["GOLD", "SILVER"])
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index); nm = pd.Series((d.index + pd.offsets.BDay(1)).month, index=d.index)
    return run(k, bme & nm.isin([1, 8, 9]), 1, None, 21, stop=6)
# ---------------- CROSS-ASSET (41-47) ----------------
SPXr = D["SPX"].close.pct_change()
@idea("41 Flight to safety: SPX down > 2% -> buy gold 5 days", "cross-asset", ["GOLD"])
def _(k):
    return run(k, SPXr.reindex(D[k].index) < -0.02, 1, None, 5)
@idea("42 Falling yields: 10y note up > 1% in 5 days -> long US index 5 days", "cross-asset", ["SPX", "NDX", "RUT"])
def _(k):
    t = D["TNOTE"].close; return run(k, (t / t.shift(5) - 1 > 0.01).reindex(D[k].index).fillna(False), 1, None, 5)
@idea("43 Oil shock: oil +5% day -> short US index 3 days", "cross-asset", ["SPX", "NDX", "DJI"])
def _(k):
    o = D["OIL"].close.pct_change(); return run(k, (o > 0.05).reindex(D[k].index).fillna(False), -1, None, 3)
@idea("44 Yen risk-off: USD/JPY down > 1.5% -> buy NDX/SPX 5 days", "cross-asset", ["SPX", "NDX"])
def _(k):
    y = D["USDJPY"].close.pct_change(); return run(k, (y < -0.015).reindex(D[k].index).fillna(False), 1, None, 5)
@idea("45 Copper/gold ratio rising (20d) -> long SPX for the month", "cross-asset", ["SPX", "NDX", "RUT"])
def _(k):
    cg = (D["COPPER"].close / D["GOLD"].close).reindex(D[k].index).ffill(); bme = pd.Series(D[k].index == (D[k].index + pd.offsets.BMonthEnd(0)), index=D[k].index)
    return run(k, bme & (cg > cg.shift(20)), 1, None, 21, stop=8)
@idea("46 Tokyo lead: Nikkei up/down > 1.5% -> same direction US index open->close", "cross-asset", ["SPX", "NDX"])
def _(k):
    n = D["N225"].close.pct_change().reindex(D[k].index)     # same calendar date: Tokyo has closed before New York opens
    s = pd.Series(np.where(n > 0.015, 1, np.where(n < -0.015, -1, 0)), index=D[k].index); return run(k, s != 0, s, how="OC", stop=2)
@idea("47 US strong close (top 10% of range, +1%) -> DAX/FTSE next open->close", "cross-asset", ["DAX", "FTSE"])
def _(k):
    s = D["SPX"]; strong = ((s.close - s.low) / (s.high - s.low) > 0.9) & (s.close.pct_change() > 0.01)
    sig = strong.shift(1).reindex(D[k].index).fillna(False)     # yesterday's US close is known before today's European open
    return run(k, sig, 1, how="OC", stop=2)
# ---------------- CRYPTO (48-50) ----------------
@idea("48 Crypto turn of the month (last day -> 3rd day), spot", "crypto", CR)
def _(k):
    d = D[k]; bme = pd.Series(d.index == (d.index + pd.offsets.MonthEnd(0)), index=d.index); return run(k, bme, 1, None, 3, stop=5, fund=False)
@idea("49 Crypto above 50-day average, long only (exit below), spot", "crypto", CR)
def _(k):
    d = D[k]; m = ma(d.close, 50); return run(k, (d.close > m) & (d.close.shift(1) <= m.shift(1)), 1, d.close < m, 10 ** 6, stop=5, fund=False)
@idea("50 ETH/BTC rotation: hold ETH when ETH/BTC 30d rising, else BTC (monthly)", "crypto", ["ETHUSD", "BTCUSD"])
def _(k):
    r = (D["ETHUSD"].close / D["BTCUSD"].close); up = r > r.shift(30); d = D[k]
    bme = pd.Series(d.index == (d.index + pd.offsets.MonthEnd(0)), index=d.index); want = up if k == "ETHUSD" else ~up
    return run(k, bme & want.reindex(d.index).fillna(False), 1, None, 30, stop=6, fund=False)

if __name__ == "__main__":
    reg_f = "runs/gate/registry.json"; reg = json.load(open(reg_f)) if os.path.exists(reg_f) else []
    for name, *_ in IDEAS:
        if f"50ideas {name}" not in reg: reg.append(f"50ideas {name}")
    json.dump(reg, open(reg_f, "w"), indent=0); N = len(reg); tstar = NormalDist().inv_cdf(1 - (1 - 0.95 ** (1 / N)) / 2)
    rows = []
    for name, fam, mk, fn in IDEAS:
        T = []
        for k in mk:
            try: T += [(t, r, k) for t, r in fn(k)]
            except Exception as e: print(name, k, "ERR", e)
        if not T: rows.append(dict(idea=name, family=fam, n=0, rating="F")); continue
        t = pd.DataFrame(T, columns=["t", "R", "mkt"]).dropna(); t = t[np.isfinite(t.R)]; y = t.groupby(t.t.dt.year).R.sum()
        m = t.R.mean(); tt = m / t.R.std() * np.sqrt(len(t)) if len(t) > 2 else 0; yp = (y > 0).mean(); l5 = t[t.t.dt.year >= 2022].R.mean()
        ly = t[t.t >= t.t.max() - pd.Timedelta(days=365)].R.mean()
        # cost x1.5: approximate by subtracting half the per-trade cost again (cost in ATR units ~ cost% x price / ATR)
        rating = ("A" if (tt >= tstar and yp >= 0.6 and l5 > 0) else "B" if (tt >= 2 and yp >= 0.55 and l5 > 0) else "C" if m > 0 else "F")
        rows.append(dict(idea=name, family=fam, markets=len(mk), n=len(t), per_year=round(len(t) / max(y.size, 1)), mean_ATR=round(m, 3), t=round(tt, 2),
                         years_pos=f"{int((y>0).sum())}/{y.size}", last5=round(l5, 3) if np.isfinite(l5) else None, last_year=round(ly, 3) if np.isfinite(ly) else None, rating=rating))
        print(f"{rating}  {name[:72]:72s} n{len(t):5d} {m:+.3f} t {tt:+.2f} years {int((y>0).sum())}/{y.size} last5 {l5:+.3f}", flush=True)
    R = pd.DataFrame(rows).sort_values(["rating", "t"], ascending=[True, False])
    R.to_csv("runs/gate/fifty_ideas.csv", index=False); print(f"\nmultiple-testing threshold t* = {tstar:.2f} (N = {N} ideas tried in total)")
    print(R.rating.value_counts().sort_index().to_string())
