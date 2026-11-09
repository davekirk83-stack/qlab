"""Doc 203 — fifty more ideas, #51-100 (DK 9 Nov 23:22 "Repeat this process for another 50 ideas or trading concepts").
Same shared honest simulator and the same fixed rating as doc 202 (src/fifty_ideas.py): t* from the full registry; A / B / C / F.
Daily data 2000-2026 (crypto 2021-26). Then the A/B ideas go through the random-entry, costs x1.5, holdout and fallow checks."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import fifty_ideas as F
from fifty_ideas import D, run, rsi, IX, IXG, ALL, CR, COST
IDEAS = []
def idea(name, family, markets):
    def deco(fn): IDEAS.append((name, family, markets, fn)); return fn
    return deco
ma = lambda c, n: c.rolling(n).mean()
up200 = lambda d: d.close > ma(d.close, 200)
def bme(d): return pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index)
# ---------- daily mean reversion / candles (51-66) ----------
@idea("51 RSI(2) < 5 and below 5MA, above 200MA, exit close > 5MA", "mean reversion", IXG)
def _(k): d = D[k]; return run(k, up200(d) & (rsi(d.close, 2) < 5) & (d.close < ma(d.close, 5)), 1, d.close > ma(d.close, 5), 10)
@idea("52 Two closes below Keltner (EMA20 - 2 ATR), above 200MA, exit EMA20", "mean reversion", IXG)
def _(k):
    d = D[k]; e = d.close.ewm(span=20).mean(); b = d.close < e - 2 * d.atr; return run(k, up200(d) & b & b.shift(1, fill_value=False), 1, d.close > e, 15)
@idea("53 Big red candle (close < open - 1 ATR), above 200MA, hold 2 days", "candles", IXG)
def _(k): d = D[k]; return run(k, up200(d) & (d.close < d.open - d.atr), 1, None, 2)
@idea("54 Hammer at a 10-day low (lower wick > 2x body, close top third), above 200MA, hold 3", "candles", IXG)
def _(k):
    d = D[k]; body = (d.close - d.open).abs(); lw = np.minimum(d.open, d.close) - d.low; pos = (d.close - d.low) / (d.high - d.low)
    return run(k, up200(d) & (d.low <= d.low.rolling(10).min()) & (lw > 2 * body) & (pos > 0.66), 1, None, 3)
@idea("55 Bullish engulfing at a 10-day low, above 200MA, hold 3", "candles", IXG)
def _(k):
    d = D[k]; e = (d.close > d.open) & (d.close.shift(1) < d.open.shift(1)) & (d.close > d.open.shift(1)) & (d.open < d.close.shift(1))
    return run(k, up200(d) & (d.low.rolling(2).min() <= d.low.rolling(10).min()) & e, 1, None, 3)
@idea("56 Inside day after a down day, above 200MA, hold 2", "candles", IXG)
def _(k):
    d = D[k]; ins = (d.high < d.high.shift(1)) & (d.low > d.low.shift(1)); return run(k, up200(d) & ins & (d.close.shift(1) < d.close.shift(2)), 1, None, 2)
@idea("57 Close above prior high after 3 down days (reversal confirmed), hold 3", "candles", IXG)
def _(k):
    d = D[k]; dn = d.close < d.close.shift(1); return run(k, up200(d) & (d.close > d.high.shift(1)) & dn.shift(1, fill_value=False) & dn.shift(2, fill_value=False) & dn.shift(3, fill_value=False), 1, None, 3)
@idea("58 Key reversal: new 20-day low but closes up on the day, hold 3", "candles", IXG)
def _(k): d = D[k]; return run(k, (d.low < d.low.rolling(20).min().shift(1)) & (d.close > d.close.shift(1)), 1, None, 3)
@idea("59 5-day drop > 2.5 ATR, above 200MA, hold 5", "mean reversion", IXG)
def _(k): d = D[k]; return run(k, up200(d) & (d.close.shift(5) - d.close > 2.5 * d.atr), 1, None, 5)
@idea("60 RSI(14) < 30 above 200MA, exit RSI(14) > 50", "mean reversion", IXG)
def _(k): d = D[k]; r = rsi(d.close, 14); return run(k, up200(d) & (r < 30), 1, r > 50, 20)
@idea("61 Stochastic %K(5) < 10 above 200MA, exit %K > 50", "mean reversion", IXG)
def _(k):
    d = D[k]; kk = (d.close - d.low.rolling(5).min()) / (d.high.rolling(5).max() - d.low.rolling(5).min()) * 100
    return run(k, up200(d) & (kk < 10), 1, kk > 50, 10)
@idea("62 Z-score(20) < -2 above 200MA, exit z > 0", "mean reversion", IXG)
def _(k): d = D[k]; z = (d.close - ma(d.close, 20)) / d.close.rolling(20).std(); return run(k, up200(d) & (z < -2), 1, z > 0, 15)
@idea("63 Short RSI(2) > 95 below 200MA, cover RSI(2) < 50", "mean reversion", IX)
def _(k): d = D[k]; r = rsi(d.close, 2); return run(k, ~up200(d) & (r > 95), -1, r < 50, 10)
@idea("64 Short 5-day high close below 200MA, cover 5-day low", "mean reversion", IX)
def _(k): d = D[k]; return run(k, ~up200(d) & (d.close >= d.close.rolling(5).max()), -1, d.close <= d.close.rolling(5).min(), 15)
@idea("65 Pullback to the 50-day in an uptrend (50 > 200), exit +2 ATR or 10 days", "trend pullback", IXG)
def _(k):
    d = D[k]; m50, m200 = ma(d.close, 50), ma(d.close, 200); e = (m50 > m200) & (d.close < m50) & (d.close.shift(1) >= m50.shift(1))
    out = run(k, e, 1, None, 10)
    return out
@idea("66 Two closes in the bottom 20% of the range, above 200MA, hold 2", "candles", IXG)
def _(k):
    d = D[k]; p = (d.close - d.low) / (d.high - d.low) < 0.2; return run(k, up200(d) & p & p.shift(1, fill_value=False), 1, None, 2)
# ---------- momentum / breakout (67-74) ----------
@idea("67 20-day-high close above 200MA, hold 10 days fixed", "momentum", IXG)
def _(k): d = D[k]; return run(k, up200(d) & (d.close >= d.close.rolling(20).max()), 1, None, 10)
@idea("68 Gap up > 0.5 ATR above prior high -> buy open, sell close", "momentum", IXG)
def _(k): d = D[k]; return run(k, d.open > d.high.shift(1) + 0.5 * d.atr.shift(1), 1, how="OC", stop=2)
@idea("69 Weekly inside bar -> buy a close above its high the next week, hold 5", "breakout", IXG)
def _(k):
    d = D[k]; w = d.resample("W-FRI").agg({"high": "max", "low": "min"}); ins = (w.high < w.high.shift(1)) & (w.low > w.low.shift(1))
    hi = w.high.where(ins).shift(1).reindex(d.index, method="ffill"); return run(k, d.close > hi, 1, None, 5)
@idea("70 Close at a 6-month high -> hold one month, 18 markets", "momentum", ALL)
def _(k): d = D[k]; return run(k, bme(d) & (d.close >= d.close.rolling(126).max()), 1, None, 21, stop=6)
@idea("71 Dual moving average 10/30 both sides, 18 markets", "trend", ALL)
def _(k):
    d = D[k]; a, b = ma(d.close, 10), ma(d.close, 30); x = (a > b) != (a.shift(1) > b.shift(1)); s = pd.Series(np.where(a > b, 1, -1), index=d.index)
    return run(k, x, s, x.shift(-0, fill_value=False), 60, stop=3)
@idea("72 Above 200MA with positive 20-day momentum: long indices, hold 20", "momentum", IX)
def _(k): d = D[k]; return run(k, bme(d) & up200(d) & (d.close > d.close.shift(20)), 1, None, 20, stop=6)
@idea("73 50-day slope / ATR > 0.1 (or < -0.1), 18 markets, exit on slope flip", "trend", ALL)
def _(k):
    d = D[k]; sl = (ma(d.close, 50) - ma(d.close, 50).shift(10)) / 10 / d.atr; s = pd.Series(np.where(sl > 0.1, 1, np.where(sl < -0.1, -1, 0)), index=d.index)
    st = s != s.shift(1); return run(k, st & (s != 0), s, (s.shift(-0) != s.shift(1)), 60, stop=3)
@idea("74 Breakout after a 30-day consolidation (range < 5 ATR), 18 markets, hold 10", "breakout", ALL)
def _(k):
    d = D[k]; hi = d.high.rolling(30).max().shift(1); lo = d.low.rolling(30).min().shift(1); tight = (hi - lo) < 5 * d.atr
    s = pd.Series(np.where(d.close > hi, 1, np.where(d.close < lo, -1, 0)), index=d.index); return run(k, tight & (s != 0), s, None, 10, stop=2)
# ---------- calendar (75-81) ----------
@idea("75 Tuesday close -> Wednesday close long", "calendar", IX)
def _(k): d = D[k]; return run(k, pd.Series(d.index.dayofweek == 1, index=d.index), 1, None, 1)
@idea("76 January effect: Russell first 5 trading days", "calendar", ["RUT", "SPX"])
def _(k):
    d = D[k]; first = pd.Series((d.index.month == 12) & ((d.index + pd.offsets.BDay(1)).month == 1), index=d.index); return run(k, first, 1, None, 5)
@idea("77 September effect: short indices for September", "calendar", IX)
def _(k): d = D[k]; return run(k, bme(d) & pd.Series((d.index + pd.offsets.BDay(1)).month == 9, index=d.index), -1, None, 21, stop=6)
@idea("78 Day after a US holiday: long the close before -> next close", "calendar", ["SPX", "NDX", "DJI", "RUT"])
def _(k):
    from pandas.tseries.holiday import USFederalHolidayCalendar
    hol = USFederalHolidayCalendar().holidays("2000-01-01", "2027-12-31"); d = D[k]
    prev_is_hol = pd.Series((d.index - pd.offsets.BDay(1)).isin(hol), index=d.index); return run(k, prev_is_hol.shift(-1, fill_value=False), 1, None, 1)
@idea("79 Triple-witching Friday: short Thursday close -> Friday close", "calendar", ["SPX", "NDX", "DJI", "RUT"])
def _(k):
    d = D[k]; t = d.index + pd.offsets.BDay(1); tw = (t.dayofweek == 4) & (t.day >= 15) & (t.day <= 21) & np.isin(t.month, [3, 6, 9, 12])
    return run(k, pd.Series(tw, index=d.index), -1, None, 1)
@idea("80 Quarter-end window dressing: long the last 5 days of the quarter", "calendar", IX)
def _(k):
    d = D[k]; q = d.index + pd.offsets.BQuarterEnd(0); s = pd.Series((q - d.index).days.isin([6, 7, 8]) & (d.index.dayofweek < 5), index=d.index)
    first = s & ~s.shift(1, fill_value=False); return run(k, first, 1, None, 5)
@idea("81 Overreaction: short the day after a > 2% up day", "mean reversion", IX)
def _(k): d = D[k]; return run(k, d.close / d.close.shift(1) - 1 > 0.02, -1, None, 1)
# ---------- cross-asset / regime (82-90) ----------
V = D["VIX"].close
@idea("82 VIX > 1.3 x its 20-day average -> buy index 5 days", "volatility", ["SPX", "NDX", "DJI", "RUT"])
def _(k): v = V.reindex(D[k].index).ffill(); return run(k, v > 1.3 * v.rolling(20).mean(), 1, None, 5, stop=4)
@idea("83 Gold/silver ratio z > 2 -> long silver (expect silver to catch up), exit z < 0", "pairs", ["SILVER"])
def _(k):
    r = (D["GOLD"].close / D["SILVER"].close).reindex(D[k].index).ffill(); z = (r - r.rolling(60).mean()) / r.rolling(60).std(); return run(k, z > 2, 1, z < 0, 30)
@idea("84 Stocks down 5 days while bonds up -> long US index 5 days", "cross-asset", ["SPX", "NDX", "RUT"])
def _(k):
    d = D[k]; t = D["TNOTE"].close.reindex(d.index).ffill(); return run(k, (d.close < d.close.shift(5)) & (t > t.shift(5)), 1, None, 5)
@idea("85 Oil +3% day -> short USD/CAD 3 days", "cross-asset", ["USDCAD"])
def _(k): o = D["OIL"].close.pct_change().reindex(D[k].index); return run(k, o > 0.03, -1, None, 3)
@idea("86 Copper +3% day -> long AUD/USD 3 days", "cross-asset", ["AUDUSD"])
def _(k): c = D["COPPER"].close.pct_change().reindex(D[k].index); return run(k, c > 0.03, 1, None, 3)
@idea("87 SPX day move > 1% -> FTSE/DAX next open->close in the same direction", "cross-asset", ["FTSE", "DAX"])
def _(k):
    r = D["SPX"].close.pct_change().shift(1).reindex(D[k].index); s = pd.Series(np.where(r > 0.01, 1, np.where(r < -0.01, -1, 0)), index=D[k].index)
    return run(k, s != 0, s, how="OC", stop=2)
@idea("88 Yen carry unwind: USD/JPY -3% in 5 days -> long USD/JPY 5 days", "cross-asset", ["USDJPY"])
def _(k): d = D[k]; return run(k, d.close / d.close.shift(5) - 1 < -0.03, 1, None, 5)
@idea("89 Gold down 3 days in a row above 200MA -> hold 3", "mean reversion", ["GOLD", "SILVER"])
def _(k):
    d = D[k]; dn = d.close < d.close.shift(1); return run(k, up200(d) & dn & dn.shift(1, fill_value=False) & dn.shift(2, fill_value=False), 1, None, 3)
@idea("90 10-year note golden cross (bond trend), exit death cross", "trend", ["TNOTE"])
def _(k): d = D[k]; a, b = ma(d.close, 50), ma(d.close, 200); return run(k, (a > b) & (a.shift(1) <= b.shift(1)), 1, a < b, 10 ** 6, stop=6)
# ---------- crypto (91-98), spot long or IG-style both sides where shorting ----------
@idea("91 Crypto weekend: long Friday close -> Sunday close", "crypto", CR)
def _(k): d = D[k]; return run(k, pd.Series(d.index.dayofweek == 4, index=d.index), 1, None, 2, fund=False)
@idea("92 Crypto -10% day -> buy, hold 3 days", "crypto", CR)
def _(k): d = D[k]; return run(k, d.close / d.close.shift(1) - 1 < -0.10, 1, None, 3, fund=False)
@idea("93 Crypto RSI(2) < 10 above its 200-day, exit RSI(2) > 70", "crypto", CR)
def _(k): d = D[k]; r = rsi(d.close, 2); return run(k, up200(d) & (r < 10), 1, r > 70, 10, fund=False)
@idea("94 Alt 20% below its 20-day high while BTC above its 50-day -> hold 7", "crypto", [c for c in CR if c != "BTCUSD"])
def _(k):
    d = D[k]; b = D["BTCUSD"].close.reindex(d.index).ffill(); return run(k, (d.close < 0.8 * d.high.rolling(20).max()) & (b > ma(b, 50)), 1, None, 7, fund=False)
@idea("95 ETH/BTC ratio z < -2 -> long ETH, exit z > 0", "crypto", ["ETHUSD"])
def _(k):
    r = (D["ETHUSD"].close / D["BTCUSD"].close); z = ((r - r.rolling(30).mean()) / r.rolling(30).std()).reindex(D[k].index); return run(k, z < -2, 1, z > 0, 20, fund=False)
@idea("96 Crypto 7-day high breakout above 50-day, exit 5-day low", "crypto", CR)
def _(k): d = D[k]; return run(k, (d.close >= d.close.rolling(7).max()) & (d.close > ma(d.close, 50)), 1, d.close <= d.close.rolling(5).min(), 30, fund=False)
@idea("97 Crypto low-volatility regime (20d vol < 40%/yr) above 100-day: long 10 days", "crypto", CR)
def _(k):
    d = D[k]; v = d.close.pct_change().rolling(20).std() * np.sqrt(365); return run(k, (v < 0.4) & (d.close > ma(d.close, 100)), 1, None, 10, fund=False)
@idea("98 Crypto Monday: long Sunday close -> Monday close", "crypto", CR)
def _(k): d = D[k]; return run(k, pd.Series(d.index.dayofweek == 6, index=d.index), 1, None, 1, fund=False)
@idea("99 Commodity pullback: RSI(2) < 10 above 200MA on oil/copper/silver, exit RSI > 70", "mean reversion", ["OIL", "COPPER", "SILVER", "NATGAS"])
def _(k): d = D[k]; r = rsi(d.close, 2); return run(k, up200(d) & (r < 10), 1, r > 70, 10)
@idea("100 FX pullback: RSI(2) < 10 above 200MA on 5 pairs, exit RSI > 70 (both sides)", "mean reversion", ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "USDCAD"])
def _(k):
    d = D[k]; r = rsi(d.close, 2); s = pd.Series(np.where(up200(d) & (r < 10), 1, np.where(~up200(d) & (r > 90), -1, 0)), index=d.index)
    return run(k, s != 0, s, (r > 70) & (s.shift(0) >= 0) | (r < 30) & (s <= 0), 10)

if __name__ == "__main__":
    from statistics import NormalDist
    reg_f = "runs/gate/registry.json"; reg = json.load(open(reg_f))
    for name, *_ in IDEAS:
        if f"50ideas2 {name}" not in reg: reg.append(f"50ideas2 {name}")
    json.dump(reg, open(reg_f, "w"), indent=0); N = len(reg); tstar = NormalDist().inv_cdf(1 - (1 - 0.95 ** (1 / N)) / 2)
    rows = []
    for name, fam, mk, fn in IDEAS:
        T = []
        for k in mk:
            try: T += [(t, r, k) for t, r in fn(k)]
            except Exception as e: print(name, k, "ERR", e)
        if not T: rows.append(dict(idea=name, family=fam, n=0, rating="F")); print(f"F  {name} — no signals"); continue
        t = pd.DataFrame(T, columns=["t", "R", "mkt"]).dropna(); t = t[np.isfinite(t.R)]; t["t"] = pd.to_datetime(t.t); y = t.groupby(t.t.dt.year).R.sum()
        m = t.R.mean(); tt = m / t.R.std() * np.sqrt(len(t)) if len(t) > 2 else 0; yp = (y > 0).mean(); l5 = t[t.t.dt.year >= 2022].R.mean()
        ly = t[t.t >= t.t.max() - pd.Timedelta(days=365)].R.mean()
        rating = ("A" if (tt >= tstar and yp >= 0.6 and l5 > 0) else "B" if (tt >= 2 and yp >= 0.55 and l5 > 0) else "C" if m > 0 else "F")
        rows.append(dict(idea=name, family=fam, markets=len(mk), n=len(t), per_year=round(len(t) / max(y.size, 1)), mean_ATR=round(m, 3), t=round(tt, 2),
                         years_pos=f"{int((y>0).sum())}/{y.size}", last5=round(l5, 3) if np.isfinite(l5) else None, last_year=round(ly, 3) if np.isfinite(ly) else None, rating=rating))
        print(f"{rating}  {name[:76]:76s} n{len(t):5d} {m:+.3f} t {tt:+.2f} years {int((y>0).sum())}/{y.size} last5 {l5:+.3f}", flush=True)
    R = pd.DataFrame(rows).sort_values(["rating", "t"], ascending=[True, False]); R.to_csv("runs/gate/fifty_ideas_2.csv", index=False)
    print(f"\nt* = {tstar:.2f} (N = {N})"); print(R.rating.value_counts().sort_index().to_string())
