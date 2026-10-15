"""Everything else the session data can tell us."""
import os, numpy as np, pandas as pd
D="/home/claude/qlab/data_1h"
SY=sorted(f[:-4] for f in os.listdir(D) if f.endswith(".csv"))
S={"ASIA":(0,8),"LONDON":(7,16),"US":(13,21)}
def load(s):
    d=pd.read_csv(f"{D}/{s}.csv",parse_dates=["date"]).set_index("date").sort_index()
    return d[~d.index.duplicated()]
def sess(d):
    rows=[];h=d.index.hour
    for n,(a,b) in S.items():
        m=(h>=a)&(h<b);sub=d[m]
        g=sub.groupby(sub.index.date).agg(open=("open","first"),high=("high","max"),
            low=("low","min"),close=("close","last"),vol=("volume","sum"))
        g.index=pd.to_datetime(g.index);g["s"]=n;rows.append(g)
    p=pd.concat(rows).reset_index().rename(columns={"index":"day"}).pivot(index="day",columns="s")
    p.columns=[f"{a}_{b}" for a,b in p.columns];return p.dropna()

rng={k:[] for k in S}; vol={k:[] for k in S}
sets_hi={k:[] for k in S}; sets_lo={k:[] for k in S}
cont={}; wknd=[]; wkdy=[]; hourly={h:[] for h in range(24)}
asia_pred=[]
for s in SY:
    d=load(s); p=sess(d)
    if len(p)<200: continue
    for k in S:
        rng[k].append(((p[f"high_{k}"]-p[f"low_{k}"])/p[f"open_{k}"]).mean())
        vol[k].append(p[f"vol_{k}"].mean())
    dh=p[[f"high_{k}" for k in S]].idxmax(axis=1).str.replace("high_","")
    dl=p[[f"low_{k}" for k in S]].idxmin(axis=1).str.replace("low_","")
    for k in S:
        sets_hi[k].append((dh==k).mean()); sets_lo[k].append((dl==k).mean())
    # does one session's direction predict the next?
    ra={k:(p[f"close_{k}"]/p[f"open_{k}"]-1) for k in S}
    for a,b in (("ASIA","LONDON"),("LONDON","US"),("ASIA","US")):
        cont.setdefault(f"{a}->{b}",[]).append(((ra[a]>0)==(ra[b]>0)).mean())
    # does a wide Asia range predict a wide US range?
    ar=(p.high_ASIA-p.low_ASIA)/p.open_ASIA; ur=(p.high_US-p.low_US)/p.open_US
    asia_pred.append(ar.corr(ur))
    # weekend vs weekday (crypto trades 7 days)
    r=d.close.pct_change().dropna()
    wknd.append(r[r.index.dayofweek>=5].mean()); wkdy.append(r[r.index.dayofweek<5].mean())
    for h in range(24):
        x=r[r.index.hour==h]
        if len(x)>100: hourly[h].append(x.mean())

print("SESSION DATA — WHAT ELSE IS IN THERE\n")
print("="*74); print("  1. RANGE AND VOLUME BY SESSION"); print("="*74)
print(f"  {'session':10s} {'mean range':>12} {'rel. volume':>13}")
tv=sum(np.mean(vol[k]) for k in S)
for k in S:
    print(f"  {k:10s} {np.mean(rng[k])*100:11.2f}% {np.mean(vol[k])/tv*100:12.1f}%")
print()
print("="*74); print("  2. WHICH SESSION SETS THE DAY'S HIGH AND LOW?"); print("="*74)
print(f"  {'session':10s} {'sets the HIGH':>15} {'sets the LOW':>14}")
for k in S:
    print(f"  {k:10s} {np.mean(sets_hi[k])*100:14.1f}% {np.mean(sets_lo[k])*100:13.1f}%")
print()
print("="*74); print("  3. DOES ONE SESSION'S DIRECTION CARRY TO THE NEXT?"); print("="*74)
for k,v in cont.items():
    m=np.mean(v)
    print(f"  {k:16s} same direction {m*100:5.1f}%   {'-> some persistence' if m>0.55 else '-> coin flip'}")
print()
print("="*74); print("  4. DOES A WIDE ASIA RANGE PREDICT A WIDE US RANGE?"); print("="*74)
print(f"  correlation(Asia range, US range) = {np.mean(asia_pred):+.3f}")
print(f"  -> {'useful: volatility clusters across sessions' if np.mean(asia_pred)>0.3 else 'weak'}")
print()
print("="*74); print("  5. WEEKEND vs WEEKDAY (crypto trades 7 days)"); print("="*74)
print(f"  weekday mean daily {np.mean(wkdy)*100:+.4f}%   weekend {np.mean(wknd)*100:+.4f}%")
print()
print("="*74); print("  6. HOUR-OF-DAY RETURN PROFILE (UTC)"); print("="*74)
hs=sorted(((h,np.mean(v)) for h,v in hourly.items() if v),key=lambda x:-x[1])
print("  best hours: "+", ".join(f"{h:02d}:00 {v*100:+.4f}%" for h,v in hs[:5]))
print("  worst hours:"+", ".join(f"{h:02d}:00 {v*100:+.4f}%" for h,v in hs[-5:]))
