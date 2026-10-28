"""Doc 157 — price/CVD divergence at swing highs and lows, as CoinGlass draws it (DK 28 Oct: "Yea"). Pre-registered before any result.
Data: Binance BTCUSDT spot and USD-M perp 15m klines with taker-buy volume (data.binance.vision), 2020-2026, resampled to 1 hour.
CVD = cumulative (taker buy - taker sell) volume; three versions: SPOT, PERP, COMBINED (spot + perp).
Swings: a 1h bar whose high (low) is the highest (lowest) of the 5 bars either side; known 5 bars later (confirmation).
BEARISH divergence: a confirmed swing high ABOVE the previous swing high (within 72 bars) while CVD at the new high is BELOW CVD at the
previous high. BULLISH: a lower swing low while CVD is ABOVE its value at the previous low.
Comparison (the control): the same swing type WITHOUT divergence (higher high with higher CVD; lower low with lower CVD) — does the
divergence add anything beyond the swing itself? Measured from the confirmation close: return over 4h, 12h, 24h; and a trade against the
swing (short bearish / long bullish), stop beyond the swing extreme, exit at 24h, 0.10% per side, in R.
Dev 2020-2024, holdout 2025-2026. Trials: 3 CVDs x 2 sides = 6."""
import numpy as np, pandas as pd
def load(k):
    d = pd.read_csv(f"data_bnb/BTCUSDT_{k}_15m.csv", parse_dates=["t"]).set_index("t")
    d["delta"] = 2 * d.takerbuy - d.vol
    return d.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "delta": "sum"}).dropna()
sp, pp = load("spot"), load("perp")
d = sp[["open", "high", "low", "close"]].copy()
d["SPOT"] = sp.delta.cumsum(); d["PERP"] = pp.delta.reindex(d.index).fillna(0).cumsum(); d["COMBINED"] = d.SPOT + d.PERP
H, L, C = d.high.values, d.low.values, d.close.values; n = len(C); idx = d.index; K = 5
sh = [k for k in range(K, n - K) if H[k] == H[k - K:k + K + 1].max()]
sl = [k for k in range(K, n - K) if L[k] == L[k - K:k + K + 1].min()]
def events(piv, hi, cvd):
    out = []; prev = None
    for k in piv:
        if prev is not None and k - prev <= 72:
            better = H[k] > H[prev] if hi else L[k] < L[prev]
            if better:
                div = cvd[k] < cvd[prev] if hi else cvd[k] > cvd[prev]
                out.append((k, div))
        prev = k
    return out
def measure(k, hi):
    c = k + K
    if c + 24 >= n: return None
    e = C[c]; s = -1 if hi else 1                      # trade AGAINST the swing
    fw = {h: (C[c + h] / e - 1) * s for h in (4, 12, 24)}
    stop = H[k] * 1.0005 if hi else L[k] * 0.9995; risk = abs(stop - e) / e
    if risk <= 0: return None
    px = C[c + 24]
    for j in range(c + 1, c + 25):
        if (hi and H[j] >= stop) or (not hi and L[j] <= stop): px = stop; break
    r = (px / e - 1) * s - 0.002
    return fw, r / max(risk, 0.001)
lines = []
for cv in ("SPOT", "PERP", "COMBINED"):
    for hi, nm in ((True, "BEARISH (higher high, weaker CVD) -> short"), (False, "BULLISH (lower low, stronger CVD) -> long")):
        ev = events(sh if hi else sl, hi, d[cv].values)
        for seg, f in (("DEV ", lambda t: t.year <= 2024), ("HOLD", lambda t: t.year >= 2025)):
            rows = {True: [], False: []}
            for k, div in ev:
                if not f(idx[k]): continue
                m = measure(k, hi)
                if m: rows[div].append(m)
            def s(rs):
                if not rs: return "n0"
                f24 = np.array([x[0][24] for x in rs]); f4 = np.array([x[0][4] for x in rs]); R = np.array([x[1] for x in rs])
                return f"n{len(rs):4} 4h {100*np.mean(f4):+.2f}% 24h {100*np.mean(f24):+.2f}% (right way {100*(f24>0).mean():.0f}%) trade {R.mean():+.2f}R"
            a = np.array([x[0][24] for x in rows[True]]); b = np.array([x[0][24] for x in rows[False]])
            t = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b)) if len(a) > 2 and len(b) > 2 else np.nan
            lines.append(f"{cv:8} {nm:42} {seg} DIVERGENCE {s(rows[True])} | NO divergence {s(rows[False])} | 24h difference t={t:+.2f}")
            print(lines[-1], flush=True)
open("runs/cvd_divergence_test.txt", "w").write("\n".join(lines) + "\n")
