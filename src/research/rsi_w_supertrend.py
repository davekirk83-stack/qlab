"""
RSI 'W' + SuperTrend (GIN_XAUUSD, 24 Nov 2026, claims ~80% success). Order he looks at:
 1 RSI falls (below 30)  2 RSI makes a 'W' (second low, higher)  3 price bounces  4 SuperTrend flips up  5 all agree -> buy.
 Mirror for sells: RSI high (~70), double top turning down, SuperTrend down.
Test: 15-min bars. BTC (Binance spot 2023-26) and gold (IG 5m cache resampled, Apr-Oct 2026).
Entry next bar open after all conditions; stop at the setup extreme; exits: 1R, 2R, SuperTrend flip. Costs included.
"""
import glob, sys, numpy as np, pandas as pd

def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)

def supertrend(h, l, c, n=10, m=3.0):
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1); atr = tr.ewm(alpha=1/n, adjust=False).mean().values
    hl2 = ((h + l) / 2).values; ub = hl2 + m * atr; lb = hl2 - m * atr; C = c.values
    fu, fl, dirn = ub.copy(), lb.copy(), np.ones(len(C))
    for i in range(1, len(C)):
        fu[i] = ub[i] if (ub[i] < fu[i-1] or C[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = lb[i] if (lb[i] > fl[i-1] or C[i-1] < fl[i-1]) else fl[i-1]
        dirn[i] = 1 if C[i] > fu[i-1] else (-1 if C[i] < fl[i-1] else dirn[i-1])
    return dirn

def signals(d, side):
    """side=+1 long: RSI<30 trough L1, RSI back above 40, second trough L2 (L1<L2<45) within 60 bars, then RSI turns up,
    close > previous high (price bounce), SuperTrend up. All within 16 bars of L2."""
    r = d.rsi.values * side + (0 if side == 1 else 100); r = r if side == 1 else 100 - d.rsi.values  # mirror for shorts
    H, L, C, ST = d.high.values, d.low.values, d.close.values, d.st.values * side
    out = []; i = 1; n = len(C)
    while i < n - 2:
        if r[i] < 30 and r[i-1] >= 30:
            j = i;
            while j < n - 1 and r[j] < 40: j += 1                       # first dip, until RSI recovers above 40
            if j - i > 40: i = j; continue
            L1 = r[i:j].min(); ext = (L[i:j].min() if side == 1 else H[i:j].max())
            k = j; done = False
            while k < min(n - 1, j + 60) and not done:
                if r[k] < r[k-1] and r[k] < 45 and r[k+1] > r[k] and r[k] > L1:     # second trough (higher low)
                    ext2 = min(ext, L[j:k+1].min()) if side == 1 else max(ext, H[j:k+1].max())
                    for e in range(k + 1, min(n - 1, k + 17)):
                        bounce = C[e] > H[e-1] if side == 1 else C[e] < L[e-1]
                        if bounce and ST[e] == 1 and r[e] > r[e-1]:
                            out.append((e, ext2)); done = True; break
                    if not done: break
                if side == 1 and r[k] < L1: break                        # lower low: no W
                if side == -1 and r[k] < L1: break
                k += 1
            i = max(k, j) + 1; continue
        i += 1
    return out

def run(d, side, cost):
    res = []
    for e, ext in signals(d, side):
        if e + 1 >= len(d): continue
        en = d.open.values[e+1]; risk = (en - ext) * side
        if risk <= en * 0.0005: continue
        row = {}
        for name, tgt in (("1R", 1), ("2R", 2), ("ST", None)):
            out = None
            for t in range(e + 1, min(len(d), e + 1 + 400)):
                lo, hi = d.low.values[t], d.high.values[t]
                stop_hit = (lo <= ext) if side == 1 else (hi >= ext)
                if stop_hit: out = -1.0; break
                if tgt is not None:
                    tp = en + side * tgt * risk
                    if (hi >= tp) if side == 1 else (lo <= tp): out = float(tgt); break
                elif d.st.values[t] * side == -1: out = (d.close.values[t] - en) * side / risk; break
            if out is None: out = (d.close.values[min(len(d)-1, e+400)] - en) * side / risk
            row[name] = out - cost * en / risk
        row["t"] = d.index[e]; res.append(row)
    return pd.DataFrame(res)

def load_btc():
    fs = sorted(glob.glob(sys.argv[1] + "/BTCUSDT-15m-*.csv")); ds = []
    for f in fs:
        x = pd.read_csv(f, header=None).iloc[:, :6]; x.columns = "t open high low close vol".split()
        x["t"] = pd.to_datetime(x.t // 1000 if x.t.iloc[0] > 1e14 else x.t, unit="ms"); ds.append(x.set_index("t"))
    return pd.concat(ds).sort_index()

def load_gold():
    g = pd.read_csv("data_ig_cache/XAUUSD_5m.csv", parse_dates=["ts"]).set_index("ts")
    return g.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

if __name__ == "__main__":
    for name, d, cost in (("BTC 15m 2023-26", load_btc(), 0.0010), ("GOLD 15m Apr-Oct 2026", load_gold(), 0.00015)):
        d = d.copy(); d["rsi"] = rsi(d.close); d["st"] = supertrend(d.high, d.low, d.close)
        print(f"\n=== {name}  bars {len(d)}  cost {cost*100:.3f}% round trip ===")
        for side, lab in ((1, "LONG"), (-1, "SHORT")):
            r = run(d, side, cost)
            if r.empty: print(lab, "no trades"); continue
            half = len(r) // 2
            for ex in ("1R", "2R", "ST"):
                w = (r[ex] > 0).mean()
                print(f"{lab:5} exit {ex:2}: n {len(r):4}  win {100*w:4.0f}%  mean {r[ex].mean():+.3f}R  halves {r[ex].iloc[:half].mean():+.3f} / {r[ex].iloc[half:].mean():+.3f}")
