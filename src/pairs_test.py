"""Pairs / spread reversion on crypto 15-min (task 13, 24 Oct 2026). Each month: fit on the prior 60 days (log-price OLS hedge ratio,
ADF on the residual), keep the 10 most cointegrated pairs with half-life 4h-3d, then trade them out of sample for the month:
enter when the residual z-score (60-day) crosses +/-2 (short the rich leg, long the cheap), exit at |z| < 0.5, stop at |z| > 4 or 3 days.
Costs: taker + slippage both legs in and out (P6: 4.5bp + 5bp per leg side). Returns are per unit of gross notional (both legs)."""
import os, glob, itertools, numpy as np, pandas as pd
from statsmodels.tsa.stattools import adfuller
COST = 4*(4.5+5)/10000   # four leg-sides per round trip
files = sorted(glob.glob("/home/claude/qlab/data_15m/*.csv"))
P = {}
for f in files:
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); P[os.path.basename(f)[:-4]] = d.close
P = pd.DataFrame(P).dropna(axis=1, thresh=80000).ffill().dropna(); L = np.log(P)
print("coins", P.shape[1], "bars", len(P), P.index[0], "->", P.index[-1])
months = pd.date_range(P.index[0].normalize() + pd.Timedelta(days=60), P.index[-1], freq="MS")
BARS60 = 60*96
rows = []
for m0 in months:
    fit = L[(L.index < m0) & (L.index >= m0 - pd.Timedelta(days=60))]
    if len(fit) < BARS60*0.8: continue
    cands = []
    for a, b in itertools.combinations(fit.columns, 2):
        x, y = fit[a].values, fit[b].values; beta = np.polyfit(x, y, 1)[0]; res = y - beta*x
        if abs(beta) < 0.2 or abs(beta) > 5: continue
        # half-life from AR(1)
        dr = np.diff(res); phi = np.polyfit(res[:-1], dr, 1)[0]
        if phi >= 0: continue
        hl = -np.log(2)/np.log(1+phi)
        if not (16 <= hl <= 288): continue   # 4h .. 3d in 15-min bars
        try: p = adfuller(res, maxlag=4, autolag=None, result_object=False)[1]
        except Exception: continue
        cands.append((p, a, b, beta, res.mean(), res.std()))
    cands.sort(); keep = cands[:10]
    m1 = m0 + pd.offsets.MonthBegin(1); oos = L[(L.index >= m0) & (L.index < m1)]
    for p, a, b, beta, mu, sd in keep:
        z = ((oos[b] - beta*oos[a]) - mu)/sd; pos = 0; e_i = None; armed = False
        for i in range(len(z)):
            if pos == 0:
                if abs(z.iloc[i]) < 2: armed = True; continue
                if not armed: continue
                if z.iloc[i] > 2: pos = -1; e_i = i; armed = False      # spread rich: short b, long a
                elif z.iloc[i] < -2: pos = 1; e_i = i; armed = False
            else:
                done = abs(z.iloc[i]) < 0.5 or abs(z.iloc[i]) > 4 or (i - e_i) >= 288 or i == len(z)-1
                if done:
                    ret = pos*((oos[b].iloc[i]-oos[b].iloc[e_i]) - beta*(oos[a].iloc[i]-oos[a].iloc[e_i]))/(1+abs(beta))
                    rows.append((m0, a, b, ret - COST, "stop" if abs(z.iloc[i]) > 4 else ("time" if (i-e_i) >= 288 else "exit"))); pos = 0
r = pd.DataFrame(rows, columns=["m", "a", "b", "ret", "how"])
print(f"trades {len(r)} over {r.m.nunique()} months; net/trade {r.ret.mean()*100:+.3f}% (gross notional), t {r.ret.mean()/r.ret.std()*np.sqrt(len(r)):+.1f}, win {100*(r.ret>0).mean():.0f}%")
print("exits:", r.how.value_counts().to_dict()); h = len(r)//2
print(f"H1 {r.ret.iloc[:h].mean()*100:+.3f}%  H2 {r.ret.iloc[h:].mean()*100:+.3f}%  | per month: {r.groupby('m').ret.sum().mul(100).round(2).to_dict()}")
