"""Doc 197 — market search 2: ideas from published research (DK 9 Nov: "go online to expert trading sites"), all through THE GATE.
A  NOISE-BAND INTRADAY MOMENTUM (Zarattini, Aziz & Barbon 2024, "Beat the Market", SPY 2007-24 Sharpe 1.33 net):
   sigma(t) = mean over the prior 14 days of |close(t)/open(09:30) - 1| at the same time of day; upper = max(open, prior close) x (1+sigma),
   lower = min(open, prior close) x (1-sigma). Checked only at bars closing on HH:00 / HH:30 from 10:00: close above upper -> long,
   below lower -> short (next bar's open). Stop = the band, trailed with VWAP (long: max(upper, VWAP)); flat at 16:00. Rules as published.
B  LAST-HALF-HOUR MOMENTUM (Gao, Han, Li & Zhou 2018, JFE): sign of (prior close -> 10:00) return; trade 15:30 -> 16:00 in that direction.
C  BITCOIN 22:00 UTC SEASONALITY (Quantpedia, from Gemini 2015-21): long at 22:00 UTC, out at 00:00.
D  DAILY TREND FOLLOWING across 20 markets (the 'century of evidence' family; Turtle-style, rules fixed in advance): close above the prior
   100-day high -> long next open (below the 100-day low -> short); initial stop 3 x ATR(20); trailing stop = the prior 50-day opposite
   channel; IG-style costs + overnight funding ~5%/yr of notional.
E  TURN OF THE MONTH (Hatlemark & Grohshennig 2022 et al.): long the index at the close 1 trading day before month end, out at the close
   of the 3rd trading day of the new month; SPX, NDX, DJI, RUT, DAX, FTSE.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G
from gate_books import sigframe, load5, NY, crypto15
R = []
def show(r): R.append(r); print(G.line(r) + (f" | by market {r.get('by_market')}" if r.get("by_market") else ""), flush=True)

# ---------- A: noise band ----------
def nb_prep(f, cost):
    d = load5(f)[["open", "high", "low", "close"]].astype(float)
    lt = d.index.tz_convert(NY); m = lt.hour * 60 + lt.minute; d = d[(m >= 570) & (m < 960)].copy()
    lt = d.index.tz_convert(NY); d["session"] = pd.Series(lt.date, index=d.index).astype(str); d["tod"] = lt.hour * 60 + lt.minute
    o = d.groupby("session").open.transform("first"); d["dopen"] = o
    pc = d.groupby("session").close.last().shift(1); d["pclose"] = d.session.map(pc)
    mv = (d.close / o - 1).abs(); piv = mv.groupby([d.session, d.tod]).first().unstack()
    sig = piv.shift(1).rolling(14, min_periods=14).mean()                       # prior 14 days, same time of day
    d["sigma"] = [sig.at[s, t] if s in sig.index and t in sig.columns else np.nan for s, t in zip(d.session, d.tod)]
    d["up"] = np.maximum(d.dopen, d.pclose) * (1 + d.sigma); d["dn"] = np.minimum(d.dopen, d.pclose) * (1 - d.sigma)
    tp = (d.high + d.low + d.close) / 3; d["vwap"] = (tp).groupby(d.session).cumsum() / d.groupby("session").cumcount().add(1)
    d["cost"] = cost; d["atr"] = G.atr(d).shift(1); d["eligible"] = (d.tod + 5) % 30 == 0
    return d
def nb_signals(d):
    end = d.tod.values + 5; chk = (end % 30 == 0) & (end >= 600) & (end < 960)
    C = d.close.values; up = d.up.values; dn = d.dn.values
    s = np.where(chk & (C > up), 1, np.where(chk & (C < dn), -1, 0)); ix = np.where((s != 0) & np.isfinite(up))[0]
    st = np.where(s[ix] == 1, np.maximum(up[ix], d.vwap.values[ix]) , np.minimum(dn[ix], d.vwap.values[ix]))
    st = np.where(s[ix] == 1, np.minimum(st, C[ix] * 0.9995), np.maximum(st, C[ix] * 1.0005))   # stop must sit beyond entry
    return sigframe(d.index[ix], s[ix], "market", np.nan, st, np.nan, 10 ** 6)
def nb_manage(df, k, st):
    s = st["s"]; b = df["up"].values[k] if s == 1 else df["dn"].values[k]; v = df["vwap"].values[k]
    t = max(b, v) if s == 1 else min(b, v)
    if (s == 1 and t > st["stop"] and t < df.close.values[k]) or (s == -1 and t < st["stop"] and t > df.close.values[k]): st["stop"] = t

# ---------- B: last half hour ----------
def lh_signals(d):
    end = d.tod.values + 5; C = d.close.values
    at10 = pd.Series(np.where(end == 600, C, np.nan), index=d.index).groupby(d.session.values).transform("max").values
    first = (at10 / d.pclose.values - 1)
    ix = np.where((end == 930) & np.isfinite(first) & (first != 0))[0]          # the 15:25-15:30 bar has closed -> enter at 15:30 open
    s = np.sign(first[ix]).astype(int); a = d.atr.values[ix]
    return sigframe(d.index[ix], s, "market", np.nan, 50 * a, np.nan, 6, dist=True)   # wide disaster stop; exit at 16:00 (6 bars)

# ---------- C: BTC 22:00 UTC ----------
def btc22_signals(h):
    ix = np.where(h.index.hour == 21)[0]                                          # the 21:00-22:00 bar closes at 22:00 -> buy 22:00 open
    return sigframe(h.index[ix], 1, "market", np.nan, 20 * h.atr.values[ix], np.nan, 2, dist=True)

# ---------- D: daily trend ----------
def trend_signals(d):
    hh = d.high.rolling(100).max().shift(1).values; ll = d.low.rolling(100).min().shift(1).values; C = d.close.values; a = d.atr.values
    s = np.where(C > hh, 1, np.where(C < ll, -1, 0)); ix = np.where((s != 0) & np.isfinite(a))[0]
    return sigframe(d.index[ix], s[ix], "market", np.nan, 3 * a[ix], np.nan, 10 ** 6, dist=True)
def trend_manage(df, k, st):
    s = st["s"]; ch = df["lo50"].values[k] if s == 1 else df["hi50"].values[k]
    if np.isfinite(ch) and ((s == 1 and ch > st["stop"]) or (s == -1 and ch < st["stop"])): st["stop"] = ch

# ---------- E: turn of month ----------
def tom_signals(d):
    # the calendar is known in advance: the month's last weekday (BMonthEnd) and the weekday before it — no use of future bars
    dd = d.index.tz_convert(None).normalize(); bme = dd + pd.offsets.BMonthEnd(0)
    prev_bd = bme - pd.offsets.BDay(1)
    pos = np.where(dd == prev_bd)[0]
    return sigframe(d.index[pos], 1, "close", np.nan, 10 * d.atr.values[pos], np.nan, 4, dist=True)

def daily(k, cost_pct, carry_pct_yr=0.05):
    d = pd.read_csv(f"data_daily/{k}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d.astype(float)
    d["atr"] = G.atr(d, 20).shift(1); d["cost"] = d.close * cost_pct; d["carry"] = d.close * carry_pct_yr / 365 * 1.4  # ~weekend days
    d["hi50"] = d.high.rolling(50).max().shift(1); d["lo50"] = d.low.rolling(50).min().shift(1); d["eligible"] = True
    return d

if __name__ == "__main__":
    ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
    if not ONLY or ONLY == "A" or ONLY == "B":
        IX = [("US Tech 100", "data_nq_cache/nq_5m.csv", 1.0), ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", 0.4), ("Wall Street", "data_ig_cache/USA30IDXUSD_5m.csv", 2.4)]
        P = {n: nb_prep(f, c) for n, f, c in IX}
        if ONLY in ("", "A"):
            for n, d in P.items(): show(G.judge(f"NOISEBAND {n}", d, nb_signals, manage=nb_manage, flat_at_session_end=True, max_bars_for_random=24))
            show(G.judge_pool("NOISEBAND pooled 3 US indices", [(n, d, nb_signals, {"manage": nb_manage, "flat_at_session_end": True}) for n, d in P.items()]))
        if ONLY in ("", "B"):
            for n, d in P.items(): show(G.judge(f"LASTHALFHOUR {n}", d, lh_signals, flat_at_session_end=True))
            show(G.judge_pool("LASTHALFHOUR pooled", [(n, d, lh_signals, {"flat_at_session_end": True}) for n, d in P.items()]))
    if ONLY in ("", "C"):
        for sym in ("BTCUSD", "ETHUSD"):
            h = crypto15(sym).resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
            h["cost"] = h.close * 0.001; h["atr"] = G.atr(h).shift(1); h["eligible"] = True
            show(G.judge(f"BTC22UTC {sym}", h, btc22_signals))
    if ONLY in ("", "D"):
        CP = {"SPX": .0002, "NDX": .0002, "DJI": .0002, "RUT": .0005, "DAX": .0002, "FTSE": .0002, "N225": .0005, "GOLD": .0003, "SILVER": .0008, "OIL": .0008,
              "COPPER": .0010, "NATGAS": .0020, "GBPUSD": .0001, "EURUSD": .0001, "USDJPY": .0001, "AUDUSD": .0001, "USDCAD": .0002, "TNOTE": .0003,
              "BTC": .0040, "ETH": .0050}
        items = [(k, daily(k, c), trend_signals, {"manage": trend_manage}) for k, c in CP.items()]
        show(G.judge_pool("TREND100 daily 20 markets", items))
    if ONLY in ("", "E"):
        items = [(k, daily(k, .0002, 0.05), tom_signals, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE")]
        show(G.judge_pool("TURN-OF-MONTH 6 indices", items))
    open(f"{G.OUT}/search2_{ONLY or 'all'}.txt", "w").write("\n".join(G.line(r) + (f" | by market {r.get('by_market')}" if r.get('by_market') else '') for r in R) + "\n")
