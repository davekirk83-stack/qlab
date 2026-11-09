"""Doc 199 — market search 5 (DK 22:47 "Find more possibilities"). Long-history daily ideas (the strongest evidence we can get), gate v2.
M  TIME-SERIES MOMENTUM (Moskowitz, Ooi & Pedersen 2012, JFE): each month-end, long a market if its 12-month return is positive, short if
   negative; hold to the next month-end. 18 markets as IG quarterly bets (forward spread, roll, index basis).
N  DOUBLE 7s (Connors & Alvarez): index above its 200-day average closes at a 7-day low -> buy the close; sell at the close of a 7-day high;
   disaster stop 3 ATR; max 15 days. 7 indices + gold.
O  IBS MEAN REVERSION (internal bar strength, Quantpedia / Pagonidis): close in the bottom 20% of the day's range -> buy the close, sell the
   next close. 7 indices + gold.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2, trend_futures_bets as TF
from gate_books import sigframe
R = []
def go(name, items, daily=True):
    r = G.judge2(name, items, daily=daily); R.append(r); print(G.line2(r), flush=True)
    t = pd.DataFrame(sum([G.simulate(df, fn(df), kw.get("manage")) for _, df, fn, kw in items], []))
    if len(t): y = t.groupby(pd.to_datetime(t.t).dt.year).R.sum(); print(f"    years positive {int((y>0).sum())}/{len(y)}, last 5y mean {t[pd.to_datetime(t.t).dt.year>=2022].R.mean():+.3f}, trades/yr {len(t)/max(len(y),1):.0f}", flush=True)

def tsmom(d):
    me = d.index.tz_convert(None).to_period("M"); last = pd.Series(me).shift(-1).values != pd.Series(me).values
    # month-end known in advance from the calendar: use BMonthEnd like turn-of-month
    dd = d.index.tz_convert(None).normalize(); ix = np.where(dd == dd + pd.offsets.BMonthEnd(0))[0]
    r12 = (d.close / d.close.shift(252) - 1).values; s = np.sign(r12[ix]); ok = np.isfinite(s) & (s != 0) & np.isfinite(d.atr.values[ix])
    ix = ix[ok]; s = s[ok].astype(int)
    return sigframe(d.index[ix], s, "close", np.nan, 6 * d.atr.values[ix], np.nan, 21, dist=True)
go("M TIME-SERIES MOMENTUM 12m 18 markets", [(k, TF.prep(k), tsmom, {}) for k in TF.SPREAD])

def d7(d):
    C = d.close; ok = (C > C.rolling(200).mean()) & (C <= C.rolling(7).min()) & d.atr.notna(); ix = np.where(ok.values)[0]
    return sigframe(d.index[ix], 1, "close", np.nan, 3 * d.atr.values[ix], np.nan, 15, dist=True)
def d7_manage(df, k, st):
    if df.close.values[k] >= df["hi7"].values[k]: st["stop"] = df.close.values[k] * 1.5   # forces an exit next bar at the open (stop above price)
def prep(k):
    d = M2.daily(k, .0003, 0.06); d["hi7"] = d.close.rolling(7).max(); return d
IX = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")
go("N DOUBLE 7s 8 markets", [(k, prep(k), d7, {"manage": d7_manage}) for k in IX])

def ibs(d):
    rng = (d.high - d.low).replace(0, np.nan); v = ((d.close - d.low) / rng).values; ix = np.where((v < 0.2) & np.isfinite(d.atr.values))[0]
    return sigframe(d.index[ix], 1, "close", np.nan, 3 * d.atr.values[ix], np.nan, 1, dist=True)
go("O IBS low close 8 markets", [(k, M2.daily(k, .0003, 0.06), ibs, {}) for k in IX])
open(f"{G.OUT}/search5.txt", "w").write("\n".join(G.line2(r) for r in R) + "\n")
