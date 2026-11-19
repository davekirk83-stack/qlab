"""Volatility risk premium test (DK 18 Nov 2026: "Maybe options is better?"). S&P 500 daily + VIX, 2000 - Nov 2026.
Weekly: open at Friday close, settle at next Friday close (5 trading days).
Short put spread: short strike = S*(1 - 1.0*sigma_w) (~16 delta), long strike 2.5% below it. Iron condor adds the mirror call spread.
Priced with Black-Scholes off VIX (puts at VIX+2 vol pts skew for the short, +4 for the long wing; calls at VIX-2), r=0.
Cost: 1.5 index pts per spread at S=7,400, scaled with S (IG-style dealing spread on both legs). P&L in index points and in 'risk units' (width - credit)."""
import pandas as pd, numpy as np
from math import log, sqrt, exp, erf
N = lambda x: 0.5 * (1 + erf(x / sqrt(2)))
def bs(S, K, T, v, call):
    if v <= 0 or T <= 0: return max(0.0, (S - K) if call else (K - S))
    d1 = (log(S / K) + 0.5 * v * v * T) / (v * sqrt(T)); d2 = d1 - v * sqrt(T)
    return S * N(d1) - K * N(d2) if call else K * N(-d2) - S * N(-d1)
spx = pd.read_csv("data_daily/SPX.csv", index_col=0, parse_dates=True).close
vix = pd.read_csv("data_daily/VIX.csv", index_col=0, parse_dates=True).close
spx.index = pd.to_datetime(pd.Index(spx.index).map(lambda x: str(x)[:10])); vix.index = pd.to_datetime(pd.Index(vix.index).map(lambda x: str(x)[:10]))
spx = spx[~spx.index.duplicated()]; vix = vix[~vix.index.duplicated()]
df = pd.concat([spx.rename("S"), vix.rename("V")], axis=1, sort=True).dropna()
fr = df[df.index.dayofweek == 4]
T = 5 / 252; W = 0.025; rows = []
for i in range(len(fr) - 1):
    t0, t1 = fr.index[i], fr.index[i + 1]
    if (t1 - t0).days != 7: continue
    S, V, ST = fr.S.iloc[i], fr.V.iloc[i] / 100, fr.S.iloc[i + 1]
    sw = V * sqrt(T); cost = 1.5 * S / 7400
    kp = S * (1 - sw); kp2 = kp * (1 - W)
    cp = bs(S, kp, T, V + .02, False) - bs(S, kp2, T, V + .04, False)
    put = cp - min(max(kp - ST, 0), kp - kp2) - cost
    kc = S * (1 + sw); kc2 = kc * (1 + W)
    cc = bs(S, kc, T, max(V - .02, .05), True) - bs(S, kc2, T, max(V - .03, .05), True)
    call = cc - min(max(ST - kc, 0), kc2 - kc) - cost
    risk_p = (kp - kp2) - cp
    rows.append(dict(t=t0, V=V*100, put=put, ic=put + call, risk=risk_p, credit=cp))
r = pd.DataFrame(rows).set_index("t")
def rep(name, x, risk):
    u = x / risk; eq = u.cumsum(); dd = (eq - eq.cummax()).min(); h = len(u)//2
    print(f"{name:34s} n={len(u):4d} win {100*(x>0).mean():5.1f}%  avg {u.mean():+.3f}R  worst week {u.min():+.2f}R  max DD {dd:+.1f}R  total {u.sum():+.1f}R  halves {u.iloc[:h].sum():+.1f}/{u.iloc[h:].sum():+.1f}")
    return u
print(f"weeks {len(r)}  {r.index.min().date()} .. {r.index.max().date()}  avg credit {100*(r.credit/r.risk).mean():.1f}% of risk\n")
u = rep("Put spread, all weeks", r.put, r.risk)
rep("Iron condor, all weeks", r.ic, 2*r.risk)
for lo, hi in ((0, 15), (15, 20), (20, 30), (30, 99)):
    m = (r.V >= lo) & (r.V < hi); rep(f"Put spread, VIX {lo}-{hi}", r.put[m], r.risk[m])
print("\nPut spread by year (R):"); print((r.put / r.risk).groupby(r.index.year).sum().round(1).to_string())
print("\nWorst 8 weeks (R):"); print((r.put / r.risk).nsmallest(8).round(2).to_string())
