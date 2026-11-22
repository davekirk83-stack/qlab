"""DK 22 Nov: "add the CVD rollover for upward reversals". Mirror of the spot CVD roll-over alert (doc 231):
spot CVD sold down over 24h (>=2% of volume), then gave back >=40% of that selling with buying in the last hour, while price is
still at/below where the selling bottomed. Judged by context (both halves). BTC 15-min Binance spot 2021-26. Long trigger: stop -2%, target +3%, else 12h."""
import sys; sys.path.insert(0, "src"); sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
d = load(); c, h, l, dl, v, idx = d.c.values, d.h.values, d.l.values, d.delta.values, d.v.values, d.index
WIN, BUILD, GIVE = 96, 0.02, 0.40
dd = d.c.resample("1D").last(); sma = dd.rolling(200).mean().shift(1)
rows = []; last = -10**9
for i in range(WIN, len(d) - 49):
    w = dl[i-WIN+1:i+1]; cv = np.cumsum(w); ip = int(np.argmin(cv)); hi = cv[:ip+1].max(); drop = hi - cv[ip]
    if drop <= 0 or drop / v[i-WIN+1:i+1].sum() < BUILD: continue
    if (cv[-1] - cv[ip]) / drop < GIVE or (WIN-1-ip) < 4 or w[-4:].sum() <= 0 or c[i] <= c[i-WIN+1+ip]*0 or c[i] > c[i-WIN+1+ip]: continue
    if i - last < 48: continue
    last = i; px = c[i]; R = None
    for k in range(i+1, i+49):
        if l[k] <= px*0.98: R = -0.02; break
        if h[k] >= px*1.03: R = 0.03; break
    if R is None: R = c[i+48]/px - 1
    day = idx[i].floor("1D"); ma = sma.get(day, np.nan)
    r24 = px / c[i-96] - 1; pos = (px - l[i-95:i+1].min()) / max(h[i-95:i+1].max() - l[i-95:i+1].min(), 1e-9)
    bull = bool(px > ma) if np.isfinite(ma) else None
    ctx = "STRONGER" if (bull and (r24 < -2/100 or pos <= 0.4)) else "CAUTION" if r24 > 3/100 else "NEUTRAL"
    rows.append(dict(t=idx[i], R=R - 0.0008, close=c[i+48]/px-1, bull=bull, r24=r24, pos=pos, ctx=ctx))
F = pd.DataFrame(rows); F["y"] = F.t.dt.year; half = F.t.iloc[len(F)//2]
rng = np.random.default_rng(0); ii = rng.integers(WIN, len(d)-49, 5000)
base = np.mean([c[i+48]/c[i]-1 for i in ii])
def s(g, name):
    a, b = g[g.t < half], g[g.t >= half]
    return f"{name:34} n{len(g):4} long-trigger mean {100*g.R.mean():+.2f}% win {(g.R>0).mean():.0%} | 12h close {100*g.close.mean():+.2f}% | halves {100*a.R.mean():+.2f}/{100*b.R.mean():+.2f}"
out = [f"random 12h close mean {100*base:+.2f}%", s(F, "ALL roll-ups")]
for k, g in F.groupby("bull"): out.append(s(g, "above 200-day" if k else "below 200-day"))
for k, g in F.groupby("ctx"): out.append(s(g, f"context {k}"))
for k, g in F.groupby(["bull", F.r24 < -0.03]): out.append(s(g, f"bull={k[0]} after 24h drop>3%={k[1]}"))
for y, g in F.groupby("y"): out.append(s(g, f"  {y}"))
open("runs/research/cvd_rollup.txt", "w").write("\n".join(out)); print("\n".join(out))
