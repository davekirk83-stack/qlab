"""
DK's ACTUAL SPEC: 5-MINUTE OSCILLATIONS IN QUIET PERIODS.

"you're talking about 4 hour oscillations - this is far too long. I'm talking
 about 5 minute or 5 minute oscillations during quiet periods"

Correct - on 15m bars my best cell was 17-32 bars held, which is four to eight
hours. That is a swing. DK means the whole cycle completing in minutes: price
ticking between tight bands while nothing is happening.

So: 1-minute and 5-minute bars, short Keltner lookback, an explicit QUIET
filter (realised volatility in its own lower percentiles), ladder in at and
below the lower band, scaled exit at mid / band / beyond, and holds capped in
MINUTES rather than hours.

Maker fees throughout (1.5bp a side) because this is a resting-order strategy;
taker plus slippage only on the forced exit.
"""
import warnings; warnings.filterwarnings("ignore")
import os,glob
import numpy as np, pandas as pd

MK,TAKER,SLIP=1.5/10000,4.5/10000,5/10000
BID=[(0.15,0.30),(0.25,0.05),(0.30,-0.25),(0.30,-0.55)]
ASK=[(0.4,"mid"),(0.4,0.0),(1.0,0.35)]

def load(tf):
    out={}
    for folder in ("/home/claude/qlab/data_1m","/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s=os.path.basename(f)[:-4]
            if s in out: continue
            d=pd.read_csv(f); d.index=pd.to_datetime(d.t,unit="ms",utc=True)
            b=d[["open","high","low","close","volume"]]
            if tf!="1min":
                b=b.resample(tf).agg(open=("open","first"),high=("high","max"),
                    low=("low","min"),close=("close","last"),volume=("volume","sum")).dropna()
            if len(b)>5000: out[s]=b
    return out

def atr_np(H,L,C,n):
    pc=np.roll(C,1); pc[0]=C[0]
    tr=np.maximum(H-L,np.maximum(np.abs(H-pc),np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values

def work(d,ema_n,atr_n,quiet_q,max_bars,band=2.0):
    C,H,L=d.close.values,d.high.values,d.low.values
    n=len(C); a=atr_np(H,L,C,atr_n)
    ema=pd.Series(C).ewm(span=ema_n,adjust=False).mean().values
    lo_b=ema-band*a; hi_b=ema+band*a
    rv=pd.Series(C).pct_change().rolling(60).std().values
    thr=pd.Series(rv).rolling(2000,min_periods=500).quantile(quiet_q).values
    out=[]; inv=[]; opened=None; opened_i=0; sold=set()
    for i in range(200,n-1):
        if not np.isfinite(a[i]) or a[i]<=0 or not np.isfinite(thr[i]): continue
        quiet = rv[i] < thr[i]
        broke = C[i]<lo_b[i]-1.5*a[i] or C[i]>hi_b[i]+1.5*a[i]
        if inv and (i-opened_i>=max_bars or broke or not quiet):
            sz=sum(s for _,s in inv); cost=sum(p*s for p,s in inv)/sz
            out.append(((C[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, i-opened_i,
                        "break" if broke else "timeout"))
            inv=[]; opened=None; sold=set(); continue
        if not quiet: continue
        if inv:
            for k,(frac,lvl) in enumerate(ASK):
                if k in sold: continue
                tgt=ema[i] if lvl=="mid" else hi_b[i]+lvl*a[i]
                if H[i]>=tgt and inv:
                    sz=sum(s for _,s in inv); sell=min(sz*frac,sz)
                    cost=sum(p*s for p,s in inv)/sz
                    out.append((((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), i-opened_i,"sold"))
                    sold.add(k)
                    inv=[(p,s*(1-sell/sz)) for p,s in inv]; inv=[(p,s) for p,s in inv if s>1e-9]
                    if not inv: opened=None; sold=set()
        held=sum(s for _,s in inv)
        if held<1.0:
            for frac,off in BID:
                p=lo_b[i]+off*a[i]
                if L[i]<p and held+frac<=1.0+1e-9:
                    inv.append((p,frac)); held+=frac
                    if opened is None: opened=d.index[i]; opened_i=i
    return out

if __name__=="__main__":
    for tf,emas,atrs,caps in (("5min",(20,40),(14,30),(6,12,24,48)),
                              ("15min",(20,40),(14,30),(4,8,16,32))):
        data=load(tf)
        print(f"\n{'='*96}\n{tf} BARS — {len(data)} symbols, quiet-period filter\n")
        print(f"  {'ema':>5}{'atr':>5}{'quiet':>7}{'cap':>6}{'n':>8}{'per trade':>12}"
              f"{'t':>8}{'win':>6}{'med held':>10}{'breaks':>8}{'worst':>9}")
        for ema_n in emas:
            for atr_n in atrs:
                for q in (0.3,):
                    for cap in caps:
                        res=[]
                        for s,d in data.items():
                            res+=work(d,ema_n,atr_n,q,cap)
                        if len(res)<200: continue
                        R=pd.DataFrame(res,columns=["ret","bars","how"])
                        m=R.ret.mean(); t=m/(R.ret.std(ddof=1)/np.sqrt(len(R)))
                        brk=R[R.how!="sold"]
                        mins=cap*{"1min":1,"5min":5,"15min":15}[tf]
                        print(f"  {ema_n:>5}{atr_n:>5}{q:>7.1f}{cap:>4}b{mins:>3}m"
                              f"{len(R):>8}{m*100:>+11.4f}%{t:>+8.2f}"
                              f"{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>10.0f}"
                              f"{len(brk)/len(R)*100:>7.0f}%{R.ret.min()*100:>+8.1f}%")
