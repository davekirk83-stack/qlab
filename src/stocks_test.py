"""
DOES THE SAME BOOK WORK ON SHARES?

DK: "we will find other things to scan and trade (stocks?)"

data_wide holds 130 US companies with ten years of daily bars. The rules are
applied completely unchanged - same bands, same target and stop, same
efficiency filter, same costs, same market-wide gate built from the equity
universe's own equal-weight index rather than crypto's.

This is the strongest test available of whether the mechanism is a property of
markets or a property of crypto. Different participants, different hours,
different microstructure, no 24/7 trading, and a universe that does not fall
92% as a matter of routine.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import system_on_history as SYS, portfolio as PF, gate_daily as G

def load_equities():
    out={}
    for p in sorted(glob.glob("/home/claude/qlab/data_wide/*.csv")):
        d=pd.read_csv(p)
        if len(d)<500: continue
        d.index=pd.to_datetime(d.date)
        out[os.path.basename(p)[:-4]]=d[["open","high","low","close","volume"]]
    return out

if __name__=="__main__":
    data=load_equities()
    sp=pd.Series({s:(d.index[-1]-d.index[0]).days/365.25 for s,d in data.items()})
    print(f"{len(data)} US equities, median history {sp.median():.1f}y, "
          f"{min(d.index[0] for d in data.values()).date()} -> "
          f"{max(d.index[-1] for d in data.values()).date()}\n")
    S=PF.signals(data); M=G.market_series(data)
    print(f"{len(S):,} signals, {S.sym.nunique()} names")
    kept=S[S.entry.map(lambda d: M["mkt_200"].get(d,np.nan)==1).fillna(False)].reset_index(drop=True)
    print(f"gated: {len(kept):,} ({len(kept)/len(S)*100:.0f}%)\n")
    T=SYS.trades(data)
    m=T.ret.mean(); c=T.ctrl.dropna()
    print(f"PER TRADE, ungated: {m*100:+.3f}%  t={m/(T.ret.std(ddof=1)/np.sqrt(len(T))):+.2f}  "
          f"edge over control {(m-c.mean())*100:+.3f}%  win {(T.ret>0).mean()*100:.0f}%\n")
    print(f"{'book':<22}{'slots':>6}{'lev':>5}{'final $':>11}{'CAGR':>8}{'maxDD':>9}"
          f"{'Sharpe':>8}{'/mo':>7}{'losing yrs':>12}")
    for tag,SS in (("ungated",S),("GATED",kept)):
        for mp,lv in ((40,1),(40,3)):
            r=PF.simulate(SS,mp,lv)
            if r is None: print(f"{tag:<22}{mp:>6}{lv:>5}  wiped out"); continue
            E=r["curve"]; yrs={y:(g.iloc[-1]/g.iloc[0]-1) for y,g in E.groupby(E.index.year) if len(g)>30}
            neg=sum(1 for v in yrs.values() if v<0)
            print(f"{tag:<22}{mp:>6}{lv:>5}{r['final']:>11,.0f}{r['cagr']*100:>7.1f}%"
                  f"{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}{r['per_month']:>7.1f}{neg:>8}/{len(yrs)}")
    r=PF.simulate(kept,40,3); E=r["curve"]
    print(f"\nGATED 40 slots 3x, year by year:")
    for y,g in E.groupby(E.index.year):
        if len(g)>30: print(f"  {y}  ${g.iloc[-1]:>9,.0f}  {(g.iloc[-1]/g.iloc[0]-1)*100:>+7.1f}%")
