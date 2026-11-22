"""DK 19 Nov 16:55 ("That drop perfectly tagged the diagonal line I had drawn earlier"; Sunday test agreed 17:13).
Auto-drawn trendlines like DK's: a rising support line through two successive higher pivot lows (falling resistance through two
lower pivot highs). Each later tag of the line is a touch (#3, #4, ...). Trade the touch in the line's favour at the touch bar's close
if it closed back on the right side: stop 0.5 ATR beyond the line, target 2R, else exit after H bars. Costs 0.08% round trip.
Compared with random entries using the same stop/target. BTCUSDT Binance, 2021-2026, 1h and 15m."""
import sys; sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
COST = 0.0008
def bars(tf):
    d = load()
    if tf != "15min": d = d.resample(tf).agg(dict(o="first", h="max", l="min", c="last", v="sum")).dropna()
    return d
def atr(d, n=14):
    tr = np.maximum(d.h - d.l, np.maximum((d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs())); return tr.rolling(n).mean().values
def pivots(x, k, low=True):
    s = pd.Series(x); w = s.rolling(2*k+1, center=True)
    p = (s == (w.min() if low else w.max())); return np.where(p.values)[0]
def sim(o, h, l, c, i, side, stop, tgt, H):
    for j in range(i+1, min(i+1+H, len(c))):
        if side > 0:
            if l[j] <= stop: return (stop/c[i]-1) - COST
            if h[j] >= tgt: return (tgt/c[i]-1) - COST
        else:
            if h[j] >= stop: return -(stop/c[i]-1) - COST
            if l[j] <= tgt: return -(tgt/c[i]-1) - COST
    j = min(i+H, len(c)-1); return side*(c[j]/c[i]-1) - COST
def run(tf, k, H, tol=0.15):
    d = bars(tf); o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; A = atr(d); n = len(c)
    rows = []
    for side in (1, -1):
        piv = pivots(l if side > 0 else h, k, side > 0); src = l if side > 0 else h
        for a, b in zip(piv[:-1], piv[1:]):
            if b - a < 2*k: continue
            if side > 0 and not src[b] > src[a]: continue      # rising support: higher low
            if side < 0 and not src[b] < src[a]: continue      # falling resistance: lower high
            slope = (src[b]-src[a])/(b-a); line = lambda t: src[a] + slope*(t-a)
            # line must not have been closed through between anchors
            seg = np.arange(a, b+1)
            if side > 0 and (c[seg] < line(seg) - 0.1*A[seg]).any(): continue
            if side < 0 and (c[seg] > line(seg) + 0.1*A[seg]).any(): continue
            touch = 2; t = b + k + 1; last_touch = b
            while t < n - 1 and t < b + 40*k:
                L = line(t); at = A[t]
                if not np.isfinite(at): break
                broke = (c[t] < L - 0.5*at) if side > 0 else (c[t] > L + 0.5*at)
                if broke: break
                tag = (l[t] <= L + tol*at) if side > 0 else (h[t] >= L - tol*at)
                if tag and t - last_touch >= k:
                    touch += 1; last_touch = t
                    ok = (c[t] > L) if side > 0 else (c[t] < L)
                    if ok:
                        stop = L - 0.5*at*side; risk = abs(c[t]-stop)
                        if risk > 0:
                            tgt = c[t] + side*2*risk
                            rows.append(dict(t=d.index[t], side=side, touch=touch, R=sim(o,h,l,c,t,side,stop,tgt,H), risk=risk/c[t]))
                t += 1
    R = pd.DataFrame(rows)
    # random control: same sides, same risk distribution
    rng = np.random.default_rng(1); ctrl = []
    for _, r in R.sample(min(len(R), 3000), random_state=1).iterrows():
        i = int(rng.integers(50, n-H-1)); risk = r.risk*c[i]
        ctrl.append(sim(o,h,l,c,i,r.side, c[i]-r.side*risk, c[i]+r.side*2*risk, H))
    return R, np.array(ctrl)
out = []
for tf, k, H in (("1h", 5, 48), ("15min", 8, 96)):
    R, C = run(tf, k, H)
    out.append(f"== BTC {tf} (pivot k={k}, max hold {H} bars) — random control mean {100*C.mean():+.3f}% win {(C>0).mean():.0%} n{len(C)}")
    for side in (1, -1):
        g = R[R.side == side]
        for tch, gg in g.groupby(np.minimum(g.touch, 6)):
            half = len(gg)//2
            out.append(f"  {'support/long' if side>0 else 'resist/short'} touch {'#'+str(tch) if tch<6 else '#6+'}: n{len(gg):5} mean {100*gg.R.mean():+.3f}% win {(gg.R>0).mean():.0%} "
                       f"| halves {100*gg.R.iloc[:half].mean():+.3f}% / {100*gg.R.iloc[half:].mean():+.3f}% | 2026 {100*gg[gg.t.dt.year==2026].R.mean():+.3f}%")
    g3 = R[R.touch.isin([3,4])]
    out.append(f"  ALL touches #3-#4: n{len(g3)} mean {100*g3.R.mean():+.3f}% win {(g3.R>0).mean():.0%}; by year " + ", ".join(f"{y} {100*x.R.mean():+.2f}%" for y, x in g3.groupby(g3.t.dt.year)))
open("runs/research/channel_lines.txt","w").write("\n".join(out)); print("\n".join(out))
