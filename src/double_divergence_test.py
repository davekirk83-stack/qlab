"""DK 9 Nov (Cheds lesson 38): use OBV (unbounded) for reversal divergence, ideally DOUBLE divergence — two higher highs in price with
two lower highs in OBV (bearish), or two lower lows with two higher lows (bullish). Longer trends -> more significant.
BTC 1h (Binance spot), dev 2020-23 / hold 2024-26. Swing points = pivots with 3 bars each side (confirmed 3 bars later, entry then).
Indicators: OBV (close-to-close sign x volume) and true CVD (taker delta). SINGLE = last two swing lows/highs diverge; DOUBLE = last three.
Forward return in the reversal direction over 12h and 48h (bp) vs the base rate at any confirmed swing low/high of the same kind."""
import numpy as np, pandas as pd
OUT = open("runs/double_divergence_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
m = pd.read_parquet("data_long/btc_1m.parquet")
h = m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "delta": "sum"}).dropna()
h["obv"] = (np.sign(h.close.diff()).fillna(0) * h.vol).cumsum(); h["cvd"] = h.delta.cumsum()
H, L, C = h.high.values, h.low.values, h.close.values; N = len(h); K = 3
ph = [i for i in range(K, N - K) if H[i] == H[i - K:i + K + 1].max()]
pl = [i for i in range(K, N - K) if L[i] == L[i - K:i + K + 1].min()]
SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
def fwd(i, side, n): return side * (C[i + n] / C[i] - 1) * 1e4 if i + n < N else np.nan
def run(ind, piv, side, maxgap=72):
    X = h[ind].values; P = L if side == 1 else H
    single, double, base = [], [], []
    for k in range(2, len(piv)):
        a, b_, c = piv[k - 2], piv[k - 1], piv[k]
        e = c + K   # known K bars after the pivot
        if e + 48 >= N: break
        base.append((e,))
        if c - b_ > maxgap: continue
        if side == 1: s = P[c] < P[b_] and X[c] > X[b_]; dd = s and P[b_] < P[a] and X[b_] > X[a] and b_ - a <= maxgap
        else: s = P[c] > P[b_] and X[c] < X[b_]; dd = s and P[b_] > P[a] and X[b_] < X[a] and b_ - a <= maxgap
        if s: single.append((e,))
        if dd: double.append((e,))
    def cell(rows):
        out = []
        for seg, f in (("dev", lambda t: t < SPLIT), ("hold", lambda t: t >= SPLIT)):
            ix = [r[0] for r in rows if f(h.index[r[0]])]
            a12 = np.array([fwd(i, side, 12) for i in ix]); a48 = np.array([fwd(i, side, 48) for i in ix])
            out.append(f"{seg} n{len(ix):4} 12h {np.nanmean(a12):+6.1f} 48h {np.nanmean(a48):+6.1f}bp ({100*np.nanmean(a48>0):.0f}%)" if len(ix) else f"{seg} none")
        return " || ".join(out)
    return cell(base), cell(single), cell(double)
log("DOUBLE DIVERGENCE (Cheds lesson 38) — BTC 1h, forward return in the reversal direction")
for ind in ("obv", "cvd"):
    for side, piv, nm in ((1, pl, "bullish (lower lows)"), (-1, ph, "bearish (higher highs)")):
        b0, s1, d2 = run(ind, piv, side)
        log(f"\n{ind.upper()} {nm}")
        log(f"  base: any swing      {b0}"); log(f"  single divergence    {s1}"); log(f"  DOUBLE divergence    {d2}")
