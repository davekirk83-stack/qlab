"""Improvement pass on the CVD roll-up (mirror) alert: price conditions and flush context. Long trigger stop -2% / target +3% / 12h, 0.08% costs."""
import sys; sys.path.insert(0, "src"); sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from btc15 import load
d = load(); c, h, l, dl, v, idx = d.c.values, d.h.values, d.l.values, d.delta.values, d.v.values, d.index
hi72 = pd.Series(h).rolling(288).max().values; lo24 = pd.Series(l).rolling(96).min().values
def run(name, price_rule, ctx_rule, GIVE=0.40, BUILD=0.02):
    rows = []; last = -10**9
    for i in range(400, len(d) - 49):
        if i - last < 48: continue
        w = dl[i-95:i+1]; cv = np.cumsum(w); ip = int(np.argmin(cv)); top = cv[:ip+1].max(); drop = top - cv[ip]
        if drop <= 0 or drop / v[i-95:i+1].sum() < BUILD or (cv[-1]-cv[ip])/drop < GIVE or (95-ip) < 4 or w[-4:].sum() <= 0: continue
        if not price_rule(i, i-95+ip) or not ctx_rule(i): continue
        last = i; px = c[i]; R = None
        for k in range(i+1, i+49):
            if l[k] <= px*0.98: R = -0.02; break
            if h[k] >= px*1.03: R = 0.03; break
        rows.append((idx[i], (R if R is not None else c[i+48]/px-1) - 0.0008))
    if not rows: return f"{name:52} n0"
    R = pd.Series([r for _, r in rows], index=[t for t, _ in rows]); hf = pd.Timestamp("2024-01-01", tz="UTC")
    y = R.groupby(R.index.year).mean()
    return f"{name:52} n{len(R):4} mean {100*R.mean():+.2f}% win {(R>0).mean():.0%} | 2021-23 {100*R[R.index<hf].mean():+.2f} / 2024-26 {100*R[R.index>=hf].mean():+.2f} | yrs+ {(y>0).sum()}/{len(y)}"
anyp = lambda i, j: True
below = lambda i, j: c[i] <= c[j]
newlow = lambda i, j: l[i-3:i+1].min() <= lo24[i-4] * 1.001       # swept the 24h low in the last hour
higher = lambda i, j: c[i] > c[j]                                 # price already turned up
allc = lambda i: True
flush6 = lambda i: c[i] <= hi72[i]*0.94
flush10 = lambda i: c[i] <= hi72[i]*0.90
out = []
for pn, pr in (("any price", anyp), ("price at/below the CVD low", below), ("swept 24h low in last hour", newlow), ("price already above", higher)):
    for cn, cr in (("all", allc), ("after 6% flush (72h)", flush6), ("after 10% flush", flush10)):
        out.append(run(f"{pn} | {cn}", pr, cr))
open("runs/research/cvd_rollup_improve.txt", "w").write("\n".join(out)); print("\n".join(out))
