"""
THE INTRADAY RANGE BOOK ON AN EQUITY CURVE.

+0.097%/trade at t=7.82 is a per-trade mean, and a per-trade mean has fooled
me twice today - finding 99. The only number that counts is what it does to
$2,000 with concurrency limits and compounding.

Config fixed from the sweep: 15min bars, 24-bar range, efficiency < 0.30,
maker-only entry at the range low, exit resting at the mid, taker stop at
1.5 ATR below. Fees swept 3 / 6 / 12 bp so the conclusion is not hostage to
the venue.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import intraday_maker as IM

TF,LOOK,EFF,HOLD = "15min",24,0.30,48
TAKER_EXIT,SLIP = IM.TAKER_EXIT, IM.SLIP
START=2000.0

def signals(data, maker_bp):
    mk=maker_bp/2/10000; rows=[]
    for s,d in data.items():
        b=IM.bars(d,TF)
        if len(b)<800: continue
        C,H,L=b.close.values,b.high.values,b.low.values
        n=len(C); a=IM.atr_np(H,L,C)
        hi=pd.Series(H).rolling(LOOK).max().values
        lo=pd.Series(L).rolling(LOOK).min().values
        eff=IM.efficiency(C); last=-10**9
        for i in range(LOOK+120,n-HOLD-2):
            if not (eff[i]<EFF) or i-last<HOLD: continue
            w=hi[i]-lo[i]
            if not np.isfinite(w) or w<=0 or not np.isfinite(a[i]) or w>6*a[i]: continue
            bid=lo[i]; tgt=(hi[i]+lo[i])/2; stop=lo[i]-1.5*a[i]
            fill=None
            for q in range(i+1,min(i+1+HOLD,n)):
                if L[q]<bid: fill=q; break
                if C[q]>hi[i]: break
            if fill is None: continue
            last=fill; e=bid*(1+mk); out=None; qq=fill
            for q in range(fill+1,min(fill+1+HOLD,n)):
                qq=q
                if C[q]<stop: out=(C[q]*(1-SLIP-TAKER_EXIT))/e-1; break
                if H[q]>=tgt: out=(tgt*(1-mk))/e-1; break
            if out is None:
                qq=min(fill+HOLD,n-1); out=(C[qq]*(1-TAKER_EXIT))/e-1
            rows.append((s,b.index[fill],b.index[qq],out))
    return pd.DataFrame(rows,columns=["sym","entry","exit","ret"]).sort_values("entry").reset_index(drop=True)

def sim(S,maxpos,lev):
    """Step the clock over every entry AND exit time, so positions actually close."""
    eq=START; open_pos=[]; curve=[]; taken=dropped=0
    ent=S.groupby(S.entry).groups
    times=pd.DatetimeIndex(sorted(set(S.entry)|set(S.exit)))
    for t in times:
        still=[]
        for ex,marg,r in open_pos:
            if ex<=t: eq+=max(r*lev*marg,-marg)
            else: still.append((ex,marg,r))
        open_pos=still
        if t in ent:
            for idx in ent[t]:
                row=S.loc[idx]
                if len(open_pos)>=maxpos or eq<=0: dropped+=1; continue
                m=eq/maxpos
                open_pos.append((row.exit,m,row.ret)); taken+=1
        curve.append((t,eq))
        if eq<=0: break
    E=pd.Series(dict(curve)).astype(float)
    if len(E)<50 or E.iloc[-1]<=0: return None
    yrs=(E.index[-1]-E.index[0]).days/365.25
    r=E.pct_change().replace([np.inf,-np.inf],np.nan).dropna()
    per=len(E)/max(yrs,.1)
    return dict(final=E.iloc[-1],cagr=(E.iloc[-1]/START)**(1/max(yrs,.1))-1,
        dd=(E/E.cummax()-1).min(),
        sharpe=r.mean()/r.std()*np.sqrt(per) if r.std()>0 else np.nan,
        taken=taken,dropped=dropped,permo=taken/max(yrs*12,.1),curve=E)

if __name__=="__main__":
    data=IM.load_1m()
    for fee in (3,6,12):
        S=signals(data,fee)
        print(f"\nfee {fee}bp — {len(S):,} fills, mean {S.ret.mean()*100:+.4f}%")
        print(f"  {'slots':>6}{'lev':>5}{'final $':>11}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>8}{'/mo':>8}")
        for mp in (10,20,40):
            for lv in (1,2,3):
                r=sim(S,mp,lv)
                if r is None: print(f"  {mp:>6}{lv:>5}   wiped out"); continue
                print(f"  {mp:>6}{lv:>5}{r['final']:>11,.0f}{r['cagr']*100:>8.1f}%"
                      f"{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}{r['permo']:>8.0f}")
