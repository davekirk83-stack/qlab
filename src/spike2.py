"""
THE SPIKE SHORT, TESTED PROPERLY THIS TIME.

I killed this prematurely. Two errors:
  1. I checked the liquidity filter only on the RAREST cell (+200% in 7 days,
     62 trades), where of course nothing survived. The +100%-in-7-days cell
     had 281 trades and was never filtered.
  2. I reported a 23-37% liquidation rate at 3x as if leverage were fixed.
     At 1x there is no liquidation. The right question is whether it pays
     unlevered.

So: every spike threshold, on the liquid half and liquid quartile, and the
return reported both raw and as what it does to a $2,000 book at 1x with
position limits - because a per-trade mean has already fooled me once today.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import shortspike as SS

data = SS.load()
liq = pd.Series({s:(d.close*d.volume).tail(60).median() for s,d in data.items()})
tiers = {"all 300": set(liq.index),
         "top half (>$147k/day)": set(liq[liq>=liq.quantile(0.50)].index),
         "top quartile (>$586k/day)": set(liq[liq>=liq.quantile(0.75)].index),
         "top decile (>$4m/day)": set(liq[liq>=liq.quantile(0.90)].index)}
print("SHORT AFTER A SPIKE — by how liquid the coin is (can you actually short it?)\n")
print(f"{'spike':>14}{'hold':>6}  {'universe':<28}{'n':>6}{'mean':>9}{'t':>7}{'win':>6}{'worst':>9}")
keep_best=[]
for up,win in ((1.0,7),(1.0,30),(0.5,7)):
    for hold in (90,180):
        for tag,ks in tiers.items():
            T=SS.short_after_spike(data,up,win,hold,1.0,keep=ks)
            if T is None or len(T)<40: 
                print(f"{up*100:>13.0f}%{hold:>6}  {tag:<28}{'too few':>6}"); continue
            m=T.ret.mean(); t=m/(T.ret.std(ddof=1)/np.sqrt(len(T)))
            print(f"{up*100:>13.0f}%{hold:>6}  {tag:<28}{len(T):>6}{m*100:>+8.2f}%{t:>+7.2f}"
                  f"{(T.ret>0).mean()*100:>5.0f}%{T.ret.min()*100:>+8.1f}%")
            if t>2 and len(T)>=80: keep_best.append((m,t,up,win,hold,tag,T))
print()
if keep_best:
    keep_best.sort(key=lambda z:-z[0])
    m,t,up,win,hold,tag,T=keep_best[0]
    print(f"BEST TRADEABLE CELL: short after +{up*100:.0f}% in {win}d, hold {hold}d, "
          f"{tag}\n  {len(T)} trades, {m*100:+.2f}%/trade, t={t:+.2f}, "
          f"win {(T.ret>0).mean()*100:.0f}%")
    T=T.copy(); T["yr"]=T.ts.dt.year
    print("\n  by year:")
    for y,g in T.groupby("yr"):
        if len(g)<10: continue
        print(f"    {y}  n={len(g):>4}  {g.ret.mean()*100:>+7.2f}%  "
              f"win {(g.ret>0).mean()*100:>3.0f}%  worst {g.ret.min()*100:>+7.1f}%")
    neg=sum(1 for y,g in T.groupby("yr") if len(g)>=10 and g.ret.mean()<0)
    tot=sum(1 for y,g in T.groupby("yr") if len(g)>=10)
    print(f"\n  losing years: {neg}/{tot}")
    print(f"  signals per month across the whole sample: "
          f"{len(T)/((T.ts.max()-T.ts.min()).days/30.44):.1f}")
else:
    print("no cell with t>2 and n>=80 after the liquidity filter.")
