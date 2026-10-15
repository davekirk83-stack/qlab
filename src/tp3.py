"""Runner gets its own target(s) instead of trailing open-ended."""
import numpy as np, pandas as pd
import core as C, levels as LV
from run10 import load_universe, atr, est_cost
PANEL=load_universe(); COSTS={s:est_cost(d) for s,d in PANEL.items()}

def trade(df,entries,cost,stop_atr=1.0,tp1_r=1.0,tp2_r=3.0,tp3_mode='trail',
          tp3_r=6.0,trail_atr=4.0,max_bars=20,be=0.10):
    A=atr(df).values; H,L,Cl,O=df.high.values,df.low.values,df.close.values,df.open.values
    SL=df.low.rolling(10).min().values
    qh=df[['high']].resample('QE').max().shift(1).reindex(df.index,method='ffill').high.values
    lo50=df.low.rolling(50).min().values; hi50=df.high.rolling(50).max().values
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
        tp1,tp2=px+tp1_r*risk,px+tp2_r*risk
        if tp3_mode=='fixedR': tp3=px+tp3_r*risk
        elif tp3_mode=='fib262': tp3=lo50[i]+(hi50[i]-lo50[i])*2.618 if lo50[i]==lo50[i] else px+tp3_r*risk
        elif tp3_mode=='qtr_high': tp3=qh[i]*1.05 if qh[i]==qh[i] and qh[i]>px else px+tp3_r*risk
        else: tp3=None
        if tp3 is not None and (not(tp3==tp3) or tp3<=tp2): tp3=px+tp3_r*risk
        filled,pnl,peak,ex=0.0,0.0,px,None; cur=st
        for j in range(i+1,min(i+1+max_bars,len(df))):
            if L[j]<=cur: pnl+=(1-filled)*(cur/px-1); ex=j; break
            if filled<0.34 and H[j]>=tp1:
                pnl+=(1/3)*(tp1/px-1); filled=1/3; cur=max(cur,px+be*risk+cost*px)
            if filled<0.67 and H[j]>=tp2: pnl+=(1/3)*(tp2/px-1); filled=2/3
            if filled>=0.66:
                if tp3 is not None and H[j]>=tp3:
                    pnl+=(1-filled)*(tp3/px-1); ex=j; break
                tr=peak-trail_atr*a
                if L[j]<=tr and tr>cur: pnl+=(1-filled)*(tr/px-1); ex=j; break
            peak=max(peak,H[j])
        if ex is None:
            j=min(i+max_bars,len(df)-1); pnl+=(1-filled)*(Cl[j]/px-1); ex=j
        out.append((pnl-cost,ex-i)); last=ex
    return out

def run(fn,**kw):
    R,B=[],[]
    for s,df in PANEL.items():
        try:
            e=fn(df); e=pd.Series(np.nan_to_num(np.asarray(e,dtype=float)),index=df.index)
        except Exception: continue
        if e.sum()==0: continue
        for r,b in trade(df,e,COSTS[s],**kw): R.append(r); B.append(max(b,1))
    if len(R)<100: return None
    r=np.array(R); b=np.array(B); mb=float(b.mean()); exp=float(r.mean())
    return dict(n=len(r),exp=exp,bars=mb,ann=(1+exp)**(252/mb)-1,
                win=float((r>0).mean()),t=float(exp/(r.std()/np.sqrt(len(r)))))
