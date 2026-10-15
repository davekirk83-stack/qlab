"""
THE RANGE-MAKER ON AN EQUITY CURVE.

+0.388%/trade at t=+53.7 is a per-trade mean and those have caught me out
twice today. This model also HOLDS INVENTORY, so capital is tied up in a way
the simple books never were - concurrency will bind much harder.

Config fixed from the sweep: 4 bids in, scaled exit (mid / band / beyond),
48-bar cap on residual inventory. Only slots and leverage vary.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import rangemaker as RM

BID=[(0.15,0.30),(0.25,0.05),(0.30,-0.25),(0.30,-0.55)]
ASK=[(0.4,"mid"),(0.4,0.0),(1.0,0.35)]
START=2000.0

def events(data, max_bars):
    rows=[]
    for s,d in data.items():
        if len(d)<800: continue
        for o,c,r,bars,how in RM.work_range(d,BID,ASK,1.0,True,max_bars=max_bars):
            rows.append((s,o,c,r))
    return pd.DataFrame(rows,columns=["sym","entry","exit","ret"]).dropna().sort_values("entry").reset_index(drop=True)

def sim(S,maxpos,lev):
    eq=START; op=[]; curve=[]; taken=dropped=0
    times=pd.DatetimeIndex(sorted(set(S.entry)|set(S.exit)))
    ent=S.groupby(S.entry).groups
    for t in times:
        still=[]
        for ex,m,r in op:
            if ex<=t: eq+=max(r*lev*m,-m)
            else: still.append((ex,m,r))
        op=still
        if t in ent:
            for i in ent[t]:
                row=S.loc[i]
                if len(op)>=maxpos or eq<=0: dropped+=1; continue
                op.append((row.exit,eq/maxpos,row.ret)); taken+=1
        curve.append((t,eq))
        if eq<=0: break
    E=pd.Series(dict(curve)).astype(float)
    if len(E)<50 or E.iloc[-1]<=0: return None
    yrs=(E.index[-1]-E.index[0]).days/365.25
    r=E.pct_change().replace([np.inf,-np.inf],np.nan).dropna()
    return dict(final=E.iloc[-1],cagr=(E.iloc[-1]/START)**(1/max(yrs,.1))-1,
        dd=(E/E.cummax()-1).min(),
        sharpe=r.mean()/r.std()*np.sqrt(len(E)/max(yrs,.1)) if r.std()>0 else np.nan,
        taken=taken,dropped=dropped,permo=taken/max(yrs*12,.1),curve=E)

if __name__=="__main__":
    data=RM.load()
    for mb,lbl in ((48,"48-bar cap on leftovers"),(None,"no cap")):
        S=events(data,mb)
        print(f"\n{lbl} — {len(S):,} position-events, mean {S.ret.mean()*100:+.4f}%")
        print(f"  {'slots':>6}{'lev':>5}{'final $':>11}{'CAGR':>9}{'maxDD':>9}"
              f"{'Sharpe':>8}{'/mo':>8}{'dropped':>9}")
        for mp in (10,20,40):
            for lv in (1,2,3):
                r=sim(S,mp,lv)
                if r is None: print(f"  {mp:>6}{lv:>5}   wiped out"); continue
                print(f"  {mp:>6}{lv:>5}{r['final']:>11,.0f}{r['cagr']*100:>8.1f}%"
                      f"{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}{r['permo']:>8.0f}"
                      f"{r['dropped']:>9}")
