"""Doc 200 addendum — market search 7 (DK 23:06 "Yes please"). Daily, 2000-2026. Rules fixed from sources.
W  TPS ladder on MORE markets: silver, oil, copper, natural gas, 4 FX pairs, US 10-year note (does the ladder generalise beyond indices?).
X  TPS SHORT side on indices (Connors: below the 200-day, RSI(2) > 75 two days -> short ladder 10/20/30/40% on higher closes; exit RSI(2) < 30).
Y  CROSS-SECTIONAL WEEKLY REVERSAL across 7 indices (short-term reversal, Lehmann 1990 / country-index versions): each Friday buy the index
   that fell most that week (relative to the 7), short the one that rose most; hold to next Friday.
Z  CROSS-SECTIONAL MOMENTUM across 18 markets (Asness, Moskowitz & Pedersen 2013 "Value and momentum everywhere"): each month-end long the
   3 with the best 12-month-minus-last-month return, short the worst 3; hold a month. IG quarterly-bet costs."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import market_search_2 as M2, market_search_4 as M4, trend_futures_bets as TF
from ladder_daily_tps import tps, report
def tps_short(d, cost, fund_yr, rsi_in=75, maxd=30, kill=0.15, ladder=(0.1, 0.2, 0.3, 0.4)):
    x = d.copy(); x[["open", "high", "low", "close"]] = 1.0 / d[["open", "low", "high", "close"]].values     # mirror: shorting = owning 1/price
    C = x.close.values; r = M4.rsi2(d.close).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 1:
        if not (d.close.values[i] < ma[i] and r[i] > rsi_in and r[i - 1] > rsi_in): i += 1; continue
        qty = spent = 0.0; last = None; k = 0; j0 = i; j = i
        while j < n:
            if k < len(ladder) and (last is None or C[j] < last): w = ladder[k]; qty += w / (C[j] * (1 + cost)); spent += w; last = C[j]; k += 1
            avg = spent / qty
            if (r[j] < 30 or (j - j0) >= maxd or C[j] <= avg * (1 - kill)) and j > j0:
                out.append((d.index[j0], qty * C[j] * (1 - cost) - spent, spent, j - j0)); break
            j += 1
        i = j + 1
    return out
MORE = {"SILVER": .0008, "OIL": .0008, "COPPER": .0010, "NATGAS": .0020, "GBPUSD": .0001, "EURUSD": .0001, "USDJPY": .0001, "AUDUSD": .0001, "TNOTE": .0003}
E = []; [E.extend(tps(M2.daily(k, c, 0), c, 0.06)) for k, c in MORE.items()]; report("W TPS ladder, 9 other markets", E)
for k, c in MORE.items(): report(f"   W {k}", tps(M2.daily(k, c, 0), c, 0.06))
IX = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225")
E = []; [E.extend(tps_short(M2.daily(k, .0003, 0), .0003, 0.0)) for k in IX]; report("X TPS SHORT ladder, 7 indices", E)
# Y / Z: cross-sectional, return series per period
C = pd.DataFrame({k: M2.daily(k, .0003, 0).close for k in IX}); C.index = C.index.tz_convert(None).normalize(); C = C.groupby(level=0).last().ffill()
W = C.resample("W-FRI").last(); wr = W.pct_change()
pos = pd.DataFrame(0.0, index=wr.index, columns=wr.columns)
for t in wr.index[1:]:
    r = wr.loc[t].dropna()
    if len(r) >= 5: pos.loc[t, r.idxmin()] = 1; pos.loc[t, r.idxmax()] = -1
pnl = (pos.shift(1) * wr).sum(axis=1) - pos.diff().abs().sum(axis=1) * 0.0003
yy = pnl.groupby(pnl.index.year).sum()
print(f"Y weekly reversal 7 indices: weeks {len(pnl)} mean {100*pnl.mean():+.3f}%/week t {pnl.mean()/pnl.std()*np.sqrt(len(pnl)):+.2f} | years + {int((yy>0).sum())}/{len(yy)} | last 5y {100*pnl[pnl.index.year>=2022].mean():+.3f}%", flush=True)
A = pd.DataFrame({k: M2.daily(k, c, 0).close for k, c in TF.SPREAD.items()}); A.index = A.index.tz_convert(None).normalize(); A = A.groupby(level=0).last().ffill()
Mo = A.resample("ME").last(); mr = Mo.pct_change(); sig = Mo.shift(1) / Mo.shift(12) - 1
pos = pd.DataFrame(0.0, index=mr.index, columns=mr.columns)
for t in mr.index:
    s = sig.loc[t].dropna()
    if len(s) >= 10: pos.loc[t, s.nlargest(3).index] = 1 / 3; pos.loc[t, s.nsmallest(3).index] = -1 / 3
pnl = (pos.shift(1) * mr).sum(axis=1) - pos.diff().abs().sum(axis=1) * 0.001
yy = pnl.groupby(pnl.index.year).sum()
print(f"Z cross-sectional momentum 18 markets: months {len(pnl)} mean {100*pnl.mean():+.3f}%/month t {pnl.mean()/pnl.std()*np.sqrt(len(pnl)):+.2f} | years + {int((yy>0).sum())}/{len(yy)} | last 5y {100*pnl[pnl.index.year>=2022].mean():+.3f}%", flush=True)
