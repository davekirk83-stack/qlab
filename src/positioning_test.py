"""Doc 199 — crypto positioning ideas from Binance futures metrics (Dec 2021 - Nov 2026), BTC, through GATE v2. Rules fixed in advance.
T  CROWD CONTRARIAN (DK's long/short ratio): daily at 00:00 UTC, the Binance account long/short ratio vs its prior 90 days:
   top 10% (crowded longs) -> short 3 days; bottom 10% (crowded shorts) -> long 3 days.
U  OI-CONFIRMED BREAKOUT: daily close at a new 20-day high (low) AND open interest up >= 5% over those 3 days -> go with it 5 days.
V  OI FLUSH BUY: open interest down >= 8% in 24h with price down >= 4% (a liquidation cascade) -> buy, hold 3 days."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G
from gate_books import sigframe
b = pd.read_parquet("data_long/btc_1m.parquet"); b = b[b.index >= "2021-11-01"]
d = b.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
m = pd.read_parquet("data_long/metrics/BTCUSDT_metrics.parquet")
lsr = m.count_long_short_ratio.astype(float).resample("1D").last(); oi = m.sum_open_interest.astype(float).resample("1D").last()
d["lsr"] = lsr.shift(1).reindex(d.index); d["oi"] = oi.shift(1).reindex(d.index)        # yesterday's last print, known at today's open
d["atr"] = G.atr(d, 14).shift(1); d["cost"] = d.close * 0.0008; d["eligible"] = True
def crowd(x):
    hi = x.lsr.rolling(90).quantile(0.9).shift(1).values; lo = x.lsr.rolling(90).quantile(0.1).shift(1).values; v = x.lsr.values
    s = np.where(v >= hi, -1, np.where(v <= lo, 1, 0)); ix = np.where((s != 0) & np.isfinite(hi) & np.isfinite(x.atr.values))[0]
    ix = ix[ix >= 1] - 1          # the reading is yesterday's close -> act at the close of yesterday's bar = today's open
    return sigframe(x.index[ix], s[ix + 1], "close", np.nan, 3 * x.atr.values[ix + 1], np.nan, 3, dist=True)
def oi_break(x):
    C = x.close.values; hh = x.high.rolling(20).max().shift(1).values; ll = x.low.rolling(20).min().shift(1).values
    oi3 = (x.oi / x.oi.shift(3) - 1).shift(-1).values      # OI through today's close (yesterday's-last series shifted forward one)
    s = np.where((C > hh) & (oi3 >= 0.05), 1, np.where((C < ll) & (oi3 >= 0.05), -1, 0)); ix = np.where((s != 0) & np.isfinite(x.atr.values))[0]
    return sigframe(x.index[ix], s[ix], "close", np.nan, 3 * x.atr.values[ix], np.nan, 5, dist=True)
def oi_flush(x):
    oi1 = (x.oi / x.oi.shift(1) - 1).shift(-1).values; r = (x.close / x.close.shift(1) - 1).values
    ix = np.where((oi1 <= -0.08) & (r <= -0.04) & np.isfinite(x.atr.values))[0]
    return sigframe(x.index[ix], 1, "close", np.nan, 3 * x.atr.values[ix], np.nan, 3, dist=True)
for name, fn in (("T CROWD contrarian long/short ratio", crowd), ("U OI-confirmed breakout", oi_break), ("V OI flush buy", oi_flush)):
    r = G.judge2(f"BTC {name}", [("BTC", d, fn, {})], daily=True); print(G.line2(r), flush=True)
    t = pd.DataFrame(G.simulate(d, fn(d)))
    if len(t): t["y"] = pd.to_datetime(t.t).dt.year; print("    by year:", " ".join(f"{y}:{g.R.mean():+.2f}(n{len(g)})" for y, g in t.groupby("y")), flush=True)
