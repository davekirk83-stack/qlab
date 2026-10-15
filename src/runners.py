"""
LETTING RUNNERS RUN.

DK: "Runners being left."

Correct criticism. The book takes profit at 0.5 ATR, which is tiny. Every
large move it catches, it exits near the beginning of. The question is whether
that is leaving money behind or whether the small target is exactly what makes
the 83% win rate possible.

FIVE EXITS COMPARED on identical entries:
  fixed        close everything at +0.5 ATR            (what we do now)
  scale        half at +0.5 ATR, half trails by 1 ATR from the high
  scale2       half at +0.5 ATR, half trails by 2 ATR
  trail_only   no fixed target, trail by 1 ATR from the high
  wide         single target at +2 ATR

Judged on the EQUITY CURVE, not per-trade averages - finding 99's lesson.
Same gate, same 40 slots at 3x, same costs.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import system_on_history as SYS, portfolio as PF, gate_daily as G

MAKER,TAKER,SLIP=SYS.MAKER,SYS.TAKER,SYS.SLIP
S_ATR,KBAND,EFF,HOLD=3.0,2.0,0.30,16

def exits(C,H,L,i,a,mode):
    n=len(C); e=C[i]*(1+MAKER); stop=C[i]-S_ATR*a
    t1=C[i]+0.5*a; tw=C[i]+2.0*a
    half=False; pnl=0.0; peak=C[i]
    trail_mult={"scale":1.0,"scale2":2.0,"trail_only":1.0}.get(mode)
    for q in range(i+1,min(i+1+HOLD,n)):
        peak=max(peak,H[q])
        if mode=="fixed":
            if L[q]<=stop: return (stop*(1-SLIP-TAKER))/e-1,q-i
            if H[q]>=t1:   return (t1*(1-MAKER))/e-1,q-i
        elif mode=="wide":
            if L[q]<=stop: return (stop*(1-SLIP-TAKER))/e-1,q-i
            if H[q]>=tw:   return (tw*(1-MAKER))/e-1,q-i
        elif mode=="trail_only":
            tr=peak-trail_mult*a
            if L[q]<=max(stop,tr):
                px=max(stop,tr); return (px*(1-SLIP-TAKER))/e-1,q-i
        else:  # scale / scale2
            if not half:
                if L[q]<=stop: return (stop*(1-SLIP-TAKER))/e-1,q-i
                if H[q]>=t1:
                    pnl+=0.5*((t1*(1-MAKER))/e-1); half=True; peak=H[q]; continue
            else:
                tr=peak-trail_mult*a
                if L[q]<=tr:
                    return pnl+0.5*((tr*(1-SLIP-TAKER))/e-1),q-i
    q=min(i+HOLD,n-1); rest=1.0 if not half else 0.5
    return pnl+rest*((C[q]*(1-MAKER))/e-1),q-i

def signals(data,mode):
    rows=[]
    for s,d in data.items():
        C,H,L=d.close.values,d.high.values,d.low.values
        n=len(C); A=SYS.atr_np(H,L,C)
        ema=pd.Series(C).ewm(span=20,adjust=False).mean().values
        lower=ema-KBAND*A; ok=SYS.efficiency(C)<EFF
        trig=(C<=lower)&(np.roll(C,1)>np.roll(lower,1))&ok
        last=-10**9
        for i in np.flatnonzero(trig):
            if i<120 or i>n-HOLD-2 or i-last<HOLD: continue
            last=i
            a=A[i]
            if not np.isfinite(a) or a<=0 or C[i]-S_ATR*a<=0: continue
            r,bars=exits(C,H,L,i,a,mode)
            rows.append((s,d.index[i],d.index[min(i+bars,n-1)],r))
    return pd.DataFrame(rows,columns=["sym","entry","exit","ret"]).sort_values("entry").reset_index(drop=True)

if __name__=="__main__":
    data=SYS.load(); M=G.market_series(data)
    print(f"{'exit rule':<14}{'per trade':>11}{'win%':>7}{'final $':>10}{'CAGR':>8}"
          f"{'maxDD':>9}{'Sharpe':>8}{'losing yrs':>12}")
    for mode in ("fixed","scale","scale2","trail_only","wide"):
        S=signals(data,mode)
        kept=S[S.entry.map(lambda d: M["mkt_200"].get(d,np.nan)==1).fillna(False)].reset_index(drop=True)
        r=PF.simulate(kept,40,3)
        if r is None: print(f"{mode:<14}  wiped out"); continue
        E=r["curve"]; yrs={y:(g.iloc[-1]/g.iloc[0]-1) for y,g in E.groupby(E.index.year) if len(g)>30}
        neg=sum(1 for v in yrs.values() if v<0)
        print(f"{mode:<14}{kept.ret.mean()*100:>+10.3f}%{(kept.ret>0).mean()*100:>6.0f}%"
              f"{r['final']:>10,.0f}{r['cagr']*100:>7.1f}%{r['dd']*100:>8.1f}%"
              f"{r['sharpe']:>8.2f}{neg:>8}/{len(yrs)}")
