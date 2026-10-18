"""Same crossover study on 4-HOUR bars - the 'major' crosses DK sees on his chart."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X
X.CAP = 180; X.X_MIN_GAP = 2
data = X.load(); P = {}
PAIRS = [(9, 21), (20, 50), (50, 200)]
for s, d in data.items():
    d4 = d.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    C, H, L, a = X.prep(d4)
    P[s] = (C, H, L, a, {p: X.signals(C, a, *p) for p in PAIRS})
print(f"{len(P)} coins, 4-HOUR bars. Trailing stop k x ATR, 30-day cap, 9bp round trip.\n")
print(f"  {'entry':<24}{'side':<6}{'k':>3}{'n':>8}{'per ep':>9}{'t':>7}{'win':>6}{'hold':>6}{'ctrl':>8}{'edge':>8}{'race':>7}{'ctrl race':>10}")
for which, label in (("cross","cross"),("ant","anticipated")):
    for pair in PAIRS:
        for side, sl in ((1,"LONG"),(-1,"SHORT")):
            for k in (2,3):
                R, Cc = X.run(P, pair, k, which, side)
                if len(R) < 100: continue
                t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
                print(f"  {label+' '+str(pair[0])+'/'+str(pair[1]):<24}{sl:<6}{k:>3}{len(R):>8,}{R.ret.mean()*100:>+8.3f}%{t:>+7.1f}"
                      f"{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>6.0f}{Cc.ret.mean()*100:>+7.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}"
                      f"{R.win2.mean()*100:>6.0f}%{Cc.win2.mean()*100:>9.0f}%", flush=True)
        print()
