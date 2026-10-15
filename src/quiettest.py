"""
IS THE QUIET FILTER HELPING OR HURTING?

Confounded: the filtered 15min run scored +0.224%/trade and the unfiltered
earlier version +0.361%, but the cap differed too (32 vs 48 bars). Isolating
it - same bars, same bands, same ladder, same cap, only the filter changes.

Swept across quiet thresholds so "how quiet" is answered too, not just
"filter or no filter".
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import fastrange as FR

def work(d, quiet_q, max_bars, ema_n=20, atr_n=14, band=2.0):
    C,H,L=d.close.values,d.high.values,d.low.values
    n=len(C); a=FR.atr_np(H,L,C,atr_n)
    ema=pd.Series(C).ewm(span=ema_n,adjust=False).mean().values
    lo_b=ema-band*a; hi_b=ema+band*a
    if quiet_q is None:
        quiet_all=np.ones(n,bool)
    else:
        rv=pd.Series(C).pct_change().rolling(60).std().values
        thr=pd.Series(rv).rolling(2000,min_periods=500).quantile(quiet_q).values
        quiet_all=np.where(np.isfinite(thr), rv<thr, False)
    out=[];inv=[];opened=None;opened_i=0;sold=set()
    for i in range(200,n-1):
        if not np.isfinite(a[i]) or a[i]<=0: continue
        quiet=bool(quiet_all[i])
        broke=C[i]<lo_b[i]-1.5*a[i] or C[i]>hi_b[i]+1.5*a[i]
        if inv and (i-opened_i>=max_bars or broke or not quiet):
            sz=sum(s for _,s in inv); cost=sum(p*s for p,s in inv)/sz
            out.append(((C[i]*(1-FR.SLIP-FR.TAKER))/(cost*(1+FR.MK))-1,i-opened_i))
            inv=[];opened=None;sold=set();continue
        if not quiet: continue
        if inv:
            for k,(frac,lvl) in enumerate(FR.ASK):
                if k in sold: continue
                tgt=ema[i] if lvl=="mid" else hi_b[i]+lvl*a[i]
                if H[i]>=tgt and inv:
                    sz=sum(s for _,s in inv);sell=min(sz*frac,sz)
                    cost=sum(p*s for p,s in inv)/sz
                    out.append((((tgt*(1-FR.MK))/(cost*(1+FR.MK))-1)*(sell/sz),i-opened_i))
                    sold.add(k)
                    inv=[(p,s*(1-sell/sz)) for p,s in inv];inv=[(p,s) for p,s in inv if s>1e-9]
                    if not inv: opened=None;sold=set()
        held=sum(s for _,s in inv)
        if held<1.0:
            for frac,off in FR.BID:
                p=lo_b[i]+off*a[i]
                if L[i]<p and held+frac<=1.0+1e-9:
                    inv.append((p,frac));held+=frac
                    if opened is None: opened=d.index[i];opened_i=i
    return out

if __name__=="__main__":
    data=FR.load("15min")
    print(f"15min bars, {len(data)} symbols. ema20/atr14, 4 bids in, scaled exit.")
    print("Only the quiet filter changes.\n")
    print(f"  {'quiet filter':<24}{'cap':>6}{'n':>8}{'per trade':>12}{'t':>8}"
          f"{'win':>6}{'worst':>9}{'P1 tail':>10}")
    for q,lbl in ((None,"OFF - trade always"),(0.5,"below median vol"),
                  (0.3,"below 30th pct"),(0.15,"below 15th pct")):
        for cap in (32,48,96):
            res=[]
            for s,d in data.items(): res+=work(d,q,cap)
            if len(res)<200: continue
            R=pd.DataFrame(res,columns=["ret","bars"])
            m=R.ret.mean(); t=m/(R.ret.std(ddof=1)/np.sqrt(len(R)))
            print(f"  {lbl:<24}{cap:>6}{len(R):>8}{m*100:>+11.4f}%{t:>+8.2f}"
                  f"{(R.ret>0).mean()*100:>5.0f}%{R.ret.min()*100:>+8.1f}%"
                  f"{R.ret.quantile(0.01)*100:>+9.2f}%")
        print()
