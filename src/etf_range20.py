"""
THE RANGE BOOK OUTSIDE CRYPTO — 37 ETFs, daily bars.

First test of the book on anything other than crypto. Same structure: EMA20,
2-ATR Keltner bands, containment switch above its own expanding median, four
laddered entries each side, scaled exits, break exit, both sides. Costs set
for liquid ETFs (2bp a side) rather than Hyperliquid. The expanding-median
warm-up is shortened to 200 bars because three years of daily data is only
753 of them.

The hypothesis is that it should do BETTER than in crypto, because these
markets have less drift and the book earns on a stable mean. The honest
counter-hypothesis is that crypto's retail-driven intraday chop is the edge
and institutional markets have arbitraged it away. Three years will not
settle that, but it will say whether it is worth getting more data.
"""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD

CP.MK = 2/10000; CP.TAKER = 3/10000; CP.SLIP = 2/10000
GROUPS = {"energy":["USO","UNG","XLE"],"metals":["GLD","SLV","CPER","GDX","SLX","XME"],
          "agri":["DBA","CORN","WEAT"],"index":["SPY","QQQ","IWM","DIA"],
          "sectors":["XLF","XLK","XLV","XLU","XLP","XLI","XLB","XLY"],
          "bonds":["TLT","IEF","HYG","LQD","TIP"],
          "intl":["EEM","EFA","FXI","EWJ","EWZ"],"vol/fx":["VXX","UUP","FXE"]}

data = {}
for f in sorted(glob.glob("/home/claude/qlab/data_etf20/*.csv")):
    s = os.path.basename(f)[:-4]
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
    data[s] = d
print(f"{len(data)} ETFs, daily bars, 20+ years.\n")

rows = []; per = {}
for s, d in data.items():
    D, ema, lo, hi, a = RD.detectors(d)
    v = pd.Series(D["contain"])
    allow = (v > v.expanding(500).median()).values
    r = CP.episodes(d, allow, ema, lo, hi, a, None, "optimistic", "L", s) + \
        CP.episodes(d, allow, ema, lo, hi, a, None, "optimistic", "S", s)
    S = pd.DataFrame(r, columns=["sym","entry","exit","ret","side"]); S = S[np.isfinite(S.ret)]
    per[s] = S; rows.append(S)
A = pd.concat(rows, ignore_index=True)

print(f"  {'group':<10}{'episodes':>10}{'per ep':>11}{'t':>7}{'win':>6}{'long':>10}{'short':>10}{'worst':>9}")
for g, syms in GROUPS.items():
    G = pd.concat([per[s] for s in syms if s in per], ignore_index=True)
    if len(G) < 20: continue
    t = G.ret.mean()/(G.ret.std(ddof=1)/np.sqrt(len(G)))
    L = G[G.side=="L"].ret.mean()*100; Sh = G[G.side=="S"].ret.mean()*100
    print(f"  {g:<10}{len(G):>10,}{G.ret.mean()*100:>+10.4f}%{t:>+7.2f}{(G.ret>0).mean()*100:>5.0f}%"
          f"{L:>+9.3f}%{Sh:>+9.3f}%{G.ret.min()*100:>+8.1f}%")
t = A.ret.mean()/(A.ret.std(ddof=1)/np.sqrt(len(A)))
print(f"  {'ALL':<10}{len(A):>10,}{A.ret.mean()*100:>+10.4f}%{t:>+7.2f}{(A.ret>0).mean()*100:>5.0f}%"
      f"{A[A.side=='L'].ret.mean()*100:>+9.3f}%{A[A.side=='S'].ret.mean()*100:>+9.3f}%{A.ret.min()*100:>+8.1f}%")
print(f"\n  Crypto on the same accounting (doc 123): ~+0.11% an episode.")
for lev in (1, 2):
    r, tk, sk = CP.simulate(A, 20, lev)
    if r: print(f"  equity {lev}x, 20 slots: CAGR {r['cagr']*100:5.1f}%  maxDD {r['dd']*100:5.1f}%  Sharpe {r['sharpe']:4.2f}  {tk:,} taken")
