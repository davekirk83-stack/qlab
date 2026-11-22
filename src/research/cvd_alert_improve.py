"""DK 22 Nov 09:35: "Keep it ... Consider which aspects work, which don't, and what can be improved." Where does the spot CVD roll-over
alert carry information? Splits by context known at the fire; a split counts only if it holds in both halves (2021-23 / 2024-26)."""
import sys; sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
d = load(); c, h, l, dl, v = d.c.values, d.h.values, d.l.values, d.delta.values, d.v.values; idx = d.index
ema4h = d.c.resample("4h").last().ewm(span=20, adjust=False).mean().reindex(idx, method="ffill").values
dd = d.c.resample("1D").last(); sma200 = dd.rolling(200).mean().shift(1).reindex(idx.floor("1D")).values
WIN = 96; rows = []; last = -10**9
for i in range(WIN, len(d) - 49):
    w = dl[i-WIN+1:i+1]; cv = np.cumsum(w); ip = int(np.argmax(cv)); lo = cv[:ip+1].min(); rise = cv[ip] - lo; vol = v[i-WIN+1:i+1].sum()
    if rise <= 0 or rise/vol < 0.02: continue
    give = (cv[ip]-cv[-1])/rise
    if give < 0.40 or (WIN-1-ip) < 4 or w[-4:].sum() >= 0 or c[i] >= c[i-WIN+1+ip]: continue
    if i - last < 48: continue
    last = i
    hi24 = h[i-96:i+1].max(); lo24 = l[i-96:i+1].min()
    rows.append(dict(t=idx[i], build=rise/vol, give=give, pos24=(c[i]-lo24)/(hi24-lo24+1e-9), vs_ema4h=c[i]/ema4h[i]-1,
                     below200=c[i] < sma200[i] if np.isfinite(sma200[i]) else np.nan, ret24=c[i]/c[i-96]-1,
                     hour=idx[i].hour, r6=c[i+24]/c[i]-1, r12=c[i+48]/c[i]-1, lo12=l[i+1:i+49].min()/c[i]-1))
F = pd.DataFrame(rows); F["half"] = np.where(F.t.dt.year <= 2023, "21-23", "24-26")
base = F.r12.mean()
def show(name, mask):
    g = F[mask]; a, b = g[g.half == "21-23"], g[g.half == "24-26"]
    ok = len(a) >= 20 and len(b) >= 20 and a.r12.mean() < 0 and b.r12.mean() < 0
    return (f"{name:42} n{len(g):4} 12h mean {100*g.r12.mean():+.2f}% down {(g.r12<0).mean():.0%} | 21-23 {100*a.r12.mean():+.2f}% (n{len(a)}) | 24-26 {100*b.r12.mean():+.2f}% (n{len(b)})" + ("  <-- holds" if ok else ""), ok)
tests = {
 "all fires": F.r12 == F.r12,
 "big build (>=4% of 24h vol)": F.build >= 0.04,
 "near the 24h HIGH (top 30% of range)": F.pos24 >= 0.7,
 "near the 24h LOW (bottom 30%)": F.pos24 <= 0.3,
 "price ABOVE 4h EMA20": F.vs_ema4h > 0,
 "price BELOW 4h EMA20": F.vs_ema4h < 0,
 "after a 24h rally (> +3%)": F.ret24 > 0.03,
 "after a 24h drop (< -3%)": F.ret24 < -0.03,
 "US session (14-21 UTC)": F.hour.between(14, 20),
 "Asia (0-7 UTC)": F.hour.between(0, 6),
 "below 200-day": F.below200 == True,
 "above 200-day": F.below200 == False,
 "near 24h high AND above 4h EMA": (F.pos24 >= 0.7) & (F.vs_ema4h > 0),
 "big build AND near 24h high": (F.build >= 0.04) & (F.pos24 >= 0.7),
 "below 200d AND near 24h high": (F.below200 == True) & (F.pos24 >= 0.6),
 "below 200d AND after rally": (F.below200 == True) & (F.ret24 > 0.02),
 "give back >= 80%": F.give >= 0.8,
}
out = []; hold = []
for k, m in tests.items():
    s, ok = show(k, m); out.append(s)
    if ok: hold.append(k)
out.append("\nSplits that hold in both halves (12h mean negative in each): " + (", ".join(hold) if hold else "none"))
open("runs/research/cvd_alert_improve.txt", "w").write("\n".join(out)); print("\n".join(out))

# As a short trigger in the context that holds: bear regime (below 200-day) and the fire comes on a bounce (24h up > 2% or top 40% of the 24h range)
ctx = (F.below200 == True) & ((F.ret24 > 0.02) | (F.pos24 >= 0.6))
def short_trade(t, stop, tgt, H=48):
    i = idx.get_loc(t); px = c[i]
    for k in range(i+1, i+H+1):
        if h[k] >= px*(1+stop): return -stop - 0.0008
        if l[k] <= px*(1-tgt): return tgt - 0.0008
    return -(c[i+H]/px - 1) - 0.0008
lines = []
for stop, tgt in ((0.02, 0.03), (0.015, 0.03), (0.02, 0.04), (0.03, 0.05)):
    for name, m in (("all fires", F.r12 == F.r12), ("CONTEXT: bear + on a bounce", ctx)):
        R = np.array([short_trade(t, stop, tgt) for t in F[m].t]); hf = F[m].half.values
        lines.append(f"stop {stop:.1%} target {tgt:.0%} | {name:28} n{len(R):4} mean {100*R.mean():+.2f}% win {(R>0).mean():.0%} | 21-23 {100*R[hf=='21-23'].mean():+.2f}% 24-26 {100*R[hf=='24-26'].mean():+.2f}%")
g = F[ctx]; lines.append(f"context fires per year: " + ", ".join(f"{y} {n}" for y, n in g.t.dt.year.value_counts().sort_index().items()))
open("runs/research/cvd_alert_improve.txt", "a").write("\n\n" + "\n".join(lines)); print("\n".join(lines))
