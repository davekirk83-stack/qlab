"""Doc 199 — Stoic's "liquidity sweeps" thread (DK 9 Nov 22:55), turned into fixed, testable rules on BTC 15-min (Binance spot bars,
Binance futures open interest 5-min), Dec 2021 - Nov 2026, through GATE v2. His points: OLD levels don't hold resting positions (his own chart:
13 daily sweeps of 30+ day levels, 6 reversed = a coin flip); RECENT range extremes do, especially after chop; a real sweep is a liquidation
(stops fire -> open interest DROPS), leaving a vacuum -> mechanical reversion; if the aggression doesn't follow through, price probes back.
Rules (fixed in advance):
  range   = high/low of the prior 48 bars (12h); sweep = bar trades beyond it and CLOSES back inside;
  fade at that close; stop 0.1 ATR beyond the sweep extreme; target the range midpoint; max 16 bars (4h); costs 0.08% round trip.
  +OI     open interest fell >= 0.3% over the sweep bar and the one before (positions closed, not opened);
  +NOFT   no follow-through: the next bar does not extend the sweep extreme -> enter at THAT bar's close instead;
  +CHOP   the 12h range is no wider than 6 ATR (price has been 'hanging out')."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G
from gate_books import sigframe
b = pd.read_parquet("data_long/btc_1m.parquet"); b = b[b.index >= "2021-11-25"]
q = b.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
oi = pd.read_parquet("data_long/metrics/BTCUSDT_metrics.parquet").sum_open_interest.astype(float)
q["oi"] = oi.resample("15min").last().reindex(q.index).ffill()           # OI at the bar's start label; shift to bar end below
q["oi_end"] = oi.resample("15min").last().shift(-1).reindex(q.index)     # last OI print inside the bar (known at its close)
q["oi_end"] = oi.reindex(q.index + pd.Timedelta(minutes=10), method="ffill").values
q["atr"] = G.atr(q).shift(1); q["cost"] = q.close * 0.0008; q["eligible"] = True
def sweeps(x, use_oi=False, noft=False, chop=False):
    H, L, C, a = x.high.values, x.low.values, x.close.values, x.atr.values
    HH = x.high.rolling(48).max().shift(1).values; LL = x.low.rolling(48).min().shift(1).values
    oie = x.oi_end.values; doi = oie / np.roll(oie, 2) - 1
    idx, side, stop, tgt = [], [], [], []
    for i in range(50, len(C) - 1):
        if not (np.isfinite(a[i]) and a[i] > 0 and np.isfinite(HH[i])): continue
        s = -1 if (H[i] > HH[i] and C[i] < HH[i]) else 1 if (L[i] < LL[i] and C[i] > LL[i]) else 0
        if s == 0: continue
        if chop and (HH[i] - LL[i]) > 6 * a[i]: continue
        if use_oi and not (np.isfinite(doi[i]) and doi[i] <= -0.003): continue
        j = i
        if noft:
            j = i + 1
            if (s == -1 and (H[j] > H[i] or C[j] >= HH[i])) or (s == 1 and (L[j] < L[i] or C[j] <= LL[i])): continue
        ext = H[i] if s == -1 else L[i]; st = ext - s * 0.1 * a[i]; mid = (HH[i] + LL[i]) / 2
        if s * (mid - C[j]) <= 0 or s * (C[j] - st) <= 0: continue
        idx.append(x.index[j]); side.append(s); stop.append(st); tgt.append(mid)
    f = sigframe(pd.DatetimeIndex(idx), side, "close", np.nan, stop, tgt, 16)
    return f[~f.index.duplicated()]
for name, kw in (("SWEEP recent 12h range (base)", {}), ("SWEEP + OI drop", {"use_oi": True}), ("SWEEP + OI drop + no follow-through", {"use_oi": True, "noft": True}),
                 ("SWEEP + chop", {"chop": True}), ("SWEEP + OI drop + chop", {"use_oi": True, "chop": True}), ("SWEEP + no follow-through", {"noft": True})):
    r = G.judge2(f"BTC {name}", [("BTC", q, lambda x, kw=kw: sweeps(x, **kw), {})]); print(G.line2(r), flush=True)
    t = pd.DataFrame(G.simulate(q, sweeps(q, **kw))); t["y"] = pd.to_datetime(t.t).dt.year
    print("    by year:", " ".join(f"{y}:{g.R.mean():+.3f}(n{len(g)})" for y, g in t.groupby("y")), f"| win {100*(t.R>0).mean():.0f}% pts-ATR", flush=True)

# 1-hour version (costs are a smaller share of a 1h ATR): range = prior 24 bars (1 day), max 8 bars
h = b.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
h["oi_end"] = oi.reindex(h.index + pd.Timedelta(minutes=55), method="ffill").values
h["atr"] = G.atr(h).shift(1); h["cost"] = h.close * 0.0008; h["eligible"] = True
def sweeps_h(x, use_oi=False):
    f = sweeps(x.assign(), use_oi=use_oi)
    return f
import types
for name, kw in (("1h SWEEP 24h range", {}), ("1h SWEEP + OI drop", {"use_oi": True})):
    def fn(x, kw=kw):
        H, L, C, a = x.high.values, x.low.values, x.close.values, x.atr.values
        HH = x.high.rolling(24).max().shift(1).values; LL = x.low.rolling(24).min().shift(1).values
        oie = x.oi_end.values; doi = oie / np.roll(oie, 1) - 1
        idx, side, stop, tgt = [], [], [], []
        for i in range(26, len(C) - 1):
            if not (np.isfinite(a[i]) and a[i] > 0 and np.isfinite(HH[i])): continue
            s = -1 if (H[i] > HH[i] and C[i] < HH[i]) else 1 if (L[i] < LL[i] and C[i] > LL[i]) else 0
            if s == 0 or (kw.get("use_oi") and not (np.isfinite(doi[i]) and doi[i] <= -0.005)): continue
            st = (H[i] if s == -1 else L[i]) - s * 0.1 * a[i]; mid = (HH[i] + LL[i]) / 2
            if s * (mid - C[i]) <= 0 or s * (C[i] - st) <= 0: continue
            idx.append(x.index[i]); side.append(s); stop.append(st); tgt.append(mid)
        return sigframe(pd.DatetimeIndex(idx), side, "close", np.nan, stop, tgt, 8)
    r = G.judge2(f"BTC {name}", [("BTC", h, fn, {})]); print(G.line2(r), flush=True)
    t = pd.DataFrame(G.simulate(h, fn(h))); t["y"] = pd.to_datetime(t.t).dt.year
    print("    by year:", " ".join(f"{y}:{g.R.mean():+.3f}(n{len(g)})" for y, g in t.groupby("y")), flush=True)
