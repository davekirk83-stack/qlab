"""Meat vs runner: separate time limits. Meat exits fast; runner left alone."""
import numpy as np, pandas as pd
import core as C, levels as LV
from run10 import load_universe, atr, est_cost
PANEL=load_universe(); COSTS={s:est_cost(d) for s,d in PANEL.items()}

def trade(df,entries,cost,stop_atr=1.0,tp1_r=1.0,tp2_r=3.0,tp3_r=15.0,
          trail_atr=4.0,meat_bars=5,runner_bars=40,be=0.10,diag=False):
    A=atr(df).values; H,L,Cl,O=df.high.values,df.low.values,df.close.values,df.open.values
    SL=df.low.rolling(10).min().values
    idx=np.flatnonzero(np.nan_to_num(entries.values)>0); out=[]; last=-1
    for i in idx:
        if i<=last or i+1>=len(df): continue
        a=A[i]
        if not(a==a) or a<=0: continue
        px=O[i+1]
        if not(px==px) or px<=0: continue
        st=max(px-stop_atr*a, SL[i]*0.995 if SL[i]==SL[i] else px-stop_atr*a)
        if st>=px: st=px-stop_atr*a
        risk=px-st
        if risk<=0: continue
        tp1,tp2,tp3=px+tp1_r*risk,px+tp2_r*risk,px+tp3_r*risk
        filled,pnl,peak,ex=0.0,0.0,px,None; cur=st
        t1_bar=t2_bar=None
        for j in range(i+1,min(i+1+runner_bars,len(df))):
            k=j-i
            if L[j]<=cur: pnl+=(1-filled)*(cur/px-1); ex=j; break
            if filled<0.34 and H[j]>=tp1:
                pnl+=(1/3)*(tp1/px-1); filled=1/3; t1_bar=k
                cur=max(cur,px+be*risk+cost*px)
            if filled<0.67 and H[j]>=tp2:
                pnl+=(1/3)*(tp2/px-1); filled=2/3; t2_bar=k
            # MEAT TIME STOP: if the first two thirds have not completed by
            # meat_bars, close whatever of them remains at market and let the
            # runner continue on its own leash.
            if k>=meat_bars and filled<0.66:
                close=(2/3)-filled if filled<(2/3) else 0.0
                if close>0: pnl+=close*(Cl[j]/px-1); filled=2/3
            if filled>=0.66:
                if H[j]>=tp3: pnl+=(1-filled)*(tp3/px-1); ex=j; break
                tr=peak-trail_atr*a
                if L[j]<=tr and tr>cur: pnl+=(1-filled)*(tr/px-1); ex=j; break
            peak=max(peak,H[j])
        if ex is None:
            j=min(i+runner_bars,len(df)-1); pnl+=(1-filled)*(Cl[j]/px-1); ex=j
        out.append((pnl-cost,ex-i,t1_bar,t2_bar)); last=ex
    return out

def run(fn,**kw):
    R,B,T1,T2=[],[],[],[]
    for s,df in PANEL.items():
        try:
            e=fn(df); e=pd.Series(np.nan_to_num(np.asarray(e,dtype=float)),index=df.index)
        except Exception: continue
        if e.sum()==0: continue
        for r,b,t1,t2 in trade(df,e,COSTS[s],**kw):
            R.append(r); B.append(max(b,1))
            if t1: T1.append(t1)
            if t2: T2.append(t2)
    if len(R)<100: return None
    r=np.array(R); b=np.array(B); mb=float(b.mean()); exp=float(r.mean())
    return dict(n=len(r),exp=exp,bars=mb,ann=(1+exp)**(252/mb)-1,win=float((r>0).mean()),
                tp1_hit=len(T1)/len(R),tp1_med=float(np.median(T1)) if T1 else 0,
                tp1_1d=float(np.mean(np.array(T1)<=1)) if T1 else 0,
                tp1_5d=float(np.mean(np.array(T1)<=5)) if T1 else 0,
                tp2_hit=len(T2)/len(R))
