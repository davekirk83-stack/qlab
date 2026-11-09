"""DK 9 Nov (Atif Hussain / ICT model, used as context): 1) directional bias from the 4h chart; 2) on 15-min, wait for a liquidity
sweep AGAINST the bias (a swept 4h low in an uptrend / swept 4h high in a downtrend); 3) enter on the retracement into the fair value gap
left by the displacement back the other way; stop beyond the sweep; target 3R. "No sweep, no trade."
Bias: 4h close above (below) its 4h EMA50 and EMA50 rising (falling) over 6 bars.
Sweep: 15-min low trades below the prior 16-bar low (4h) by >= 0.1 ATR, then within 4 bars a bullish displacement leaves a 3-candle FVG
(low of bar k > high of bar k-2). Entry: limit at the top of that FVG (filled if price comes back to it within 12 bars).
Stop: sweep low - 0.1 ATR. Target: 3R. Max hold 48 bars (12h). Mirror for shorts. Costs: BTC 0.1% round trip; NQ 1 pt (cash hours).
Compared: same entries WITHOUT the bias filter, and with the bias reversed. BTC dev 2020-23 / hold 2024-26; NQ A 2020-21 / B 2025-26."""
import numpy as np, pandas as pd
OUT = open("runs/ict_trend_sweep_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def run(q, cost_fn, sess=None, bias_mode="with"):
    O, H, L, C = q.open.values, q.high.values, q.low.values, q.close.values; n = len(q)
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().shift(1).values
    ll = pd.Series(L).rolling(16).min().shift(1).values; hh = pd.Series(H).rolling(16).max().shift(1).values
    h4 = q.close.resample("4h").last().dropna(); e50 = h4.ewm(span=50, adjust=False).mean()
    up = ((h4 > e50) & (e50 > e50.shift(6))).shift(1); dn = ((h4 < e50) & (e50 < e50.shift(6))).shift(1)   # completed 4h bars only
    biasU = up.reindex(q.index, method="ffill").fillna(False).values.astype(bool); biasD = dn.reindex(q.index, method="ffill").fillna(False).values.astype(bool)
    ok = np.ones(n, bool) if sess is None else sess
    res = []; i = 20; busy = -1
    while i < n - 70:
        if i <= busy or not ok[i]: i += 1; continue
        side = 0
        if L[i] <= ll[i] - 0.1 * atr[i]: side = 1
        elif H[i] >= hh[i] + 0.1 * atr[i]: side = -1
        if side == 0: i += 1; continue
        b = biasU[i] if side == 1 else biasD[i]; br = biasD[i] if side == 1 else biasU[i]
        if bias_mode == "with" and not b: i += 1; continue
        if bias_mode == "against" and not br: i += 1; continue
        ext = L[i] if side == 1 else H[i]; done = False
        for k in range(i + 2, i + 6):
            ext = min(ext, L[k]) if side == 1 else max(ext, H[k])
            fvg = (L[k] > H[k - 2]) if side == 1 else (H[k] < L[k - 2])
            if not fvg: continue
            entry = L[k] if side == 1 else H[k]           # top of the bullish gap / bottom of the bearish gap
            stop = ext - side * 0.1 * atr[i]; risk = abs(entry - stop)
            if risk <= 0: break
            tgt = entry + side * 3 * risk
            fill = None
            for j in range(k + 1, min(k + 13, n)):
                if (side == 1 and L[j] <= entry) or (side == -1 and H[j] >= entry): fill = j; break
                if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt): break   # ran away without us
            if fill is None: break
            r = None
            for j in range(fill, min(fill + 48, n)):
                if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop): r = -risk; break
                if j > fill and ((side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt)): r = 3 * risk; break
            if r is None: r = side * (C[min(fill + 47, n - 1)] - entry)
            res.append((q.index[fill], (r - cost_fn(entry)) / risk)); busy = j; done = True
            break
        i += 1
    return pd.DataFrame(res, columns=["t", "R"])
def fmt(X, split):
    out = []
    for seg, msk in (("dev", X.t < split), ("hold", X.t >= split)):
        x = X[msk]; out.append(f"{seg} n{len(x):4} {x.R.mean():+.3f}R win {100*(x.R>0).mean():3.0f}% total {x.R.sum():+6.1f}R" if len(x) else f"{seg} none")
    return " || ".join(out)
def bars15(d): return d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
log("ICT TREND SWEEP (4h bias, 15m sweep against it, FVG pullback entry, 3R) — R per trade after costs")
qb = bars15(pd.read_parquet("data_long/btc_1m.parquet")); S = pd.Timestamp("2024-01-01", tz="UTC")
for mode in ("with", "none", "against"):
    log(f"  BTC   bias {mode:8} {fmt(run(qb, lambda e: 0.001 * e, bias_mode=mode), S)}")
for tag, f, st in (("NQ A 2020-21", "data_long/nq_5m_2020_21.csv", "2020-01-01"), ("NQ B 2025-26", "data_nq_cache/nq_5m.csv", "2025-10-15")):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated()].sort_index(); d = d[d.index >= st]
    q = bars15(d); lt = q.index.tz_convert("America/New_York"); mn = lt.hour * 60 + lt.minute
    for mode in ("with", "none"):
        log(f"  {tag} bias {mode:8} {fmt(run(q, lambda e: 1.0, sess=np.asarray((mn >= 570) & (mn < 930)), bias_mode=mode), pd.Timestamp('2099-01-01', tz='UTC'))}")
# iteration 2 (same day): the 15-min version is eaten by costs (tight stops); on 1-HOUR BTC bars the bias filter separates clearly.
m1 = pd.read_parquet("data_long/btc_1m.parquet"); q1 = m1.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
log("\nBTC 1-HOUR bars (same rules; 16-bar = 16h lows/highs; 48-bar = 2-day hold)")
for lab, cf in (("gross", lambda e: 0.0), ("taker 0.10%", lambda e: 0.001 * e), ("limit 0.04%", lambda e: 0.0004 * e)):
    for mode in ("with", "none"):
        log(f"  BTC 1h {lab:12} bias {mode:5} {fmt(run(q1, cf, bias_mode=mode), S)}")
