"""Doc 199 — market search 4 (DK 9 Nov 22:38: "More ideas"). Every rule fixed in advance from its published source; judged by GATE v2.
H  ASIAN-RANGE BREAKOUT, same fixed rules as the gold book, on other London-session markets: GBP/USD, USD/JPY, Germany 40, FTSE 100
   (does the gold result generalise, or is it gold-specific?).
I  RSI(2) PULLBACK (Connors & Alvarez, "Short Term Trading Strategies That Work", 2008): index above its 200-day average and RSI(2) < 10
   -> buy at the close; sell at the close when price closes above its 5-day average; disaster stop 3 ATR; max 10 days. 7 indices + gold.
J  VIX SPIKE REVERSION: VIX up >= 15% on the day (doc 193 found spikes revert) -> buy the S&P 500 / Nasdaq-100 at the close, hold 5 days.
K  CRYPTO 20-DAY-HIGH BREAKOUT (Quantpedia "Revisiting trend-following and mean-reversion in Bitcoin": the MAX rule held out of sample
   2022-24): close at a new 20-day high -> buy next open; exit when it closes below the 10-day low. Spot, long only (Revolut X-style costs,
   no funding). BTC, ETH, SOL + 7 large alts (Coinbase daily from 15-min data).
L  OPENING-GAP FADE (indices): cash open gaps >= 0.5 ATR(daily) from the prior close -> fade at the 09:35 bar close toward the prior close;
   stop 1 x gap beyond the open; flat at 12:00 NY. US Tech 100, US 500, Wall Street.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G
from gate_books import load5, NY, sigframe, crypto15
import market_search_2 as M2, market_search_3 as M3
ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
R = []
def go(name, items, daily=False):
    if ONLY and not name.startswith(ONLY): return
    r = G.judge2(name, items, daily=daily); R.append(r); print(G.line2(r), flush=True)

# H — Asian-range breakout elsewhere (prices scaled as in the data: GBP/USD x10000, USD/JPY x100)
for nm, f, cost in (("GBP/USD", "data_ig_cache/GBPUSD_IG_5m.csv", 1.4), ("USD/JPY", "data_ig_cache/USDJPY_IG_5m.csv", 1.0),
                    ("Germany 40", "data_ig_cache/DEUIDXEUR_5m.csv", 1.2), ("FTSE 100", "data_ig_cache/GBRIDXGBP_5m.csv", 1.0)):
    if ONLY and ONLY != "H": continue
    g = load5(f)[["open", "high", "low", "close"]].astype(float); g["cost"] = cost; g["atr"] = G.atr(g).shift(1)
    lt = g.index.tz_convert("UTC"); g["session"] = pd.Series(lt.date, index=g.index).astype(str); g["eligible"] = (lt.hour >= 6) & (lt.hour < 19)
    go(f"H ASIAN-RANGE BREAKOUT {nm}", [(nm, g, M3.gold_signals, {"flat_at_session_end": True})])

# I — RSI(2)
def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def rsi_signals(d):
    C = d.close; ok = (C > C.rolling(200).mean()) & (rsi2(C) < 10) & d.atr.notna()
    ix = np.where(ok.values)[0]
    return sigframe(d.index[ix], 1, "close", np.nan, 3 * d.atr.values[ix], np.nan, 10, dist=True)
def rsi_manage(df, k, st):
    if df.close.values[k] > df["ma5"].values[k]: st["stop"] = df.close.values[k] * 10 if st["s"] == -1 else min(st.get("stop"), df.close.values[k] * 0 + df.close.values[k] * 10) if False else st["stop"]
def prep_rsi(k):
    d = M2.daily(k, .0003, 0.06); d["ma5"] = d.close.rolling(5).mean(); return d
# exit "close above the 5-day average": modelled as a target at the 5-day average known at the signal bar (conservative: fixed at entry)
def rsi_signals_t(d):
    f = rsi_signals(d); f["target"] = (d["ma5"].reindex(f.index).values - d.close.reindex(f.index).values).clip(min=0.1 * d.atr.reindex(f.index).values)
    return f
go("I RSI2 pullback 8 markets", [(k, prep_rsi(k), rsi_signals_t, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225", "GOLD")], daily=True)

# J — VIX spike
vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).normalize(); vchg = vix.close.pct_change()
def vix_signals(d):
    v = vchg.reindex(d.index.normalize()).values; ix = np.where((v >= 0.15) & np.isfinite(d.atr.values))[0]
    return sigframe(d.index[ix], 1, "close", np.nan, 4 * d.atr.values[ix], np.nan, 5, dist=True)
go("J VIX spike reversion SPX NDX", [(k, M2.daily(k, .0003, 0.06), vix_signals, {}) for k in ("SPX", "NDX")], daily=True)

# K — crypto 20-day high, spot
def kday(sym):
    d = crypto15(sym).resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    d["atr"] = G.atr(d, 20).shift(1); d["cost"] = d.close * 0.002; d["lo10"] = d.low.rolling(10).min().shift(1); d["eligible"] = True; return d
def k_signals(d):
    hh = d.high.rolling(20).max().shift(1).values; ix = np.where((d.close.values > hh) & np.isfinite(d.atr.values))[0]
    return sigframe(d.index[ix], 1, "market", np.nan, 3 * d.atr.values[ix], np.nan, 10 ** 6, dist=True)
def k_manage(df, k, st):
    ch = df["lo10"].values[k]
    if np.isfinite(ch) and ch > st["stop"]: st["stop"] = ch
go("K CRYPTO 20-day high breakout 10 coins", [(s, kday(s), k_signals, {"manage": k_manage}) for s in
   ("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD", "AVAXUSD", "LINKUSD", "ADAUSD", "LTCUSD", "DOTUSD") if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")], daily=True)

# L — gap fade
def gap_prep(f, cost):
    d = load5(f)[["open", "high", "low", "close"]].astype(float); lt = d.index.tz_convert(NY); m = lt.hour * 60 + lt.minute
    d = d[(m >= 570) & (m < 960)].copy(); lt = d.index.tz_convert(NY); d["session"] = pd.Series(lt.date, index=d.index).astype(str); d["tod"] = lt.hour * 60 + lt.minute
    daily = d.groupby("session").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
    datr = (daily.h - daily.l).rolling(14).mean().shift(1); pc = daily.c.shift(1)
    d["pc"] = d.session.map(pc); d["datr"] = d.session.map(datr); d["dopen"] = d.session.map(daily.o)
    d["cost"] = cost; d["atr"] = d["datr"]; d["eligible"] = d.tod == 570
    return d
def gap_signals(d):
    gap = (d.dopen - d.pc).values; ix = np.where((d.tod.values == 570) & np.isfinite(gap) & (np.abs(gap) >= 0.5 * d.datr.values))[0]
    s = -np.sign(gap[ix]).astype(int); C = d.close.values[ix]
    stop = d.dopen.values[ix] + np.sign(gap[ix]) * np.abs(gap[ix]); tgt = d.pc.values[ix]
    ok = s * (C - stop) > 0
    return sigframe(d.index[ix][ok], s[ok], "close", np.nan, stop[ok], tgt[ok], 30)
go("L GAP FADE 3 US indices", [(n, gap_prep(f, c), gap_signals, {"flat_at_session_end": True}) for n, f, c in
   (("US Tech 100", "data_nq_cache/nq_5m.csv", 1.0), ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", 0.4), ("Wall Street", "data_ig_cache/USA30IDXUSD_5m.csv", 2.4))])
open(f"{G.OUT}/search4_{ONLY or 'all'}.txt", "w").write("\n".join(G.line2(r) for r in R) + "\n")
