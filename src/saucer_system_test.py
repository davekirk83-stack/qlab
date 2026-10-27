"""Doc 145c: the saucer as Bill Williams / Skyrexio intend it — a trend system, not a fixed-horizon forecast.
Long only, 3h bars, BTC and ETH, Oct 2021 - Oct 2026. Rules (Skyrexio 'MultiLayer AO Saucer', TradingView):
 close > EMA100; Alligator/fractal trend = up (last up-fractal break above the teeth, after the last down-fractal break below);
 saucer: AO a1>a2<a3, all >0; buy stop 1 tick above the signal bar high, kept while AO keeps rising (moved to lower highs), cancelled if AO turns down;
 10% per entry, pyramid to 5; exit ALL when the trend flips down (close below the last down fractal while below the teeth). Costs 0.1% + 0.05% slippage per side.
Control: identical trend filter and exit, but entries at RANDOM bars inside the up-trend (same number of entries), 200 draws."""
import pandas as pd, numpy as np, sys
COST=0.0015
def load(f):
    d=pd.read_csv(f"data_15m/{f}.csv"); d["t"]=pd.to_datetime(d.iloc[:,0],utc=True); d=d.set_index("t")[["open","high","low","close"]].astype(float)
    return d.resample("3h").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
def smma(x,n): return x.ewm(alpha=1/n,adjust=False).mean()
def build(d):
    mp=(d.high+d.low)/2; ao=(mp.rolling(5).mean()-mp.rolling(34).mean()).values
    teeth=smma(mp,8).shift(5).values; ema=d.close.ewm(span=100,adjust=False).mean().values
    H,L,C=d.high.values,d.low.values,d.close.values; n=len(C)
    upf=np.full(n,np.nan); dnf=np.full(n,np.nan); lu=ld=np.nan
    for i in range(4,n):   # fractal at i-2 confirmed at i
        k=i-2
        if H[k]==max(H[k-2:k+3]) : lu=H[k]
        if L[k]==min(L[k-2:k+3]) : ld=L[k]
        upf[i]=lu; dnf[i]=ld
    state=np.zeros(n,int); s=0
    for i in range(1,n):
        if np.isfinite(upf[i-1]) and C[i]>upf[i-1] and upf[i-1]>teeth[i]: s=1
        elif np.isfinite(dnf[i-1]) and C[i]<dnf[i-1] and dnf[i-1]<teeth[i]: s=-1
        state[i]=s
    return ao,ema,state,H,L,C
def run(d, entry_mode="saucer", rng=None, n_target=None):
    ao,ema,state,H,L,C=build(d); n=len(C); pos=[]; trades=[]; pend=None; entries=0
    cand=[i for i in range(40,n-1) if state[i]==1 and C[i]>ema[i]]
    rnd=set(rng.choice(cand,size=min(n_target,len(cand)),replace=False)) if entry_mode=="random" else set()
    for i in range(40,n):
        if state[i]==-1 and pos:          # exit all at close
            for p in pos: trades.append((C[i]*(1-COST))/p-1)
            pos=[]; pend=None
        if pend is not None and state[i]==1:
            if H[i]>pend and len(pos)<5: pos.append(max(pend,C[i-1])*(1+COST)); pend=None; entries+=1
            elif ao[i]<ao[i-1]: pend=None
            elif H[i]<pend: pend=H[i]     # move to lower highs while AO rising
        if state[i]!=1 or C[i]<=ema[i]: continue
        if entry_mode=="saucer":
            if ao[i]>0 and ao[i-1]>0 and ao[i-2]>0 and ao[i-2]>ao[i-1] and ao[i]>ao[i-1]: pend=H[i]
        elif i in rnd and len(pos)<5: pos.append(C[i]*(1+COST)); entries+=1
    for p in pos: trades.append(C[-1]/p-1)
    return np.array(trades)
def summ(t):
    w=t[t>0].sum(); l=-t[t<0].sum()
    return dict(n=len(t), win=(t>0).mean()*100 if len(t) else 0, pf=w/l if l>0 else np.inf, mean=t.mean()*100 if len(t) else 0, tot=t.sum()*10)  # tot = % of capital at 10% per trade
out=[]
for f in ("BTCUSD","ETHUSD"):
    d=load(f); half=d.index[len(d)//2]
    for lab,dd in (("all",d),("H1",d[d.index<half]),("H2",d[d.index>=half])):
        t=run(dd); s=summ(t)
        rs=[summ(run(dd,"random",np.random.default_rng(k),s["n"])) for k in range(200)]
        pf_r=np.median([r["pf"] for r in rs if np.isfinite(r["pf"])]); tot_r=np.array([r["tot"] for r in rs])
        bh=(dd.close.iloc[-1]/dd.close.iloc[40]-1)*100
        out.append(f"{f} {lab:3} {dd.index[0].date()}→{dd.index[-1].date()} | saucer n{s['n']:3} win {s['win']:.0f}% PF {s['pf']:.2f} mean/trade {s['mean']:+.2f}% total {s['tot']:+.1f}% of capital | random entries same filter: median PF {pf_r:.2f}, total median {np.median(tot_r):+.1f}%, saucer beats {100*(tot_r<s['tot']).mean():.0f}% of draws | buy&hold {bh:+.0f}%")
txt="\n".join(out); print(txt); open("runs/saucer_system_test.txt","w").write(txt+"\n")
