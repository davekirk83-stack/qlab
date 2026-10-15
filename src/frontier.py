"""
THE GATED BOOK, SCALED — where is the usable configuration?

The index-above-200d gate turns the book from 0.48 Sharpe / -33.7% drawdown
with two account-destroying years into 0.95 Sharpe / -9.4% drawdown with none.
That was one arbitrary configuration: 20 slots, 1x. This finds the frontier.

A 9.4% drawdown at 1x is a lot of unused risk budget for someone who has
stated 2-5x as normal. The question is how much return that budget buys before
the drawdown stops being survivable. DK's own stated tolerance governs, so
both axes are reported rather than one 'optimal' cell chosen for him.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import system_on_history as SYS, portfolio as PF, gate_daily as G

data = SYS.load(); S = PF.signals(data); M = G.market_series(data)
kept = S[S.entry.map(lambda d: M["mkt_200"].get(d, np.nan) == 1).fillna(False)]
kept = kept.reset_index(drop=True)
print(f"gated signals: {len(kept):,} of {len(S):,} ({len(kept)/len(S)*100:.0f}%)")
sd = kept.groupby(kept.entry.dt.to_period('M')).size()
print(f"gated signals per month: median {sd.median():.0f}, max {sd.max()}\n")
print(f"{'slots':>6}{'lev':>5}{'final $':>11}{'CAGR':>8}{'maxDD':>9}{'Sharpe':>8}"
      f"{'trades/mo':>11}{'worst yr':>10}{'losing yrs':>11}")
best=[]
for maxpos in (5,10,20,40):
    for lev in (1,2,3,5,10):
        r=PF.simulate(kept,maxpos,lev)
        if r is None:
            print(f"{maxpos:>6}{lev:>5}  WIPED OUT"); continue
        E=r["curve"]
        yrs={y:(g.iloc[-1]/g.iloc[0]-1) for y,g in E.groupby(E.index.year) if len(g)>30}
        wy=min(yrs.values()); neg=sum(1 for v in yrs.values() if v<0)
        r.update(wy=wy,neg=neg,nyr=len(yrs)); best.append(r)
        print(f"{maxpos:>6}{lev:>5}{r['final']:>11,.0f}{r['cagr']*100:>7.1f}%"
              f"{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}{r['per_month']:>11.1f}"
              f"{wy*100:>9.1f}%{neg:>7}/{r['nyr']}")
ok=[r for r in best if r["dd"]>-0.35 and r["neg"]==0]
print(f"\nCONFIGURATIONS WITH NO LOSING YEAR AND DRAWDOWN BETTER THAN -35%: {len(ok)}")
for r in sorted(ok,key=lambda x:-x["cagr"])[:6]:
    print(f"  {r['maxpos']:>2} slots {r['lev']}x -> ${r['final']:>8,.0f}  "
          f"CAGR {r['cagr']*100:>5.1f}%  maxDD {r['dd']*100:>6.1f}%  "
          f"Sharpe {r['sharpe']:.2f}  {r['per_month']:.0f} trades/mo")
if ok:
    b=max(ok,key=lambda x:x["cagr"]); E=b["curve"]
    print(f"\nHIGHEST RETURN WITH NO LOSING YEAR: {b['maxpos']} slots at {b['lev']}x")
    for y,g in E.groupby(E.index.year):
        if len(g)>30:
            print(f"    {y}  ${g.iloc[-1]:>10,.0f}  {(g.iloc[-1]/g.iloc[0]-1)*100:>+7.1f}%  "
                  f"worst drawdown {(g/g.cummax()-1).min()*100:>6.1f}%")
    E.to_csv("/home/claude/qlab/runs/equity_gated.csv")
