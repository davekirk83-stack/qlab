"""
THE PAPER BOOK v15 — "Trend-aligned sweep, 1 hour" (doc 192; DK 9 Nov 2026 "Yes" to paper-testing). SIMULATED LEDGER ONLY:
public Binance market data, no account, key or money (CAP-021).
REGISTERED RULES (any change restarts the clock)
  main      BTCUSDT 1h. Bias: last COMPLETED 4h close above its 4h EMA50 and the EMA50 higher than 6 bars earlier (mirror for shorts).
            Sweep against the bias: a 1h low below the prior 16h low by >= 0.1 ATR14 (uptrend) / high above the prior 16h high (downtrend).
            Within the next 4 bars a fair value gap back the other way (low[k] > high[k-2] for longs) -> limit order at the gap's edge,
            valid 12 bars; filled only if price trades THROUGH it. Stop = sweep extreme -/+ 0.1 ATR; target 3R; exit at 48 bars.
            One trade at a time. Costs 0.04% round trip (limit orders).
  shadow    ETHUSDT and SOLUSDT with the 4R / EMA30 variant (the only setting positive on all three in both test periods).
  sizing    £500 notional pool per market, 1% of the pool risked per trade.
  replay    from 10 Nov 2026 00:00 UTC every run, on the last 1,000 hourly bars (enough warm-up); no state file.
  review    with the other books in the week of 16 Nov, then monthly. PASS after 3 months: main positive with >= 20 trades and mean R
            within half of the backtest's (+0.09R hold period).
Writes runs/paper15/summary.json and runs/paper15/trades.csv.
"""
import os, json, urllib.request, numpy as np, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); OUT = f"{ROOT}/runs/paper15"
START = pd.Timestamp(os.environ.get("PB15_START", "2026-11-10"), tz="UTC"); EQ0, RISK, FEE = 500.0, 0.01, 0.0004
def klines(sym, n=1000):
    u = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&limit={n}"
    k = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    d = pd.DataFrame([[float(x[i]) for i in (1, 2, 3, 4)] for x in k], columns=["open", "high", "low", "close"], index=pd.to_datetime([x[0] for x in k], unit="ms", utc=True))
    return d.iloc[:-1]   # drop the bar still forming
def trades(q, R=3.0, ema=50, slope=6):
    O, H, L, C = q.open.values, q.high.values, q.low.values, q.close.values; n = len(q)
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().shift(1).values
    ll = pd.Series(L).rolling(16).min().shift(1).values; hh = pd.Series(H).rolling(16).max().shift(1).values
    h4 = q.close.resample("4h").last().dropna(); e = h4.ewm(span=ema, adjust=False).mean()
    up = ((h4 > e) & (e > e.shift(slope))).shift(1); dn = ((h4 < e) & (e < e.shift(slope))).shift(1)
    bU = up.reindex(q.index, method="ffill").fillna(False).values.astype(bool); bD = dn.reindex(q.index, method="ffill").fillna(False).values.astype(bool)
    out = []; i = 20; busy = -1
    while i < n - 1:
        if i <= busy or q.index[i] < START: i += 1; continue
        side = 1 if L[i] <= ll[i] - 0.1 * atr[i] else -1 if H[i] >= hh[i] + 0.1 * atr[i] else 0
        if side == 0 or not (bU[i] if side == 1 else bD[i]): i += 1; continue
        ext = L[i] if side == 1 else H[i]; placed = False
        for k in range(i + 2, min(i + 6, n)):
            ext = min(ext, L[k]) if side == 1 else max(ext, H[k])
            if not ((L[k] > H[k - 2]) if side == 1 else (H[k] < L[k - 2])): continue
            entry = L[k] if side == 1 else H[k]; stop = ext - side * 0.1 * atr[i]; risk = abs(entry - stop)
            if risk <= 0: break
            tgt = entry + side * R * risk; fill = None; placed = True
            for j in range(k + 1, min(k + 13, n)):
                if (side == 1 and L[j] < entry) or (side == -1 and H[j] > entry): fill = j; break
                if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt): break
            if fill is None:
                if k + 13 > n: out.append(dict(signal=str(q.index[k]), side=side, entry=entry, stop=stop, target=tgt, status="order working"))
                break
            r = None; how = "open"; j = fill
            for j in range(fill, min(fill + 48, n)):
                if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop): r, how = -risk, "stop"; break
                if j > fill and ((side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt)): r, how = R * risk, "target"; break
            if r is None and fill + 48 <= n: r, how = side * (C[fill + 47] - entry), "time"; j = fill + 47
            rec = dict(signal=str(q.index[k]), filled=str(q.index[fill]), side=side, entry=round(entry, 4), stop=round(stop, 4), target=round(tgt, 4), status=how)
            if r is not None: rec.update(closed=str(q.index[j]), R=round((r - FEE * entry) / risk, 3))
            out.append(rec); busy = j if r is not None else n
            break
        i += 1
    return out
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); summ = {"start": str(START.date()), "asof": str(pd.Timestamp.now("UTC").floor("min")), "books": {}}; rows = []
    for sym, kw, role in (("BTCUSDT", dict(R=3.0, ema=50, slope=6), "main"), ("ETHUSDT", dict(R=4.0, ema=30, slope=6), "shadow"), ("SOLUSDT", dict(R=4.0, ema=30, slope=6), "shadow")):
        T = trades(klines(sym), **kw); done = [t for t in T if "R" in t]; eq = EQ0
        for t in done: eq += EQ0 * RISK * t["R"]   # fixed 1% of the starting pool per trade
        summ["books"][sym] = dict(role=role, rules=kw, closed=len(done), open=[t for t in T if "R" not in t], total_R=round(sum(t["R"] for t in done), 2),
                                  win_rate=round(100 * np.mean([t["R"] > 0 for t in done]), 1) if done else None, pool=round(eq, 2))
        rows += [dict(market=sym, role=role, **t) for t in T]
    json.dump(summ, open(f"{OUT}/summary.json", "w"), indent=1); pd.DataFrame(rows).to_csv(f"{OUT}/trades.csv", index=False)
    print(json.dumps(summ["books"], indent=1))
