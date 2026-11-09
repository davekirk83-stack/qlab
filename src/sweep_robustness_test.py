"""Doc 192 follow-up (DK 9 Nov "Yes please"): robustness of the 1-hour trend-aligned sweep engine before paper testing.
Same rules as src/ict_trend_sweep_test.py run(), parameterised: target R, 4h EMA length, slope lookback, and a STRICT fill
(price must trade THROUGH the limit, not just touch it). Markets: BTC (where it was found), ETH and SOL (never seen).
Costs: limit-order fees 0.04% round trip (maker in, maker/taker out averaged) and a harsher 0.10%. Dev 2020-23 / hold 2024-26."""
import numpy as np, pandas as pd, itertools
OUT = open("runs/sweep_robustness_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def run(q, cost, R=3.0, ema=50, slope=6, strict=False, bias=True):
    O, H, L, C = q.open.values, q.high.values, q.low.values, q.close.values; n = len(q)
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().shift(1).values
    ll = pd.Series(L).rolling(16).min().shift(1).values; hh = pd.Series(H).rolling(16).max().shift(1).values
    h4 = q.close.resample("4h").last().dropna(); e = h4.ewm(span=ema, adjust=False).mean()
    up = ((h4 > e) & (e > e.shift(slope))).shift(1); dn = ((h4 < e) & (e < e.shift(slope))).shift(1)
    bU = up.reindex(q.index, method="ffill").fillna(False).values.astype(bool); bD = dn.reindex(q.index, method="ffill").fillna(False).values.astype(bool)
    res = []; setups = 0; i = 20; busy = -1
    while i < n - 70:
        if i <= busy: i += 1; continue
        side = 1 if L[i] <= ll[i] - 0.1 * atr[i] else -1 if H[i] >= hh[i] + 0.1 * atr[i] else 0
        if side == 0 or (bias and not (bU[i] if side == 1 else bD[i])): i += 1; continue
        ext = L[i] if side == 1 else H[i]
        for k in range(i + 2, i + 6):
            ext = min(ext, L[k]) if side == 1 else max(ext, H[k])
            if not ((L[k] > H[k - 2]) if side == 1 else (H[k] < L[k - 2])): continue
            entry = L[k] if side == 1 else H[k]; stop = ext - side * 0.1 * atr[i]; risk = abs(entry - stop)
            if risk <= 0: break
            setups += 1; tgt = entry + side * R * risk; fill = None
            for j in range(k + 1, min(k + 13, n)):
                touched = (L[j] < entry) if strict else (L[j] <= entry)
                if side == -1: touched = (H[j] > entry) if strict else (H[j] >= entry)
                if touched: fill = j; break
                if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt): break
            if fill is None: break
            r = None
            for j in range(fill, min(fill + 48, n)):
                if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop): r = -risk; break
                if j > fill and ((side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt)): r = R * risk; break
            if r is None: r = side * (C[min(fill + 47, n - 1)] - entry)
            res.append((q.index[fill], (r - cost * entry) / risk, side)); busy = j
            break
        i += 1
    X = pd.DataFrame(res, columns=["t", "R", "side"]); X.attrs["setups"] = setups; return X
S = pd.Timestamp("2024-01-01", tz="UTC")
def fmt(X):
    o = []
    for seg, msk in (("dev", X.t < S), ("hold", X.t >= S)):
        x = X[msk]; o.append(f"{seg} n{len(x):3} {x.R.mean():+.3f}R ({100*(x.R>0).mean():.0f}%)" if len(x) else f"{seg} none")
    return " | ".join(o)
mk = {}
m = pd.read_parquet("data_long/btc_1m.parquet"); mk["BTC"] = m.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
for s in ("eth", "sol"): mk[s.upper()] = pd.read_parquet(f"data_long/{s}_1h.parquet")[["open", "high", "low", "close"]]
log("1) BASE RULES (3R, EMA50, slope 6) — touch fill vs STRICT fill (trade-through), fees 0.04% / 0.10%")
for name, q in mk.items():
    for strict in (False, True):
        for c in (0.0004, 0.001):
            X = run(q, c, strict=strict); fr = len(X) / max(X.attrs["setups"], 1)
            log(f"  {name} {'strict' if strict else 'touch '} fee {c*100:.2f}%  fills {100*fr:.0f}%  {fmt(X)}")
    Xn = run(q, 0.0004, bias=False); log(f"  {name} NO BIAS filter fee 0.04%          {fmt(Xn)}")
log("\n2) PARAMETER NEIGHBOURHOOD (strict fill, fee 0.04%) — mean R dev | hold")
grid = list(itertools.product((2.0, 3.0, 4.0), (30, 50, 100), (3, 6, 12)))
summ = {name: [] for name in mk}
for R, ema, sl in grid:
    cells = []
    for name, q in mk.items():
        X = run(q, 0.0004, R=R, ema=ema, slope=sl, strict=True)
        dv, ho = X[X.t < S].R.mean(), X[X.t >= S].R.mean(); summ[name].append((dv, ho)); cells.append(f"{name} {dv:+.2f}|{ho:+.2f}")
    log(f"  R{R:.0f} EMA{ema:3} slope{sl:2}: " + "   ".join(cells))
log("\n   share of the 27 settings positive in BOTH periods:")
for name, v in summ.items(): log(f"   {name}: {sum(1 for a, b in v if a > 0 and b > 0)}/27")
log("\n3) LONGS vs SHORTS (base rules, strict, 0.04%)")
for name, q in mk.items():
    X = run(q, 0.0004, strict=True)
    for sd, lab in ((1, "longs"), (-1, "shorts")): log(f"  {name} {lab:6} {fmt(X[X.side == sd])}")
