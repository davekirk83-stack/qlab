"""Doc 191 — BTC order-flow signals with TRUE aggressor delta (Binance spot 1m klines: taker-buy volume).
Dev 2020-2023, holdout 2024-Nov 2026. Forward returns in basis points (bp), long-side signals at lows and the mirror at highs
(shorts sign-flipped so + = the signal was right). Compared with the BASE RATE of the same location without the order-flow condition.
A  ABSORPTION: 15m bar makes a 4h low, delta strongly negative (z<=-1.5 vs prior 4 days of 15m deltas), but closes in the top half of its range.
B  CVD DIVERGENCE: 15m close at a 4h low that undercuts the low of 4-24h ago, while 24h-rolling CVD is HIGHER than at that earlier low.
C  CLIMAX WICK (big-order proxy): a 1m bar with volume >= 6x its 60-min average at a 4h low, lower wick >= 60% of range, delta negative.
D  STACKED PRESSURE (imbalance proxy): 3 consecutive 1m bars with |delta|/volume >= 0.5 the same way, total volume >= 3x average -> continuation?
"""
import numpy as np, pandas as pd
OUT = open("runs/btc_orderflow_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
m = pd.read_parquet("data_long/btc_1m.parquet")
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
c1 = m.close
def fwd(ts_idx, side, horizons=(15, 60, 240)):
    p0 = c1.reindex(ts_idx).values
    out = {}
    for h in horizons:
        ph = c1.reindex(ts_idx + pd.Timedelta(minutes=h)).values
        out[h] = side * (ph / p0 - 1) * 1e4
    return pd.DataFrame(out, index=ts_idx)
def report(name, ev, base):
    for lab, e in (("signal", ev), ("base", base)):
        cells = []
        for seg, msk in (("dev", e.index < SPLIT), ("hold", e.index >= SPLIT)):
            x = e[msk].dropna()
            cells.append(f"{seg} n{len(x):6} " + " ".join(f"{h}m {x[h].mean():+6.1f}bp/{100*(x[h]>0).mean():3.0f}%" for h in x.columns))
        log(f"  {name:28} {lab:6} " + " || ".join(cells))
# 15m bars
b = m.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "delta": "sum"}).dropna()
b["t_end"] = b.index + pd.Timedelta(minutes=15) - pd.Timedelta(minutes=1)   # decide at the bar's last minute close
lo16 = b.low.rolling(16).min(); hi16 = b.high.rolling(16).max()
atLow = b.low <= lo16; atHigh = b.high >= hi16
dz = (b.delta - b.delta.shift(1).rolling(384).mean()) / b.delta.shift(1).rolling(384).std()
pos = (b.close - b.low) / (b.high - b.low).replace(0, np.nan)
log("BTC ORDER FLOW — true taker delta, Binance spot 1m, " + str(m.index[0].date()) + " to " + str(m.index[-1].date()))
log("bp = basis points (100bp = 1%). Each cell: mean forward return / % of cases right. 'base' = same place (a 4h low or high) without the order-flow condition.")
# A
for side, at, cond, nm in ((1, atLow, (dz <= -1.5) & (pos >= 0.5), "A absorption at 4h LOW -> long"), (-1, atHigh, (dz >= 1.5) & (pos <= 0.5), "A absorption at 4h HIGH -> short")):
    ev = fwd(pd.DatetimeIndex(b.t_end[at & cond]), side); base = fwd(pd.DatetimeIndex(b.t_end[at]), side)
    report(nm, ev, base)
# B CVD divergence
cvd = b.delta.rolling(96).sum()
def div(side):
    idx = []
    L = b.low.values if side == 1 else -b.high.values; C = (cvd.values if side == 1 else -cvd.values)
    at = (atLow if side == 1 else atHigh).values
    for i in range(400, len(b)):
        if not at[i]: continue
        w0, w1 = i - 96, i - 16
        j = w0 + int(np.argmin(L[w0:w1]))
        if L[i] < L[j] and C[i] > C[j]: idx.append(b.t_end.iloc[i])
    return pd.DatetimeIndex(idx)
for side, nm in ((1, "B CVD bull divergence -> long"), (-1, "B CVD bear divergence -> short")):
    report(nm, fwd(div(side), side), fwd(pd.DatetimeIndex(b.t_end[(atLow if side == 1 else atHigh)]), side))
# C climax wick on 1m
va = m.vol.rolling(60).mean().shift(1); lo240 = m.low.rolling(240).min(); hi240 = m.high.rolling(240).max()
rng = (m.high - m.low).replace(0, np.nan)
lw = (np.minimum(m.open, m.close) - m.low) / rng; uw = (m.high - np.maximum(m.open, m.close)) / rng
big = m.vol >= 6 * va
cl = big & (m.low <= lo240) & (lw >= 0.6) & (m.delta < 0); ch = big & (m.high >= hi240) & (uw >= 0.6) & (m.delta > 0)
bl = big & (m.low <= lo240); bh = big & (m.high >= hi240)
def thin(ix, gap=60):
    keep, last = [], None
    for t in ix:
        if last is None or (t - last) > pd.Timedelta(minutes=gap): keep.append(t)
        last = t
    return pd.DatetimeIndex(keep)
report("C climax wick at LOW -> long", fwd(thin(m.index[cl]), 1), fwd(thin(m.index[bl]), 1))
report("C climax wick at HIGH -> short", fwd(thin(m.index[ch]), -1), fwd(thin(m.index[bh]), -1))
# D stacked pressure -> continuation
imb = m.delta / m.vol.replace(0, np.nan)
up3 = (imb >= 0.5) & (imb.shift(1) >= 0.5) & (imb.shift(2) >= 0.5) & (m.vol.rolling(3).sum() >= 9 * va)
dn3 = (imb <= -0.5) & (imb.shift(1) <= -0.5) & (imb.shift(2) <= -0.5) & (m.vol.rolling(3).sum() >= 9 * va)
mv3 = (m.close / m.close.shift(3) - 1)
q = mv3.abs().quantile(0.99)
report("D stacked BUYING -> long", fwd(thin(m.index[up3]), 1), fwd(thin(m.index[(mv3 > 0) & (m.vol.rolling(3).sum() >= 9 * va)]), 1))
report("D stacked SELLING -> short", fwd(thin(m.index[dn3]), -1), fwd(thin(m.index[(mv3 < 0) & (m.vol.rolling(3).sum() >= 9 * va)]), -1))
log("done")
