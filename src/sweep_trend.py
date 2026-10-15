"""Does the London sweep run WITH or AGAINST the prevailing trend?

Hypothesis worth testing: the classic 'stop hunt' shape is a sweep AGAINST the
trend (taking out the obvious stops) followed by continuation WITH the trend.
Pooling all regimes would hide that completely, which is what the first test did.
"""
import os, numpy as np, pandas as pd
D="/home/claude/qlab/data_1h"
SY=sorted(f[:-4] for f in os.listdir(D) if f.endswith(".csv"))
S={"ASIA":(0,8),"LONDON":(7,16),"US":(13,21)}

def frames(sym):
    d=pd.read_csv(f"{D}/{sym}.csv",parse_dates=["date"]).set_index("date").sort_index()
    d=d[~d.index.duplicated()]
    # trend: daily close vs its own 50-day MA, known BEFORE the day starts
    day=d.resample("D").agg(close=("close","last")).dropna()
    ma=day.close.rolling(50).mean()
    trend=(day.close>ma).shift(1)          # yesterday's state -> no lookahead
    rows=[]
    h=d.index.hour
    for n,(a,b) in S.items():
        m=(h>=a)&(h<b); sub=d[m]
        g=sub.groupby(sub.index.date).agg(open=("open","first"),high=("high","max"),
                                          low=("low","min"),close=("close","last"))
        g.index=pd.to_datetime(g.index); g["session"]=n; rows.append(g)
    f=pd.concat(rows).reset_index().rename(columns={"index":"day"})
    p=f.pivot(index="day",columns="session")
    p.columns=[f"{a}_{b}" for a,b in p.columns]
    p=p.dropna()
    p["up"]=trend.reindex(p.index)
    return p.dropna(subset=["up"])

up_hi=[];up_lo=[];dn_hi=[];dn_lo=[]
up_sweep_lo_then_close_up=[];dn_sweep_hi_then_close_dn=[]
up_sweep_hi_then_close_up=[];dn_sweep_lo_then_close_dn=[]
n=0
for s in SY:
    try: p=frames(s)
    except Exception: continue
    if len(p)<200: continue
    n+=len(p)
    ush,usl,ucl,uop=p["high_US"],p["low_US"],p["close_US"],p["open_US"]
    lh,ll=p["high_LONDON"],p["low_LONDON"]
    up=p["up"].astype(bool)
    swh=ush>lh; swl=usl<ll
    up_hi.append(swh[up].mean()); up_lo.append(swl[up].mean())
    dn_hi.append(swh[~up].mean()); dn_lo.append(swl[~up].mean())
    # after an AGAINST-trend sweep, does the session close WITH the trend?
    m=up&swl
    if m.sum()>20: up_sweep_lo_then_close_up.append((ucl[m]>uop[m]).mean())
    m=(~up)&swh
    if m.sum()>20: dn_sweep_hi_then_close_dn.append((ucl[m]<uop[m]).mean())
    # and after a WITH-trend sweep?
    m=up&swh
    if m.sum()>20: up_sweep_hi_then_close_up.append((ucl[m]>uop[m]).mean())
    m=(~up)&swl
    if m.sum()>20: dn_sweep_lo_then_close_dn.append((ucl[m]<uop[m]).mean())

print("DOES THE LONDON SWEEP RUN WITH OR AGAINST THE TREND?")
print(f"  {n:,} session-days, {len(SY)} symbols, trend = daily close vs 50d MA (lagged)\n")
print("="*72)
print("  WHICH SIDE GETS SWEPT, BY TREND")
print("="*72)
print(f"  {'regime':16s} {'US sweeps London HIGH':>24} {'US sweeps London LOW':>24}")
print(f"  {'UPTREND':16s} {np.mean(up_hi)*100:23.1f}% {np.mean(up_lo)*100:23.1f}%")
print(f"  {'DOWNTREND':16s} {np.mean(dn_hi)*100:23.1f}% {np.mean(dn_lo)*100:23.1f}%")
print()
print("  -> in an uptrend the sweep favours the %s"%("HIGH (with trend)" if np.mean(up_hi)>np.mean(up_lo) else "LOW (against trend)"))
print("  -> in a downtrend the sweep favours the %s"%("LOW (with trend)" if np.mean(dn_lo)>np.mean(dn_hi) else "HIGH (against trend)"))
print()
print("="*72)
print("  AFTER THE SWEEP, HOW DOES THE US SESSION CLOSE?")
print("="*72)
if up_sweep_lo_then_close_up:
    print(f"  UPTREND, swept the LOW (against trend)  -> closes UP   {np.mean(up_sweep_lo_then_close_up)*100:5.1f}%")
if up_sweep_hi_then_close_up:
    print(f"  UPTREND, swept the HIGH (with trend)    -> closes UP   {np.mean(up_sweep_hi_then_close_up)*100:5.1f}%")
if dn_sweep_hi_then_close_dn:
    print(f"  DOWNTREND, swept the HIGH (against)     -> closes DOWN {np.mean(dn_sweep_hi_then_close_dn)*100:5.1f}%")
if dn_sweep_lo_then_close_dn:
    print(f"  DOWNTREND, swept the LOW (with trend)   -> closes DOWN {np.mean(dn_sweep_lo_then_close_dn)*100:5.1f}%")
