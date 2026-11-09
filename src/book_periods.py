"""Doc 201 — DK 9 Nov 23:09: "Every book should be studied for its worst periods/timeframes and adjusted accordingly."
For each shortlisted book: results by things knowable in advance (month, weekday, VIX band at the prior close; hour for intraday books), then
an HONEST switch test — a bucket is switched off only if it was negative in the data BEFORE the period being judged:
  daily books (20+ years): expanding walk-forward by year (buckets chosen from all earlier years, >= 8 of them);
  intraday / short-history books (~1-5 years): chosen on the first half, judged on the second half.
A switch is ADOPTED only if, out of sample, it raises the total AND keeps >= 50% of the trades. Output runs/gate/book_periods.txt."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, market_search_2 as M2, market_search_4 as M4, market_search_5 as M5, market_search_6 as M6, trend_futures_bets as TF
from ladder_daily_tps import tps
from gate_books import load5
import market_search_3 as M3
vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).normalize(); vprev = vix.close.shift(1)
def sim(items):
    T = []
    for k, df, fn, kw in items:
        for x in G.simulate(df, fn(df), kw.get("manage"), kw.get("flat_at_session_end", False)): x["mkt"] = k; T.append(x)
    t = pd.DataFrame(T)[["t", "R"]]; t["t"] = pd.to_datetime(t.t, utc=True); return t
IX8 = ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")
B = {}
B["TPS ladder indices+gold"] = (pd.DataFrame([(t, p) for k in IX8 for t, p, _, _ in tps(M2.daily(k, .0003, 0), .0003, 0.06)], columns=["t", "R"]), True)
CR = ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "ADAUSD", "LTCUSD", "DOTUSD")
from gate_books import crypto15
cd = {s: crypto15(s).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for s in CR if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")}
B["TPS ladder coins"] = (pd.DataFrame([(t, p) for d in cd.values() for t, p, _, _ in tps(d, .002, 0)], columns=["t", "R"]), False)
B["RSI(2) pullback"] = (sim([(k, M4.prep_rsi(k), M4.rsi_signals_t, {}) for k in IX8]), True)
B["Double 7s"] = (sim([(k, M5.prep(k), M5.d7, {"manage": M5.d7_manage}) for k in IX8]), True)
B["12-month momentum"] = (sim([(k, TF.prep(k), M5.tsmom, {}) for k in TF.SPREAD]), True)
B["Trend 100-day"] = (sim(TF.items), True)
B["Halloween"] = (sim([(k, M2.daily(k, .0002, 0.06), M6.halloween, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225")]), True)
for nm, f in (("Ignition US hours", "IGNITION_v1.1_US_Tech_100"), ("Gold London breakout", "GOLD_London_breakout_of_Asian_range"), ("Ignition all-hours regime+coil", "AD_ignition_+_REGIME_+_COIL")):
    t = pd.read_csv(f"runs/gate/{f}_trades.csv", parse_dates=["t"])[["t", "R"]]; t["t"] = pd.to_datetime(t.t, utc=True); B[nm] = (t, False)
g = load5("data_ig_cache/DEUIDXEUR_5m.csv")[["open", "high", "low", "close"]].astype(float); g["cost"] = 1.2; g["atr"] = G.atr(g).shift(1)
lt = g.index.tz_convert("UTC"); g["session"] = pd.Series(lt.date, index=g.index).astype(str); g["eligible"] = (lt.hour >= 6) & (lt.hour < 19)
B["DAX Asian-range breakout"] = (sim([("DAX", g, M3.gold_signals, {"flat_at_session_end": True})]), False)
import positioning_test as PT
B["BTC crowd contrarian"] = (sim([("BTC", PT.d, PT.crowd, {})]), False)
out = []
def p(s): print(s, flush=True); out.append(s)
def buckets(t, daily):
    v = vprev.reindex(t.t.dt.normalize()).ffill().values
    b = {"month": t.t.dt.month, "weekday": t.t.dt.dayofweek, "vix": pd.Series(pd.cut(v, [0, 15, 20, 30, 300], labels=[0, 1, 2, 3]), index=t.index).astype(float)}
    if not daily: b["hour"] = t.t.dt.tz_convert("America/New_York").dt.hour
    return b
NAMES = {"month": lambda k: ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(k)],
         "weekday": lambda k: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][int(k)], "vix": lambda k: ["VIX<15", "VIX 15-20", "VIX 20-30", "VIX>30"][int(k)],
         "hour": lambda k: f"{int(k):02d}h NY"}
ADOPT = {}
for name, (t, daily) in B.items():
    t = t.dropna().sort_values("t").reset_index(drop=True); bk = buckets(t, daily); yrs = t.t.dt.year
    p(f"\n== {name}: n{len(t)}, {t.t.min().date()}..{t.t.max().date()}, mean {t.R.mean():+.3f}")
    long_hist = daily and yrs.nunique() >= 15
    for dim, key in bk.items():
        key = key.reindex(t.index)
        if long_hist:
            keep_oos, base_oos, kept, tot = 0.0, 0.0, 0, 0
            for y in sorted(yrs.unique()):
                past = t[yrs < y]
                if past.t.dt.year.nunique() < 8: continue
                m = past.groupby(key[yrs < y]).R.mean(); cnt = past.groupby(key[yrs < y]).R.size()
                off = set(m[(m < 0) & (cnt >= 10)].index)
                cur = t[yrs == y]; ck = key[yrs == y]; on = cur[~ck.isin(off)]
                keep_oos += on.R.sum(); base_oos += cur.R.sum(); kept += len(on); tot += len(cur)
            m_all = t.groupby(key).R.mean(); cnt = t.groupby(key).R.size(); off_now = sorted(m_all[(m_all < 0) & (cnt >= 10)].index)
        else:
            h = t.t < t.t.iloc[len(t) // 2]; m = t[h].groupby(key[h]).R.mean(); cnt = t[h].groupby(key[h]).R.size()
            off = set(m[(m < 0) & (cnt >= 5)].index); cur = t[~h]; on = cur[~key[~h].isin(off)]
            keep_oos, base_oos, kept, tot = on.R.sum(), cur.R.sum(), len(on), len(cur)
            m_all = t.groupby(key).R.mean(); cnt = t.groupby(key).R.size(); off_now = sorted(m_all[(m_all < 0) & (cnt >= 5)].index)
        ok = tot > 0 and keep_oos > base_oos and kept >= 0.5 * tot
        lab = ", ".join(NAMES[dim](k) for k in off_now) or "none"
        p(f"  {dim:8s} worst buckets now: {lab:40s} | out-of-sample: all {base_oos:+.1f} -> switched {keep_oos:+.1f}, trades kept {kept}/{tot} | {'ADOPT' if ok and off_now else 'keep running'}")
        if ok and off_now: ADOPT.setdefault(name, []).append((dim, lab))
p("\nADOPTED switches (passed out of sample):")
for k, v in ADOPT.items(): p(f"  {k}: " + "; ".join(f"off in {lab} ({dim})" for dim, lab in v))
open("runs/gate/book_periods.txt", "w").write("\n".join(out) + "\n")
