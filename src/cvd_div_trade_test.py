"""Doc 158 — building the bullish CVD divergence (doc 157) into a trade (rule 188). DK: "Sure give it a try". Pre-registered 28 Oct 2026.
Signal: a lower swing low (pivot 5 bars either side on 1h; 3 on 4h) within 72 hours of the previous swing low, while COMBINED CVD (Binance
spot + perp taker delta) is HIGHER than at the previous low. Entry at the confirmation close. Stop = swing low - 0.05%.
Exits (pre-registered): X24 hold 24h | X72 hold 72h | T2R target 2R, cap 72h | TSH target the swing high between the two lows, cap 72h |
TRL trail: stop moves to max(stop, highest close - 2 x ATR14), cap 7 days.
Markets BTC, ETH; timeframes 1h, 4h. Also both SHORT-side mirrors (bearish divergence -> short) with the same exits, for DK's question on BTC shorts.
Control: the same exits on lower lows WITHOUT divergence (higher highs without divergence for the short side). Costs 0.10%/side (Binance-like)
and 0.45%/side (Kraken taker, doc 147). Dev 2020-2024, holdout 2025-2026."""
import numpy as np, pandas as pd, itertools
def load(sym, tf):
    out = {}
    for k in ("spot", "perp"):
        d = pd.read_csv(f"data_bnb/{sym}_{k}_15m.csv", parse_dates=["t"]).set_index("t"); d["delta"] = 2 * d.takerbuy - d.vol
        out[k] = d.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last", "delta": "sum"}).dropna()
    d = out["spot"][["open", "high", "low", "close"]].copy()
    d["cvd"] = out["spot"].delta.cumsum() + out["perp"].delta.reindex(d.index).fillna(0).cumsum()
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean(); return d
def run(d, K, win, long_side, cost):
    H, L, C, A, V, idx = d.high.values, d.low.values, d.close.values, d.atr.values, d.cvd.values, d.index; n = len(C)
    if long_side: piv = [k for k in range(K, n - K) if L[k] == L[k - K:k + K + 1].min()]
    else: piv = [k for k in range(K, n - K) if H[k] == H[k - K:k + K + 1].max()]
    res = {e: {True: [], False: []} for e in ("X24", "X72", "T2R", "TSH", "TRL")}; prev = None
    bars = lambda hrs: max(1, int(round(hrs / (24 / win))))  # win = bars per 24h
    for k in piv:
        if prev is not None and (k - prev) <= bars(72):
            if (long_side and L[k] < L[prev]) or (not long_side and H[k] > H[prev]):
                div = V[k] > V[prev] if long_side else V[k] < V[prev]
                c = k + K
                if c + bars(168) < n:
                    s = 1 if long_side else -1; e = C[c]
                    stop0 = L[k] * 0.9995 if long_side else H[k] * 1.0005; risk = abs(e - stop0) / e
                    mid = H[prev:k + 1].max() if long_side else L[prev:k + 1].min()
                    if risk > 0:
                        for ex in res:
                            stop = stop0; cap = {"X24": bars(24), "X72": bars(72), "T2R": bars(72), "TSH": bars(72), "TRL": bars(168)}[ex]
                            tgt = e * (1 + 2 * risk * s) if ex == "T2R" else (mid if ex == "TSH" else None)
                            if ex == "TSH" and (mid - e) * s <= 0: tgt = None
                            px = C[c + cap]; best = e
                            for j in range(c + 1, c + cap + 1):
                                if (s == 1 and L[j] <= stop) or (s == -1 and H[j] >= stop): px = stop; break
                                if tgt is not None and ((s == 1 and H[j] >= tgt) or (s == -1 and L[j] <= tgt)): px = tgt; break
                                if ex == "TRL":
                                    best = max(best, C[j]) if s == 1 else min(best, C[j])
                                    stop = max(stop, best - 2 * A[j]) if s == 1 else min(stop, best + 2 * A[j])
                            r = (px / e - 1) * s - 2 * cost
                            res[ex][div].append((idx[k], r / risk, r))
        prev = k
    return res
lines = []
for sym, (tf, K, win) in itertools.product(("BTCUSDT", "ETHUSDT"), (("1h", 5, 24), ("4h", 3, 6))):
    d = load(sym, tf)
    for long_side in (True, False):
        for cost in (0.001, 0.0045):
            res = run(d, K, win, long_side, cost)
            for ex, rr in res.items():
                cell = []
                for seg, f in (("dev", lambda t: t.year <= 2024), ("hold", lambda t: t.year >= 2025)):
                    a = np.array([x[1] for x in rr[True] if f(x[0])]); b = np.array([x[1] for x in rr[False] if f(x[0])])
                    if len(a) < 3: cell.append(f"{seg} n{len(a)}"); continue
                    t = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
                    cell.append(f"{seg} n{len(a):3} {a.mean():+.2f}R vs {b.mean():+.2f}R (t {t:+.1f})")
                lines.append(f"{sym[:3]} {tf} {'LONG bullish-div' if long_side else 'SHORT bearish-div'} cost {100*cost:.2f}% {ex}: " + " | ".join(cell))
            print("\n".join(lines[-5:]), flush=True)
open("runs/cvd_div_trade_test.txt", "w").write("\n".join(lines) + "\n")
