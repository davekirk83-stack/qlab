"""
THE TWO TESTS THAT HAVE TO FAIL BEFORE THE 15-MINUTE KELTNER LINE IS CLOSED.

Two sweeps (72 cells) have now found zero positive cells, with the real trade
tracking its time-matched control to within +-0.02% in every one. That says the
entry carries no information. But it would be sloppy to close the line on that
alone, because both sweeps shared two assumptions:

  A. LONGS ONLY, at the lower band. Crypto is not symmetric and the short side
     has never been tested here.
  B. UNCONDITIONED. Every edge this programme actually owns came from
     conditioning, not from a raw trigger. close_in_bar scored +0.004 standalone
     and TRIPLED the cascade's edge as a filter (doc 67). Judging a trigger
     unconditioned is the exact mistake doc 67 warned about.

So: the short side, and the full element library as a conditioner on the long
side. If neither finds anything, the line is dead on evidence rather than on
one framing of it.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
import keltner_intraday as K
import elements as EL
import elements_mktadv as MA

MAKER,TAKER,SLIP=K.MAKER,K.TAKER,K.SLIP
RNG=np.random.default_rng(4242)


def play_dir(C,H,L,i,stop,tgt,maxh,long=True):
    n=len(C); e0=C[i]
    for q in range(i+1,min(i+1+maxh,n)):
        if long:
            if L[q]<=stop: return (stop*(1-SLIP-TAKER))/(e0*(1+MAKER))-1
            if H[q]>=tgt:  return (tgt*(1-MAKER))/(e0*(1+MAKER))-1
        else:
            if H[q]>=stop: return 1-(stop*(1+SLIP+TAKER))/(e0*(1-MAKER))
            if L[q]<=tgt:  return 1-(tgt*(1+MAKER))/(e0*(1-MAKER))
    q=min(i+maxh,n-1)
    return ((C[q]*(1-MAKER))/(e0*(1+MAKER))-1) if long else (1-(C[q]*(1+MAKER))/(e0*(1-MAKER)))


def collect(data, long=True, t_atr=1.0, s_atr=2.0, maxh=16, eff_cut=0.30):
    recs=[]
    for s,d in data.items():
        C,H,L=d.close.values,d.high.values,d.low.values
        n=len(C); a=K.atr_np(H,L,C)
        ema=pd.Series(C).ewm(span=20,adjust=False).mean().values
        lower=ema-2*a; upper=ema+2*a
        ok=K.efficiency(C)<eff_cut
        trig=((C<=lower)&(np.roll(C,1)>np.roll(lower,1))&ok) if long else \
             ((C>=upper)&(np.roll(C,1)<np.roll(upper,1))&ok)
        F=EL.build(d); M=MA.build(d)
        F.update(M)
        elig=np.flatnonzero(ok&np.isfinite(a)&(np.arange(n)>200))
        elig=elig[(elig>200)&(elig<n-maxh-2)]
        last=-10**9
        for i in np.flatnonzero(trig):
            if i<200 or i>n-maxh-2 or i-last<maxh: continue
            last=i
            st=C[i]-s_atr*a[i] if long else C[i]+s_atr*a[i]
            tg=C[i]+t_atr*a[i] if long else C[i]-t_atr*a[i]
            r=play_dir(C,H,L,i,st,tg,maxh,long)
            rec={"sym":s,"ret":r}
            for k,v in F.items():
                try: rec[k]=float(v[i])
                except Exception: rec[k]=np.nan
            recs.append(rec)
            if len(elig):
                q=int(RNG.choice(elig))
                stq=C[q]-s_atr*a[q] if long else C[q]+s_atr*a[q]
                tgq=C[q]+t_atr*a[q] if long else C[q]-t_atr*a[q]
                recs.append({"sym":s,"ret":play_dir(C,H,L,q,stq,tgq,maxh,long),
                             "__ctrl":1})
    return pd.DataFrame(recs)


if __name__=="__main__":
    D=K.load("/home/claude/qlab/data_1m")

    print("A. THE SHORT SIDE — upper-band touch, same geometry sweep\n")
    print(f"{'tgt':>5}{'stop':>6}{'hold':>6}{'n':>6}{'net%':>9}{'t':>7}{'ctrl%':>8}{'EDGE':>8}{'win%':>6}")
    best=None
    for t_atr in (0.5,1.0,2.0):
        for s_atr in (1.0,2.0,4.0):
            for maxh in (8,16,32):
                T=collect(D,long=False,t_atr=t_atr,s_atr=s_atr,maxh=maxh)
                r=T[T.get("__ctrl",pd.Series(np.nan,index=T.index)).isna()].ret.dropna()
                c=T[T.get("__ctrl",pd.Series(np.nan,index=T.index))==1].ret.dropna()
                if len(r)<120 or len(c)<120: continue
                t=r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
                print(f"{t_atr:>5.1f}{s_atr:>6.1f}{maxh:>6}{len(r):>6}"
                      f"{r.mean()*100:>+8.3f}%{t:>+7.2f}{c.mean()*100:>+7.3f}%"
                      f"{(r.mean()-c.mean())*100:>+7.3f}%{(r>0).mean()*100:>5.0f}%")
                if best is None or r.mean()>best[0]: best=(r.mean(),t_atr,s_atr,maxh,t)
    if best: print(f"\n  best short cell {best[0]*100:+.3f}%/trade t={best[4]:+.2f}")

    print("\n\nB. CONDITIONING — can any element separate winners on the long side?\n")
    T=collect(D,long=True,t_atr=1.0,s_atr=2.0,maxh=16)
    R=T[T.get("__ctrl",pd.Series(np.nan,index=T.index)).isna()].copy()
    print(f"  {len(R)} long trades, base {R.ret.mean()*100:+.3f}%/trade")
    cols=[c for c in R.columns if c not in ("sym","ret","__ctrl")]
    out=[]
    for c in cols:
        x=R[c]
        if x.notna().sum()<500 or x.nunique()<5: continue
        q=pd.qcut(x,5,labels=False,duplicates="drop")
        if q.nunique()<5: continue
        g=R.groupby(q).ret
        spread=g.mean().iloc[-1]-g.mean().iloc[0]
        top=g.mean().iloc[-1]; bot=g.mean().iloc[0]
        ic=stats.spearmanr(x[x.notna()],R.ret[x.notna()]).statistic
        se=np.sqrt(g.var().iloc[-1]/g.count().iloc[-1]+g.var().iloc[0]/g.count().iloc[0])
        out.append((c,spread,spread/se,top,bot,ic))
    out.sort(key=lambda z:-abs(z[2]))
    print(f"  {'element':<22}{'Q5-Q1':>9}{'t':>7}{'Q5 ret':>9}{'Q1 ret':>9}{'IC':>8}")
    for c,sp,t,tp,bt,ic in out[:14]:
        print(f"  {c:<22}{sp*100:>+8.3f}%{t:>+7.2f}{tp*100:>+8.3f}%{bt*100:>+8.3f}%{ic:>+8.4f}")
    n_best=sum(1 for o in out if o[3]>0)
    print(f"\n  elements tested: {len(out)} | with a PROFITABLE top quintile: {n_best}")
    print(f"  multiple-testing bar for {len(out)} tests: t={np.sqrt(2*np.log(max(len(out),2))):.2f}")
