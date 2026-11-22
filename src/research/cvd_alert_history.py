"""Doc 231 follow-up (DK 19 Nov 19:07): spot CVD roll-over alert over the full Binance history, 2021-2026."""
import sys; sys.path.insert(0, "src"); sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
d = load(); c = d.c.values; h = d.h.values; l = d.l.values; dl = d.delta.values; v = d.v.values; idx = d.index
WIN, BUILD, GIVE = 96, 0.02, 0.40
fires = []; last = -10**9
for i in range(WIN, len(d)):
    w = dl[i-WIN+1:i+1]; cv = np.cumsum(w); ip = int(np.argmax(cv)); lo = cv[:ip+1].min(); rise = cv[ip] - lo
    if rise <= 0 or rise / v[i-WIN+1:i+1].sum() < BUILD: continue
    if (cv[ip] - cv[-1]) / rise < GIVE or (WIN-1-ip) < 4 or w[-4:].sum() >= 0 or c[i] >= c[i-WIN+1+ip]: continue
    if i - last < 48: continue
    last = i
    j = min(i + 48, len(d) - 1)
    if j - i < 48: continue
    px = c[i]; lo12 = l[i+1:j+1].min() / px - 1; hi12 = h[i+1:j+1].max() / px - 1; cl12 = c[j] / px - 1
    fires.append(dict(t=idx[i], px=px, lo=lo12, hi=hi12, close=cl12))
F = pd.DataFrame(fires); F["year"] = F.t.dt.year
# baseline: random bars, same horizon
rng = np.random.default_rng(0); ii = rng.integers(WIN, len(d) - 49, 5000)
B = pd.DataFrame(dict(lo=[l[i+1:i+49].min()/c[i]-1 for i in ii], hi=[h[i+1:i+49].max()/c[i]-1 for i in ii], close=[c[i+48]/c[i]-1 for i in ii]))
def summ(x, name):
    return (f"{name:10} n{len(x):4} | 12h close mean {100*x.close.mean():+.2f}% median {100*x.close.median():+.2f}% down {(x.close<0).mean():.0%} | "
            f"low median {100*x.lo.median():+.2f}% (≤−2%: {(x.lo<=-0.02).mean():.0%}, ≤−3%: {(x.lo<=-0.03).mean():.0%}) | high median {100*x.hi.median():+.2f}% (≥+2%: {(x.hi>=0.02).mean():.0%})")
out = [summ(F, "ALERT"), summ(B, "random")]
for y, g in F.groupby("year"): out.append(summ(g, str(y)))
# as a short trigger: sell at fire, stop +2%, target -3%, else exit at 12h; cost 0.08% round trip
res = []
for _, r in F.iterrows():
    i = idx.get_loc(r.t); px = r.px; R = None
    for k in range(i+1, i+49):
        if h[k] >= px*1.02: R = -0.02; break
        if l[k] <= px*0.97: R = 0.03; break
    if R is None: R = -(c[i+48]/px - 1)
    res.append(R - 0.0008)
res = np.array(res)
half = len(res)//2
out.append(f"SHORT trigger (stop +2%, target −3%, else 12h exit, 0.08% costs): n{len(res)} mean {100*res.mean():+.2f}% win {(res>0).mean():.0%} "
           f"total {100*res.sum():+.0f}% | halves {100*res[:half].mean():+.2f}% / {100*res[half:].mean():+.2f}%")
last5 = F[F.t >= pd.Timestamp("2026-11-01", tz="UTC")]
out.append("Nov 2026 fires:\n" + last5.assign(lo=lambda x: (100*x.lo).round(1), hi=lambda x:(100*x.hi).round(1), close=lambda x:(100*x.close).round(1)).to_string(index=False))
open("runs/research/cvd_alert_history.txt","w").write("\n".join(out)); print("\n".join(out))

# regime check: does it work below the 200-day average (bear regime), as in Nov 2026?
dd = d.c.resample("1D").last(); sma = dd.rolling(200).mean().shift(1)
F["below200"] = [bool(dd.get(t.floor("1D")) is not None and c0 < sma.get(t.floor("1D"), np.nan)) for t, c0 in zip(F.t, F.px)]
F["R"] = res
lines = []
for k, g in F.groupby("below200"):
    lines.append(summ(g, "below200" if k else "above200") + f" | short trigger mean {100*g.R.mean():+.2f}% win {(g.R>0).mean():.0%} n{len(g)}")
    if k:
        for y, gg in g.groupby("year"): lines.append(f"   {y}: n{len(gg)} short mean {100*gg.R.mean():+.2f}% 12h close median {100*gg.close.median():+.2f}%")
open("runs/research/cvd_alert_history.txt","a").write("\n"+"\n".join(lines)); print("\n".join(lines))
