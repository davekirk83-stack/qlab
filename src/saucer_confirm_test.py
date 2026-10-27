"""Doc 145b: at AO saucer signals (bull and bear, direction-signed), which other indicators separate winners from losers?
15m bars, BTC and ETH, Oct 2021 - Oct 2026. Outcome: signed return over the next 16 bars (4h). Features split into quintiles;
a feature 'helps' only if the top-vs-bottom quintile gap has the same sign on BTC and ETH and in both halves."""
import pandas as pd, numpy as np
def load(f):
    d=pd.read_csv(f"data_15m/{f}.csv"); d["t"]=pd.to_datetime(d.iloc[:,0],utc=True); return d.set_index("t")[["open","high","low","close","volume"]].astype(float)
def feats(d):
    c=d.close; mp=(d.high+d.low)/2; ao=mp.rolling(5).mean()-mp.rolling(34).mean(); col=ao.diff()
    tr=pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean()
    e20,e50,e200=[c.ewm(span=s,adjust=False).mean() for s in (20,50,200)]
    dl=c.diff(); up=dl.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); rsi=100-100/(1+up/dn)
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); hist=macd-macd.ewm(span=9,adjust=False).mean()
    bbw=(4*c.rolling(20).std())/c.rolling(20).mean(); bbw=bbw/bbw.rolling(500).median()
    bull=(ao>0)&(ao.shift(1)>0)&(ao.shift(2)>0)&(col.shift(2)<0)&(col.shift(1)<0)&(col>0)
    bear=(ao<0)&(ao.shift(1)<0)&(ao.shift(2)<0)&(col.shift(2)>0)&(col.shift(1)>0)&(col<0)
    sgn=pd.Series(0,index=d.index); sgn[bull]=1; sgn[bear]=-1
    fwd=(c.shift(-16)/c-1)*sgn
    # break-of-signal-bar confirmation within next 4 bars (entry at the break level)
    hi,lo=d.high,d.low
    brk=pd.Series(np.nan,index=d.index)
    F=pd.DataFrame({"sgn":sgn,"fwd":fwd,
        "RSI (dir-adj)":np.where(sgn>=0,rsi,100-rsi),
        "MACD hist agrees (dir-adj, /ATR)":hist*sgn/atr,
        "distance from EMA20 (ATR, dir-adj)":(c-e20)*sgn/atr,
        "trend strength EMA20-50 (ATR, dir-adj)":(e20-e50)*sgn/atr,
        "above/below EMA200 (dir-adj, %)":(c/e200-1)*sgn*100,
        "volume vs 20-bar avg":d.volume/d.volume.rolling(20).mean(),
        "Bollinger width vs norm":bbw,
        "prior 4h move (dir-adj, %)":(c/c.shift(16)-1)*sgn*100,
        "AO size (ATR)":ao.abs()/atr,
        "hour UTC":d.index.hour})
    return F[sgn!=0].dropna()
rows=[]
res={}
for f in ("BTCUSD","ETHUSD"):
    F=feats(load(f)); half=F.index[len(F)//2]; res[f]=F
    base=F.fwd; print(f"{f}: n {len(F)} saucers, right direction after 4h {100*(base>0).mean():.1f}%, mean {base.mean()*100:+.3f}%")
out=[]
for col in [c for c in res["BTCUSD"].columns if c not in ("sgn","fwd")]:
    line=f"{col:40}"; signs=[]
    for f,F in res.items():
        for part,m in (("H1",F.index<F.index[len(F)//2]),("H2",F.index>=F.index[len(F)//2])):
            x=F[m]; q=pd.qcut(x[col].rank(method="first"),5,labels=False)
            g=x.groupby(q).fwd.apply(lambda s:(s>0).mean()*100)
            signs.append(np.sign(g.iloc[4]-g.iloc[0]))
        x=F; q=pd.qcut(x[col].rank(method="first"),5,labels=False); g=x.groupby(q).fwd.apply(lambda s:(s>0).mean()*100)
        line+=f" | {f[:3]} Q1..Q5 win% "+" ".join(f"{v:.0f}" for v in g.values)
    cons="CONSISTENT" if len(set(signs))==1 else "mixed"
    out.append(line+f" | {cons}")
print("\n".join(out))
