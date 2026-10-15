"""
WHICH TRADE TYPE WORKS IN WHICH SESSION AND VOLATILITY REGIME?

Two opposite trade archetypes, tested in every cell:
  MOMENTUM / BREAKOUT : buy a push above the recent high  (trend continuation)
  FADE / MEAN REVERT  : buy a push below the recent low   (counter-trend)
Both on 15-min bars, short holds, symmetric exits, costs applied.

Cells: 3 sessions x 3 volatility regimes (low/mid/high, measured on a trailing
window known BEFORE the bar, so no lookahead).
"""
import os, numpy as np, pandas as pd
D="/home/claude/qlab/data_15m"
SY=sorted(f[:-4] for f in os.listdir(D) if f.endswith(".csv"))
COST=0.0006
SESS={"ASIA":(0,7),"LONDON":(7,13),"US":(13,21)}

def load(s):
    d=pd.read_csv(f"{D}/{s}.csv",parse_dates=["date"]).set_index("date").sort_index()
    d=d[~d.index.duplicated()]
    d["ret"]=d.close.pct_change()
    d["rv"]=d.ret.rolling(96).std()                 # 1 day of 15-min bars
    d["rv_pct"]=d.rv.rolling(96*20).rank(pct=True)  # vs the last 20 days
    d["hi20"]=d.high.rolling(20).max().shift(1)
    d["lo20"]=d.low.rolling(20).min().shift(1)
    d["atr"]=(d.high-d.low).rolling(20).mean()
    return d.dropna()

def test(d, kind, bars_hold=8, stop_mult=1.5, tgt_mult=1.5):
    """Event-driven, fixed bars or stop/target. Returns array of net returns + index."""
    H,L,C,O=d.high.values,d.low.values,d.close.values,d.open.values
    A=d.atr.values
    if kind=="momentum": sig=(d.close>d.hi20).values
    else:                sig=(d.close<d.lo20).values
    idx=np.flatnonzero(sig); out=[];pos=[];last=-1
    for i in idx:
        if i<=last or i+1>=len(d): continue
        a=A[i]
        if not(a==a) or a<=0: continue
        e=O[i+1]
        if not(e==e) or e<=0: continue
        st=e-stop_mult*a; tg=e+tgt_mult*a
        r=None
        for j in range(i+1,min(i+1+bars_hold,len(d))):
            if L[j]<=st: r=(st/e-1); last=j; break
            if H[j]>=tg: r=(tg/e-1); last=j; break
        if r is None:
            j=min(i+bars_hold,len(d)-1); r=(C[j]/e-1); last=j
        out.append(r-COST); pos.append(i)
    return np.array(out), np.array(pos)

def main():
    print("REGIME x SESSION x TRADE TYPE — 15-min bars\n")
    print(f"  {len(SY)} symbols, cost {COST*1e4:.0f}bp, 20-bar breakout, 1.5 ATR stop/target, 8-bar max hold\n")
    res={}
    for s in SY:
        d=load(s)
        h=d.index.hour.values; rvp=d.rv_pct.values
        for kind in ("momentum","fade"):
            r,pos=test(d,kind)
            if not len(r): continue
            for sn,(a,b) in SESS.items():
                ms=(h[pos]>=a)&(h[pos]<b)
                for rn,lo,hi in (("low vol",0,0.33),("mid vol",0.33,0.67),("high vol",0.67,1.01)):
                    mr=(rvp[pos]>=lo)&(rvp[pos]<hi)
                    m=ms&mr
                    if m.sum()>=30:
                        res.setdefault((kind,sn,rn),[]).extend(r[m])
    print("="*86)
    print(f"  {'':10s} " + "".join(f"{s:>24}" for s in SESS))
    print("="*86)
    for kind in ("momentum","fade"):
        print(f"\n  {kind.upper()} ({'buy breakouts above the 20-bar high' if kind=='momentum' else 'buy pushes below the 20-bar low'})")
        for rn in ("low vol","mid vol","high vol"):
            row=f"  {rn:10s} "
            for sn in SESS:
                v=res.get((kind,sn,rn))
                if v and len(v)>=100:
                    v=np.array(v); t=v.mean()/(v.std()/np.sqrt(len(v)))
                    row+=f"{v.mean()*100:+8.3f}% (t{t:+5.1f},n{len(v):5d})"
                else:
                    row+=f"{'-':>24}"
            print(row)
    print()
    print("="*86); print("  BEST CELL PER SESSION"); print("="*86)
    for sn in SESS:
        best=None
        for kind in ("momentum","fade"):
            for rn in ("low vol","mid vol","high vol"):
                v=res.get((kind,sn,rn))
                if v and len(v)>=100:
                    m=np.mean(v)
                    if best is None or m>best[0]: best=(m,kind,rn,len(v))
        if best:
            print(f"  {sn:8s} -> {best[1]:9s} in {best[2]:9s}  {best[0]*100:+.3f}%/trade  (n={best[3]})")
if __name__=="__main__": main()
