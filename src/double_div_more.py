"""Doc 192 follow-up: bullish OBV DOUBLE divergence on more markets (ETH, SOL 1h 2020-26; US Tech 100 / US 500 / FTSE 1h from 5-min data).
Same pivot rules as src/double_divergence_test.py. Also a TRADE version: enter at the confirmation close, stop below the last swing low
(-0.25 ATR), exit after 48h or at 3R. Forward 48h return in bp, and R per trade after costs (crypto 0.1% rt; indices IG spread)."""
import numpy as np, pandas as pd
OUT = open("runs/double_div_more.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def study(h, name, cost_pct=0.001, cost_pts=None, split=pd.Timestamp("2024-01-01", tz="UTC")):
    h = h.dropna().copy(); h["obv"] = (np.sign(h.close.diff()).fillna(0) * h.vol).cumsum()
    H, L, C, X = h.high.values, h.low.values, h.close.values, h.obv.values; N = len(h); K = 3
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().values
    pl = [i for i in range(K, N - K) if L[i] == L[i - K:i + K + 1].min()]
    ev, base = [], []
    for k in range(2, len(pl)):
        a, b, c = pl[k - 2], pl[k - 1], pl[k]; e = c + K
        if e + 48 >= N: break
        base.append(e)
        if c - b <= 72 and b - a <= 72 and L[c] < L[b] < L[a] and X[c] > X[b] > X[a]: ev.append((e, c))
    rows = []
    for e, c in ev:
        stop = L[c] - 0.25 * atr[e]; risk = C[e] - stop; tgt = C[e] + 3 * risk; r = None
        for j in range(e + 1, min(e + 49, N)):
            if L[j] <= stop: r = -risk; break
            if H[j] >= tgt: r = 3 * risk; break
        if r is None: r = C[min(e + 48, N - 1)] - C[e]
        cost = cost_pts if cost_pts is not None else cost_pct * C[e]
        rows.append((h.index[e], (C[e + 48] / C[e] - 1) * 1e4, (r - cost) / risk))
    E = pd.DataFrame(rows, columns=["t", "f48", "R"]); B = pd.Series([(C[i + 48] / C[i] - 1) * 1e4 for i in base], index=h.index[base])
    cells = []
    for seg, f in (("dev", lambda t: t < split), ("hold", lambda t: t >= split)):
        x = E[f(E.t)]; bb = B[f(B.index)]
        cells.append(f"{seg} n{len(x):2} 48h {x.f48.mean():+6.0f}bp vs base {bb.mean():+4.0f} | trade {x.R.mean():+.2f}R ({100*(x.R>0).mean():.0f}%)" if len(x) else f"{seg} none")
    log(f"  {name:12} " + " || ".join(cells))
    return E
log("BULLISH OBV DOUBLE DIVERGENCE across markets (1h)")
allE = []
m = pd.read_parquet("data_long/btc_1m.parquet"); allE.append(study(m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}), "BTC"))
for s in ("eth", "sol"): allE.append(study(pd.read_parquet(f"data_long/{s}_1h.parquet"), s.upper()))
for name, f, cost in (("US Tech 100", "data_nq_cache/nq_5m.csv", 1.0), ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", 0.4), ("FTSE 100", "data_ig_cache/GBRIDXGBP_5m.csv", 1.0)):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated()].sort_index()
    h = d.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"})
    allE.append(study(h, name, cost_pts=cost, split=pd.Timestamp("2026-05-01", tz="UTC")))
A = pd.concat(allE); log(f"\n  ALL MARKETS: n{len(A)} trades, mean {A.R.mean():+.2f}R, win {100*(A.R>0).mean():.0f}%, total {A.R.sum():+.1f}R; 48h mean {A.f48.mean():+.0f}bp")
# iteration: the 3R/tight-stop version gets shaken out; the 48h drift is where the edge is. HOLD version: buy at confirmation, hold 48h,
# catastrophe stop -8%, costs 0.1% round trip. Crypto only (the indices had too few events and were negative).
log("\nHOLD-48h version (crypto): return per trade after 0.1% costs, catastrophe stop -8%")
def hold(h, name, split=pd.Timestamp("2024-01-01", tz="UTC")):
    h = h.dropna().copy(); h["obv"] = (np.sign(h.close.diff()).fillna(0) * h.vol).cumsum()
    H, L, C, X = h.high.values, h.low.values, h.close.values, h.obv.values; N = len(h); K = 3
    pl = [i for i in range(K, N - K) if L[i] == L[i - K:i + K + 1].min()]; out = []
    for k in range(2, len(pl)):
        a, b, c = pl[k - 2], pl[k - 1], pl[k]; e = c + K
        if e + 48 >= N: break
        if c - b <= 72 and b - a <= 72 and L[c] < L[b] < L[a] and X[c] > X[b] > X[a]:
            lo = L[e + 1:e + 49].min(); r = -0.08 if lo <= C[e] * 0.92 else C[e + 48] / C[e] - 1
            out.append((h.index[e], r - 0.001))
    E = pd.DataFrame(out, columns=["t", "r"]); cells = []
    for seg, f in (("dev", lambda t: t < split), ("hold", lambda t: t >= split)):
        x = E[f(E.t)]; cells.append(f"{seg} n{len(x):2} mean {100*x.r.mean():+.2f}% win {100*(x.r>0).mean():.0f}% worst {100*x.r.min():+.1f}%")
    log(f"  {name:4} " + " || ".join(cells)); return E
HE = [hold(m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}), "BTC")]
for s in ("eth", "sol"): HE.append(hold(pd.read_parquet(f"data_long/{s}_1h.parquet"), s.upper()))
A = pd.concat(HE).sort_values("t"); yrs = (A.t.max() - A.t.min()).days / 365
log(f"  ALL CRYPTO: n{len(A)} ({len(A)/yrs:.0f} a year), mean {100*A.r.mean():+.2f}% per trade, win {100*(A.r>0).mean():.0f}%, sum {100*A.r.sum():+.0f}% (each trade on its own stake)")
log("  by year: " + " ".join(f"{y}:{100*g.r.sum():+.0f}%(n{len(g)})" for y, g in A.groupby(A.t.dt.year)))
