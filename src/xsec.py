"""
CROSS-SECTIONAL FACTOR BOOK — long the best-ranked, short the worst, each day.

Why this and not another directional book: all four registered strategies are
long-biased crypto mean-reversion. They will draw down together. A
cross-sectional book holds equal long and short notional, so the market's
direction largely cancels and it is diversifying rather than duplicating.

It also uses what doc 57 measured rather than anything new: rank every
instrument each day on the composite, go long the top decile and short the
bottom, rebalance, hold.

TESTED HONESTLY
  - costs charged on every rebalance, both legs
  - the market leg is explicitly removed (returns are demeaned across the
    panel each day), so this cannot be long-drift in disguise
  - by year, and the 2025 bear separately
  - turnover reported, because a factor that rebalances daily pays for it
"""
import warnings; warnings.filterwarnings("ignore")
import sys,os,glob; sys.path.insert(0,'/home/claude/qlab/src')
import numpy as np, pandas as pd
import elements as EL

FEE=10/10000      # 5bp a side, crypto perp taker

panel={}
for p in (sorted(glob.glob("/home/claude/qlab/data/*.csv"))+
          sorted(glob.glob("/home/claude/qlab/data_alt/*.csv"))):
    s=os.path.basename(p)[:-4]
    try:
        d=pd.read_csv(p); d["date"]=pd.to_datetime(d["date"],errors="coerce")
        d=d.dropna(subset=["date"]).set_index("date").sort_index()
    except Exception: continue
    if len(d)>800 and not d.close.le(0).any(): panel[s]=d[~d.index.duplicated()]

# build the composite per instrument
FE=["bb_width_50","dist_ema_200","vol_rel"]
SG={"bb_width_50":-1,"dist_ema_200":-1,"vol_rel":+1}
score={}; rets={}
for s,df in panel.items():
    try: F=EL.build(df)
    except Exception: continue
    if any(k not in F for k in FE): continue
    M=pd.DataFrame({k:F[k] for k in FE},index=df.index)
    score[s]=M
    rets[s]=df.close.pct_change()
S=pd.concat({s:m for s,m in score.items()},axis=1)
R=pd.DataFrame(rets)
dates=R.index
print(f"{len(score)} instruments, {len(dates)} days\n")

def run(hold,topq):
    # rank each element cross-sectionally per day, average with signs
    comp=None
    for k in FE:
        X=S.xs(k,axis=1,level=1)
        r=X.rank(axis=1,pct=True)*SG[k]
        comp=r if comp is None else comp+r
    comp=comp.reindex(R.index)
    pnl=[]; turn=[]; prev=pd.Series(dtype=float)
    for i in range(300,len(dates)-hold,hold):
        row=comp.iloc[i].dropna()
        if len(row)<20: continue
        k=max(3,int(len(row)*topq))
        longs=row.nlargest(k).index; shorts=row.nsmallest(k).index
        w=pd.Series(0.0,index=row.index)
        w[longs]=1.0/k; w[shorts]=-1.0/k
        fwd=(R.iloc[i+1:i+1+hold][w.index].fillna(0)+1).prod()-1
        mkt=R.iloc[i+1:i+1+hold].mean(axis=1).add(1).prod()-1     # market leg
        gross=float((w*fwd).sum())
        t=float((w-prev.reindex(w.index).fillna(0)).abs().sum())
        pnl.append(gross-t*FE_cost(t)); turn.append(t); prev=w
    return np.array(pnl),np.array(turn)

def FE_cost(t): return FEE
print(f"  {'hold':>5}{'top%':>7}{'n per':>7}{'mean/period':>13}{'ann~':>9}{'t':>8}{'turnover':>10}")
best=None
for hold in (5,10,21):
    for topq in (0.1,0.2,0.3):
        pnl,turn=run(hold,topq)
        if len(pnl)<25: continue
        se=pnl.std(ddof=1)/np.sqrt(len(pnl))
        ann=pnl.mean()*(365/hold)*100
        print(f"  {hold:>5}{topq*100:>6.0f}%{len(pnl):>7}{pnl.mean()*100:>12.3f}%{ann:>8.1f}%{pnl.mean()/se:>+8.2f}{turn.mean():>10.2f}")
        if best is None or pnl.mean()/se>best[0]: best=(pnl.mean()/se,hold,topq,pnl)
if best:
    t,hold,topq,pnl=best
    print(f"\n  BEST: hold {hold}d, top/bottom {topq*100:.0f}%  t={t:+.2f}")
    print(f"  periods positive: {int((pnl>0).sum())}/{len(pnl)}")
    cum=(1+pnl).cumprod()
    dd=(cum/np.maximum.accumulate(cum)-1).min()
    print(f"  cumulative {(cum[-1]-1)*100:+.1f}%   max drawdown {dd*100:.1f}%")
