"""DK forwarded Brad Goh (The Trading Geek), 24 Nov: (1) direction on 15m (higher highs + higher lows -> buys only; mirror for sells),
(2) location = the small sideways base on 15m right before a strong move (demand / supply zone), wait for price to come back to it,
(3) confirmation on 5m = a candle CLOSE above the last lower high made inside/near the zone (market shift); stop below the swing low,
target 2R, 1% risk, max trades/day, no trading 15 min either side of major news. Mechanised as literally as possible:
 - 15m swings = 3-bar pivots; uptrend = last two swing highs AND lows rising (downtrend mirror)
 - base = 3-6 15m bars whose total range <= 1.0 x ATR14, followed within 3 bars by an impulse that closes >= 2 x ATR beyond the base
 - zone valid for 3 days, first return only; on 5m after the return, the last 5m pivot high (lower high) since the touch; entry on the first
   5m close above it (while price hasn't closed > 1 ATR15 below the zone); stop = lowest low since the touch - small buffer; target 2R
 - costs: BTC 0.10% round trip (taker+slip), NQ 2 pts; max 3 trades/day. R per trade reported."""
import os, sys, numpy as np, pandas as pd, requests, time
def btc5():
    f = "data_long/btc5.parquet"
    if os.path.exists(f): return pd.read_parquet(f)
    rows = []; start = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp() * 1000); end = int(pd.Timestamp("2026-11-23", tz="UTC").timestamp() * 1000)
    while start < end:
        r = requests.get("https://data-api.binance.vision/api/v3/klines", params=dict(symbol="BTCUSDT", interval="5m", startTime=start, limit=1000), timeout=30).json()
        if not r: break
        rows += r; start = r[-1][0] + 300000
    d = pd.DataFrame(rows).iloc[:, :5].astype(float); d.columns = ["t", "open", "high", "low", "close"]; d.index = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d.drop(columns="t"); os.makedirs("data_long", exist_ok=True); d.to_parquet(f); return d
def nq5():
    sys.path.insert(0, "src"); os.environ.setdefault("QLAB_ROOT", os.getcwd())
    src = open("src/ad_stack_gate.py").read(); g = {"__file__": os.path.abspath("src/ad_stack_gate.py"), "__name__": "x"}; exec(src[:src.index("R = []")], g); return g["d"][["open", "high", "low", "close"]]
def atr(d, n=14):
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1); return tr.rolling(n).mean()
def pivots(h, l, k=3):
    ph = (h == h.rolling(2 * k + 1, center=True).max()); pl = (l == l.rolling(2 * k + 1, center=True).min()); return ph, pl
def run(d5, cost_fn, label):
    d15 = d5.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(); a15 = atr(d15)
    ph, pl = pivots(d15.high, d15.low); trend = pd.Series(0, index=d15.index); last_h, last_l = [], []
    for i, t in enumerate(d15.index):
        if i >= 3 and ph.iloc[i - 3]: last_h = (last_h + [d15.high.iloc[i - 3]])[-2:]
        if i >= 3 and pl.iloc[i - 3]: last_l = (last_l + [d15.low.iloc[i - 3]])[-2:]
        if len(last_h) == 2 and len(last_l) == 2:
            trend.iloc[i] = 1 if (last_h[1] > last_h[0] and last_l[1] > last_l[0]) else -1 if (last_h[1] < last_h[0] and last_l[1] < last_l[0]) else 0
    zones = []; H, L, C, A = d15.high.values, d15.low.values, d15.close.values, a15.values
    for i in range(20, len(d15) - 4):
        for n in (3, 4, 5, 6):
            bh, bl = H[i - n + 1:i + 1].max(), L[i - n + 1:i + 1].min()
            if not np.isfinite(A[i]) or bh - bl > 1.0 * A[i]: continue
            fut = C[i + 1:i + 4]
            if (fut >= bh + 2 * A[i]).any(): zones.append((d15.index[i + 3], 1, bl, bh, A[i])); break
            if (fut <= bl - 2 * A[i]).any(): zones.append((d15.index[i + 3], -1, bl, bh, A[i])); break
    a5 = atr(d5).values; h5, l5, c5 = d5.high.values, d5.low.values, d5.close.values; idx = d5.index; pos = {t: i for i, t in enumerate(idx)}
    ph5, pl5 = pivots(d5.high, d5.low, 2); ph5 = ph5.values; pl5 = pl5.values
    tr_at = trend.reindex(idx, method="ffill").values; out = []; busy = -1; per_day = {}
    for zt, s, zl, zh, za in zones:
        if zt not in pos: continue
        i0 = pos[zt]; iend = min(len(idx) - 1, i0 + 288 * 3); touched = None
        for i in range(i0 + 1, iend):
            if touched is None:
                if (s == 1 and l5[i] <= zh) or (s == -1 and h5[i] >= zl):
                    if tr_at[i] != s: break                       # step 1: direction must agree when price arrives
                    touched = i; ext = l5[i] if s == 1 else h5[i]; lh = None
                continue
            ext = min(ext, l5[i]) if s == 1 else max(ext, h5[i])
            if (s == 1 and c5[i] < zl - za) or (s == -1 and c5[i] > zh + za): break   # zone failed
            j = i - 2
            if j > touched and ((s == 1 and ph5[j]) or (s == -1 and pl5[j])): lh = h5[j] if s == 1 else l5[j]
            if lh is not None and ((s == 1 and c5[i] > lh) or (s == -1 and c5[i] < lh)):
                if i <= busy: break
                day = idx[i].date(); per_day[day] = per_day.get(day, 0)
                if per_day[day] >= 3: break
                e = c5[i]; stop = ext - s * 0.1 * a5[i]; R = abs(e - stop)
                if R <= 0: break
                tgt = e + s * 2 * R; res = None
                for k in range(i + 1, min(len(idx), i + 288)):
                    if (s == 1 and l5[k] <= stop) or (s == -1 and h5[k] >= stop): res = -1.0; break
                    if (s == 1 and h5[k] >= tgt) or (s == -1 and l5[k] <= tgt): res = 2.0; break
                if res is None: res = s * (c5[min(len(idx) - 1, i + 287)] - e) / R; k = i + 287
                res -= cost_fn(e) / R; out.append((idx[i], s, res)); busy = k; per_day[day] += 1
                break
    R = pd.DataFrame(out, columns=["t", "s", "r"]).set_index("t")
    if not len(R): return f"{label}: no trades"
    half = R.index[len(R) // 2]; mo = R.r.groupby(R.index.to_period("M")).sum(); days = (idx[-1] - idx[0]).days
    return (f"{label}: n {len(R)} ({len(R)/days:.2f}/day) mean {R.r.mean():+.3f}R win {(R.r>0).mean():.0%} total {R.r.sum():+.1f}R | halves {R.r[R.index<half].mean():+.3f} / {R.r[R.index>=half].mean():+.3f} "
            f"| longs {R.r[R.s==1].mean():+.3f} shorts {R.r[R.s==-1].mean():+.3f} | months+ {(mo>0).sum()}/{len(mo)}")
out = [run(btc5(), lambda e: e * 0.001, "BTC 5m/15m 2024-26"), run(nq5(), lambda e: 2.0, "NQ 5m/15m Oct25-Nov26")]
open("runs/research/brad_goh_sd.txt", "w").write("\n".join(out)); print("\n".join(out))
