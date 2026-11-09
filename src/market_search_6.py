"""Doc 199 — market search 6 (DK 22:52 "More ideas please"). Daily, 2000-2026, gate v2. Rules fixed from their sources.
P  NR7 BREAKOUT (Toby Crabel, "Day Trading with Short Term Price Patterns", 1990): after a day with the narrowest range of the last 7,
   place a buy-stop above its high and a sell-stop below its low for the next day; stop = the other side; exit at that day's close.
   8 index/gold markets + 4 FX.
Q  PRE-HOLIDAY (Ariel 1990; Lakonishok & Smidt 1988): long the index at the close before a US market holiday (known in advance), sell at the
   next close. SPX, NDX, DJI, RUT.
R  HALLOWEEN / "SELL IN MAY" (Bouman & Jacobsen 2002): long indices only from the end of October to the end of April, month by month;
   flat May-October. 7 indices. (Compared with holding every month.)
S  FX MONTH-END REBALANCING (Melvin & Prins 2015): if US stocks beat non-US stocks over the month to 3 days before month end, foreign
   investors sell dollars to rebalance -> sell USD vs GBP and EUR for the last 2 trading days (and the reverse). GBP/USD, EUR/USD, AUD/USD.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2
from gate_books import sigframe
R = []
def go(name, items):
    r = G.judge2(name, items, daily=True); R.append(r); print(G.line2(r), flush=True)
    t = pd.DataFrame(sum([G.simulate(df, fn(df), kw.get("manage")) for _, df, fn, kw in items], []))
    if len(t): y = t.groupby(pd.to_datetime(t.t).dt.year).R.sum(); print(f"    years positive {int((y>0).sum())}/{len(y)}, last 5y mean {t[pd.to_datetime(t.t).dt.year>=2022].R.mean():+.3f}, trades/yr {len(t)/max(len(y),1):.0f}", flush=True)
CP = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003,
      "GBPUSD": .0001, "EURUSD": .0001, "USDJPY": .0001, "AUDUSD": .0001}

def nr7(d):
    rng = d.high - d.low; nr = (rng <= rng.rolling(7).min()).values & np.isfinite(d.atr.values)
    ix = np.where(nr)[0]; H, L = d.high.values[ix], d.low.values[ix]
    f1 = sigframe(d.index[ix], 1, "stop", H, L, np.nan, 1, valid=1); f2 = sigframe(d.index[ix] + pd.Timedelta(seconds=1), -1, "stop", L, H, np.nan, 1, valid=1)
    # one order per bar in the gate: keep the side closer to the close (most likely to trigger first is unknowable; take the nearer)
    C = d.close.values[ix]; near_up = (H - C) <= (C - L)
    f = pd.concat([f1[near_up], f2[~near_up].set_axis(d.index[ix][~near_up])]).sort_index()
    return f

def preholiday(d):
    from pandas.tseries.holiday import USFederalHolidayCalendar
    hol = USFederalHolidayCalendar().holidays("2000-01-01", "2027-12-31")
    dd = d.index.tz_convert(None).normalize(); nxt = dd + pd.offsets.BDay(1)
    ix = np.where(nxt.isin(hol) & np.isfinite(d.atr.values))[0]
    return sigframe(d.index[ix], 1, "close", np.nan, 4 * d.atr.values[ix], np.nan, 1, dist=True)

def halloween(d, months=(11, 12, 1, 2, 3, 4)):
    dd = d.index.tz_convert(None).normalize(); ix = np.where(dd == dd + pd.offsets.BMonthEnd(0))[0]
    nm = (dd[ix] + pd.offsets.BDay(1)).month; ix = ix[np.isin(nm, months) & np.isfinite(d.atr.values[ix])]
    return sigframe(d.index[ix], 1, "close", np.nan, 8 * d.atr.values[ix], np.nan, 21, dist=True)

spx = M2.daily("SPX", .0002, 0); ftse = M2.daily("FTSE", .0002, 0); dax = M2.daily("DAX", .0002, 0)
def monthend_fx(d):
    dd = d.index.tz_convert(None).normalize(); bme = dd + pd.offsets.BMonthEnd(0); sig_day = bme - pd.offsets.BDay(3)
    ix = np.where(dd == sig_day)[0]; out_i, side = [], []
    for i in ix:
        t = d.index[i]; m0 = (t.tz_convert(None).normalize() - pd.offsets.BMonthBegin(1))
        def ret(x):
            xs = x.close[(x.index.tz_convert(None) >= m0) & (x.index <= t)]
            return xs.iloc[-1] / xs.iloc[0] - 1 if len(xs) > 5 else np.nan
        us = ret(spx); ex = np.nanmean([ret(ftse), ret(dax)])
        if not np.isfinite(us) or not np.isfinite(ex): continue
        out_i.append(i + 1 if i + 1 < len(d) else i); side.append(1 if us > ex else -1)   # US beat -> sell USD -> BUY GBP/USD (enter the close 2 days before month end)
    out_i = np.array(out_i, int)
    return sigframe(d.index[out_i], side, "close", np.nan, 4 * d.atr.values[out_i], np.nan, 2, dist=True)

if __name__ == "__main__":
    go("P NR7 breakout 12 markets", [(k, M2.daily(k, c, 0.06), nr7, {}) for k, c in CP.items()])
    go("Q PRE-HOLIDAY 4 US indices", [(k, M2.daily(k, .0002, 0.06), preholiday, {}) for k in ("SPX", "NDX", "DJI", "RUT")])
    go("R HALLOWEEN Nov-Apr 7 indices", [(k, M2.daily(k, .0002, 0.06), halloween, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225")])
    go("R2 every month (comparison) 7 indices", [(k, M2.daily(k, .0002, 0.06), lambda x: halloween(x, tuple(range(1, 13))), {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225")])
    go("S FX month-end rebalancing 3 pairs", [(k, M2.daily(k, .0001, 0.0), monthend_fx, {}) for k in ("GBPUSD", "EURUSD", "AUDUSD")])
    open(f"{G.OUT}/search6.txt", "w").write("\n".join(G.line2(r) for r in R) + "\n")
