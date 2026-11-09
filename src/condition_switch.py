"""Doc 201 — DK 23:09: "Every book should be studied for its worst periods/timeframes and adjusted accordingly". For every shortlisted book,
an honest walk-forward 'fallow' switch on conditions known in advance: calendar month, weekday, VIX band at the previous close (<15, 15-20,
20-30, >30) and, for intraday books, the New York hour. For each period P (a year for daily books, a month for intraday books) the
conditions to skip are chosen ONLY from the periods before P: a bucket is switched off if it has >= 15 earlier trades and a negative earlier
average (min. 8 earlier years / 4 earlier months). Result: the book traded every time vs with its switch, period by period."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2, market_search_4 as M4, market_search_5 as M5, trend_futures_bets as TF, market_search_6 as M6
from ladder_daily_tps import tps, IX as TIX
from gate_books import crypto15
vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).normalize(); vprev = vix.close.shift(1)
def frame(T, col="R"):
    t = pd.DataFrame(T); t["t"] = pd.to_datetime(t.t, utc=True); t = t.sort_values("t"); t["R"] = t[col]
    v = vprev.reindex(t.t.dt.normalize()).ffill().values
    t["vix"] = pd.cut(v, [0, 15, 20, 30, 200], labels=["v<15", "v15-20", "v20-30", "v>30"]).astype(str)
    t["month"] = t.t.dt.month.astype(str); t["dow"] = t.t.dt.dayofweek.astype(str); t["hour"] = t.t.dt.tz_convert("America/New_York").dt.hour.astype(str)
    return t
def switch(t, daily=True, conds=("month", "dow", "vix")):
    per = t.t.dt.year if daily else t.t.dt.tz_convert(None).dt.to_period("M")
    t = t.assign(per=per.values); rows = []; minp = 8 if daily else 4; offs_last = None
    for p in sorted(t.per.unique()):
        past = t[t.per < p]; cur = t[t.per == p]
        if past.per.nunique() < minp: continue
        off = {c: set(k for k, g in past.groupby(c).R if len(g) >= 15 and g.mean() < 0) for c in conds}
        keep = cur
        for c in conds: keep = keep[~keep[c].isin(off[c])]
        rows.append(dict(p=str(p), all=cur.R.sum(), sw=keep.R.sum(), n=len(cur), k=len(keep))); offs_last = off
    r = pd.DataFrame(rows)
    return r, offs_last
def show(name, T, daily=True, conds=("month", "dow", "vix")):
    t = frame(T); r, off = switch(t, daily, conds)
    if not len(r): print(f"{name}: not enough history for a walk-forward switch"); return
    tail = 5 if daily else 3
    print(f"{name:34s} periods {len(r):3d} | every time: total {r['all'].sum():+8.1f}, periods + {(r['all']>0).sum()}/{len(r)}, last {tail}: {r['all'].tail(tail).sum():+.1f} | "
          f"SWITCHED: total {r.sw.sum():+8.1f}, periods + {(r.sw>0).sum()}/{len(r)}, last {tail}: {r.sw.tail(tail).sum():+.1f}, trades kept {r.k.sum()}/{r.n.sum()} | "
          f"now off: {', '.join(f'{c}={sorted(v)}' for c, v in off.items() if v) or 'nothing'}", flush=True)
    return r
def sim(items):
    T = []
    for k, df, fn, kw in items:
        for x in G.simulate(df, fn(df), kw.get("manage"), kw.get("flat_at_session_end", False)): x["mkt"] = k; T.append(x)
    return T
def tps_T(items):
    T = []
    for d, c, f in items: T += [dict(t=e[0], R=e[1] * 100) for e in tps(d, c, f)]      # % of budget
    return T
if __name__ == "__main__":
    IX8 = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")
    show("TPS ladder indices+gold", tps_T([(M2.daily(k, .0003, 0), .0003, 0.06) for k in IX8]))
    CR = [s for s in ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "ADAUSD", "LTCUSD", "DOTUSD") if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")]
    cd = {s: crypto15(s).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for s in CR}
    print("TPS ladder coins: only 5 years — monthly walk-forward instead:")
    show("TPS ladder coins (monthly WF)", tps_T([(d, .002, 0) for d in cd.values()]), daily=False, conds=("dow", "vix"))
    show("RSI(2) pullback", sim([(k, M4.prep_rsi(k), M4.rsi_signals_t, {}) for k in IX8]))
    show("Double 7s", sim([(k, M5.prep(k), M5.d7, {"manage": M5.d7_manage}) for k in IX8]))
    show("12-month momentum", sim([(k, TF.prep(k), M5.tsmom, {}) for k in TF.SPREAD]))
    show("Trend 100-day (IG quarterly)", sim(TF.items))
    show("Halloween Nov-Apr", sim([(k, M2.daily(k, .0002, 0.06), M6.halloween, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225")]), conds=("dow", "vix"))
    for nm in ("IGNITION_v1.1_US_Tech_100", "GOLD_London_breakout_of_Asian_range", "AD_ignition_+_REGIME_+_COIL"):
        t = pd.read_csv(f"runs/gate/{nm}_trades.csv"); show(nm.replace("_", " ")[:34], t.to_dict("records"), daily=False, conds=("hour", "dow", "vix"))
