"""
WHY THE 15-MINUTE KELTNER BOOK LOST, AND WHETHER THE GEOMETRY FIXES IT.

THE DIAGNOSIS. Win rates of 63-67% with every cell still negative is a
small-wins / big-losses profile, and the geometry says exactly why:
  target = the mid   -> 2 ATR above the band
  stop   = band - 8 ATR -> 10 ATR below the target
65% x 2 ATR  -  35% x 8 ATR  =  +1.3 - 2.8  =  -1.5 ATR.  It cannot win.

Doc 66 found the WIDE STOP worked - but it found that on an HOURLY book with a
120-bar hold, where the mid has five days to travel toward price. I transplanted
the stop without the hold. Stop width and hold length are coupled, and a wide
stop on a short hold is not patience, it is just a bigger loss.

So the target is not allowed to be "the mid" by assumption any more. Here both
legs are swept in ATR units, independently, and the reward/risk of each cell is
printed next to its result so a geometrically impossible cell is visible as one.

Run on the best-performing base from keltner_intraday.py (eff<0.30, 4 rungs).
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import keltner_intraday as K

MAKER,TAKER,SLIP = K.MAKER,K.TAKER,K.SLIP
RNG = np.random.default_rng(777)


def play(C,H,L,i,stop,tgt,maxh,rungs=4):
    n=len(C); top=C[i]
    if stop>=top*0.9995 or tgt<=top: return None
    px=[top] if rungs==1 else list(np.linspace(top,stop*1.0015,rungs))
    w=np.arange(1,len(px)+1,dtype=float); w/=w.sum()
    filled=[]
    for q in range(i+1,min(i+1+maxh,n)):
        for k,(p,ww) in enumerate(zip(px,w)):
            if L[q]<=p and k not in [f[0] for f in filled]: filled.append((k,p,ww))
        if not filled: continue
        dep=sum(x for _,_,x in filled)
        e=(sum(p*x for _,p,x in filled)/dep)*(1+MAKER)
        if L[q]<=stop: return ((stop*(1-SLIP-TAKER))/e-1)*dep, dep
        if H[q]>=tgt:  return ((tgt*(1-MAKER))/e-1)*dep, dep
    if not filled: return 0.0,0.0
    dep=sum(x for _,_,x in filled)
    e=(sum(p*x for _,p,x in filled)/dep)*(1+MAKER)
    q=min(i+maxh,n-1)
    return ((C[q]*(1-MAKER))/e-1)*dep, dep


def run(data,t_atr,s_atr,maxh,eff_cut=0.30):
    real=[];ctrl=[];days=0.0
    for s,d in data.items():
        C,H,L=d.close.values,d.high.values,d.low.values
        n=len(C); a=K.atr_np(H,L,C)
        ema=pd.Series(C).ewm(span=20,adjust=False).mean().values
        lower=ema-2*a
        eff=K.efficiency(C); ok=eff<eff_cut
        trig=(C<=lower)&(np.roll(C,1)>np.roll(lower,1))&ok
        days+=(d.index[-1]-d.index[0]).total_seconds()/86400
        elig=np.flatnonzero(ok&np.isfinite(a)&(np.arange(n)>150))
        elig=elig[(elig>150)&(elig<n-maxh-2)]
        last=-10**9
        for i in np.flatnonzero(trig):
            if i<150 or i>n-maxh-2 or i-last<maxh: continue
            last=i
            r=play(C,H,L,i,C[i]-s_atr*a[i],C[i]+t_atr*a[i],maxh)
            if r is None: continue
            real.append(r[0])
            if len(elig):
                q=int(RNG.choice(elig))
                c=play(C,H,L,q,C[q]-s_atr*a[q],C[q]+t_atr*a[q],maxh)
                if c: ctrl.append(c[0])
    return np.array(real),np.array(ctrl),days/max(len(data),1)


if __name__=="__main__":
    D=K.load("/home/claude/qlab/data_1m")
    print(f"GEOMETRY SWEEP  {len(D)} symbols, 15min bars, eff<0.30, 4-rung ladder\n")
    print(f"{'tgt':>5}{'stop':>6}{'R:R':>6}{'hold':>6}{'n':>6}{'/mo':>6}"
          f"{'net%':>9}{'t':>7}{'ctrl%':>8}{'EDGE':>8}{'win%':>6}{'$/trd':>7}{'$/mo':>8}")
    cells=[]
    for t_atr in (0.5,1.0,2.0):
        for s_atr in (0.5,1.0,2.0,4.0):
            for maxh in (8,16,32):
                r,c,dd=run(D,t_atr,s_atr,maxh)
                if len(r)<120 or len(c)<120: continue
                mo=dd/30.44; per=len(r)/mo
                t=r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
                dol=r.mean()*K.STACK*K.LEV
                cells.append(dict(t_atr=t_atr,s_atr=s_atr,maxh=maxh,n=len(r),
                    per=per,mean=r.mean(),t=t,edge=r.mean()-c.mean(),dol=dol))
                print(f"{t_atr:>5.1f}{s_atr:>6.1f}{t_atr/s_atr:>6.2f}{maxh:>6}"
                      f"{len(r):>6}{per:>6.0f}{r.mean()*100:>+8.3f}%{t:>+7.2f}"
                      f"{c.mean()*100:>+7.3f}%{(r.mean()-c.mean())*100:>+7.3f}%"
                      f"{(r>0).mean()*100:>5.0f}%{dol:>7.2f}{dol*per:>8.0f}")
    pos=[x for x in cells if x["mean"]>0]
    beat=[x for x in cells if x["edge"]>0]
    tb=float(np.sqrt(2*np.log(max(len(cells),2))))
    print(f"\n  {len(pos)}/{len(cells)} net positive | {len(beat)}/{len(cells)} beat control"
          f" | corrected t bar: {tb:.2f}")
    if pos:
        b=max(pos,key=lambda x:x["mean"])
        print(f"  BEST: tgt {b['t_atr']}A stop {b['s_atr']}A hold {b['maxh']}b -> "
              f"{b['mean']*100:+.3f}%/trade t={b['t']:+.2f} edge {b['edge']*100:+.3f}% "
              f"{b['per']:.0f}/mo ${b['dol']*b['per']:.0f}/mo "
              f"{'CLEARS' if b['t']>=tb else 'BELOW'}")
