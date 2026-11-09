"""
THE PAPER BOOK v16 — "OBV double divergence, crypto rare book" (doc 192; Cheds lesson 38; DK 9 Nov "Yes", and 16:51 "nothing against
incorporating a rare book ... provided it makes profit on those rare days"). SIMULATED LEDGER ONLY: Binance public data (CAP-021).
REGISTERED RULES
  markets   BTCUSDT, ETHUSDT, SOLUSDT, 1h bars. Swing low = the lowest low of 7 bars centred on it (3 each side), known 3 bars later.
  signal    BULLISH DOUBLE DIVERGENCE: three consecutive swing lows, each lower than the last, while OBV (close-to-close sign x volume,
            cumulative) at those lows is each HIGHER than the last; gaps between the lows <= 72 bars.
  trade     long at the close of the bar that confirms the third low; hold 48 bars; catastrophe stop -8%; costs 0.1% round trip.
  sizing    £500 pool (Revolut X style, long only): each trade takes 10% of current equity; several can be open.
  replay    from 10 Nov 2026 every run on the last 1,000 hourly bars; no state file.
  review    with the other books; PASS after 6 months: positive, >= 8 trades, mean per trade >= +0.5% (backtest +1.65%, 18 a year).
Writes runs/paper16/summary.json and runs/paper16/trades.csv.
"""
import os, json, numpy as np, pandas as pd
ROOT = os.environ.get("QLAB_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); OUT = f"{ROOT}/runs/paper16"
START = pd.Timestamp(os.environ.get("PB16_START", "2026-11-10"), tz="UTC"); EQ0, FRAC, COST, STOP, HOLD, K = 500.0, 0.10, 0.001, 0.08, 48, 3
def kl(sym):
    import urllib.request
    u = f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&limit=1000"
    k = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))[:-1]
    return pd.DataFrame([[float(x[i]) for i in (2, 3, 4, 5)] for x in k], columns=["high", "low", "close", "vol"], index=pd.to_datetime([x[0] for x in k], unit="ms", utc=True))
def signals(h):
    obv = (np.sign(h.close.diff()).fillna(0) * h.vol).cumsum().values; L, C, H = h.low.values, h.close.values, h.high.values; N = len(h)
    pl = [i for i in range(K, N - K) if L[i] == L[i - K:i + K + 1].min()]; out = []
    for k in range(2, len(pl)):
        a, b, c = pl[k - 2], pl[k - 1], pl[k]; e = c + K
        if h.index[e] < START: continue
        if c - b <= 72 and b - a <= 72 and L[c] < L[b] < L[a] and obv[c] > obv[b] > obv[a]:
            px = C[e]; end = min(e + HOLD, N - 1); lo = L[e + 1:end + 1].min() if end > e else px
            if lo <= px * (1 - STOP): r, how, j = -STOP, "stop", e + 1 + int(np.argmax(L[e + 1:end + 1] <= px * (1 - STOP)))
            elif e + HOLD <= N - 1: r, how, j = C[e + HOLD] / px - 1, "48h", e + HOLD
            else: r, how, j = None, "open", None
            rec = dict(signal=str(h.index[e]), entry=px, status=how)
            if r is not None: rec.update(closed=str(h.index[j]), ret_pct=round(100 * (r - COST), 3))
            out.append(rec)
    return out
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); rows = []
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"): rows += [dict(market=sym, **t) for t in signals(kl(sym))]
    rows.sort(key=lambda r: r["signal"]); eq = EQ0
    for r in rows:
        if "ret_pct" in r: r["stake"] = round(eq * FRAC, 2); eq += r["stake"] * r["ret_pct"] / 100
    done = [r for r in rows if "ret_pct" in r]
    summ = dict(start=str(START.date()), asof=str(pd.Timestamp.now("UTC").floor("min")), pool=round(eq, 2), closed=len(done),
                open=[r for r in rows if "ret_pct" not in r], mean_pct=round(float(np.mean([r["ret_pct"] for r in done])), 2) if done else None)
    json.dump(summ, open(f"{OUT}/summary.json", "w"), indent=1); pd.DataFrame(rows).to_csv(f"{OUT}/trades.csv", index=False); print(json.dumps(summ, indent=1))
