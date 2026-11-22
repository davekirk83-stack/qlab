"""EMA contraction (doc 248 #4) — improve and check breadth: same rule on 1h for NQ, US 500, Wall Street, Germany 40, FTSE, gold, and a
trend filter (only trade the break in the direction of the 200-EMA slope)."""
import numpy as np, pandas as pd
SRC = {"NQ": ("data_nq_cache/nq_5m.csv", 2.0), "US500": ("data_ig_cache/USA500IDXUSD_5m.csv", 0.5), "WALLST": ("data_ig_cache/USA30IDXUSD_5m.csv", 3.0),
       "GER40": ("data_ig_cache/DEUIDXEUR_5m.csv", 1.5), "FTSE": ("data_ig_cache/GBRIDXGBP_5m.csv", 1.0), "GOLD": ("data_ig_cache/XAUUSD_5m.csv", 0.4)}
def test(m, tf, trend):
    d = pd.read_csv(SRC[m][0], parse_dates=["ts"]).set_index("ts")[["open","high","low","close"]].resample(tf).agg(dict(open="first", high="max", low="min", close="last")).dropna()
    cost = SRC[m][1]; c = d.close; E = pd.concat([c.ewm(span=s, adjust=False).mean() for s in (20, 50, 100, 200)], axis=1)
    tr = np.maximum(d.high-d.low, np.maximum((d.high-c.shift()).abs(), (d.low-c.shift()).abs())); A = tr.rolling(14).mean()
    spread = (E.max(axis=1)-E.min(axis=1))/A; tight = spread < spread.rolling(500, min_periods=200).quantile(0.2); was = tight.rolling(6).max().astype(bool)
    slope = E.iloc[:, 3].diff(10)
    up = was & (c > E.max(axis=1)) & (c.shift() <= E.max(axis=1).shift()); dn = was & (c < E.min(axis=1)) & (c.shift() >= E.min(axis=1).shift())
    if trend: up &= slope > 0; dn &= slope < 0
    H, L, C, a = d.high.values, d.low.values, c.values, A.values; res = []; nxt = 0
    for i in np.where((up | dn).values)[0]:
        if i < nxt or i < 220 or i > len(C)-50: continue
        s = 1 if up.iloc[i] else -1; st = C[i]-s*1.5*a[i]; tg = C[i]+s*3*a[i]; r = None
        for j in range(i+1, i+49):
            if (s>0 and L[j]<=st) or (s<0 and H[j]>=st): r = -1.5*a[i]; break
            if (s>0 and H[j]>=tg) or (s<0 and L[j]<=tg): r = 3*a[i]; break
        if r is None: j = i+48; r = s*(C[j]-C[i])
        res.append((r-cost)/a[i]); nxt = j
    return np.array(res)
out = []; pool = {False: [], True: []}
for m in SRC:
    for trend in (False, True):
        r = test(m, "1h", trend); pool[trend] += list(r); hf = len(r)//2
        out.append(f"  {m:6} 1h {'trend-filtered' if trend else 'all          '}: n{len(r):3} mean {r.mean():+.3f} ATR win {(r>0).mean():.0%} | halves {r[:hf].mean():+.3f}/{r[hf:].mean():+.3f}")
for trend in (False, True):
    p = np.array(pool[trend]); out.append(f"  POOLED {'trend-filtered' if trend else 'all'}: n{len(p)} mean {p.mean():+.3f} ATR win {(p>0).mean():.0%}")
open("runs/research/ema_contraction_improve.txt", "w").write("\n".join(out)); print("\n".join(out))
