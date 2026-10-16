"""NEVER SELL THE CORE. Add side capital on dips, withdraw it on the recovery,
leave the profit in the core.
DK: 'Leave the core. Just add on dips and then remove the capital again on
mean reversions or rips, leaving the profit in the core.'

Different from every earlier test: those all started 100% invested and TRIMMED,
which sells the compounder. Here the core is never sold. The cost is explicit
and measurable - holding side capital in cash means that much less compounding -
so the dip round trips must out-earn the growth forgone.

  A  all capital in the core, never touched              (benchmark)
  B  (1-c) in the core + c as side capital that buys dips, exits on recovery,
     and sweeps its profit into the core

Grid drawn in full before any cell is quoted (doc 128)."""
import sys; sys.path.insert(0,"/home/claude/qlab/src")
import warnings; warnings.filterwarnings("ignore")
import glob,os
import numpy as np, pandas as pd
COST=0.0010; STABLE=("USDT","USDC","DAI","PYUSD","USDS","GUSD")
def load(mb=900):
    out={}
    for f in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        s=os.path.basename(f)[:-4]
        if any(s.startswith(x) for x in STABLE): continue
        d=pd.read_csv(f)
        if "t" not in d.columns or len(d)<mb: continue
        d.index=pd.to_datetime(d.t,unit="ms",utc=True)
        out[s]=d[~d.index.duplicated(keep="last")].sort_index().close.astype(float)
    return out

def run(px,dip,recover,side=0.20,win=21):
    """Core units bought at the start and NEVER sold. Side capital buys when
    price is `dip` below its 21-day high; sells the added units when price
    recovers `recover` above the entry; the original capital returns to cash
    and the PROFIT is converted into extra core units."""
    p=px.dropna()
    if len(p)<400: return None
    hi=p.rolling(win).max()
    core=(1.0-side)/p.iloc[0]
    cash=side; add_u=0.0; add_px=None
    curve=[]; trips=0; wins=0
    for i in range(win,len(p)):
        price=p.iloc[i]; h=hi.iloc[i]
        curve.append(core*price + add_u*price + cash)
        if not np.isfinite(h) or h<=0: continue
        if add_u==0.0 and cash>0 and price<=h*(1-dip):
            add_u=cash/(price*(1+COST)); add_px=price; cash=0.0
        elif add_u>0 and price>=add_px*(1+recover):
            proceeds=add_u*price*(1-COST)
            cash=side                      # the side pot is restored
            profit=max(proceeds-side,0.0)
            core+=profit/(price*(1+COST))  # profit compounds in the core
            if proceeds>side: wins+=1
            add_u=0.0; add_px=None; trips+=1
    if not curve: return None
    E=pd.Series(curve)
    return E.iloc[-1],(E/E.cummax()-1).min(),trips,wins

data=load()
holds={s:p.dropna().iloc[-1]/p.dropna().iloc[0] for s,p in data.items() if len(p.dropna())>=400}
hmean=np.mean(list(holds.values()))
btc=data[[k for k in data if k.startswith("BTC")][0]]; bh=btc.iloc[-1]/btc.iloc[0]
DIP=[0.05,0.10,0.15,0.25]; REC=[0.05,0.10,0.20]
for side in (0.10,0.20):
    print(f"\nBITCOIN — side pot {int(side*100)}%, % versus holding 100% ({bh:.1f}x)\n")
    print("  buy dip of   " + "".join(f"{'exit +'+str(int(r*100))+'%':>13}" for r in REC) + f"{'trips':>7}")
    for d in DIP:
        cells=[]; tr=0
        for r in REC:
            o=run(btc,d,r,side)
            cells.append(f"{(o[0]/bh-1)*100:+.1f}%" if o else "-")
            if o: tr=max(tr,o[2])
        print(f"  -{int(d*100):>3}% from 21d high" + "".join(f"{c:>13}" for c in cells) + f"{tr:>7}")
print(f"\nALL {len(holds)} PRODUCTS — side pot 20%, mean versus holding ({hmean:.2f}x)\n")
print("  buy dip of   " + "".join(f"{'exit +'+str(int(r*100))+'%':>13}" for r in REC))
for d in DIP:
    cells=[]
    for r in REC:
        vals=[]
        for s,p in data.items():
            if s not in holds: continue
            o=run(p,d,r,0.20)
            if o and np.isfinite(o[0]): vals.append(o[0])
        cells.append(f"{(np.mean(vals)/hmean-1)*100:+.1f}%" if len(vals)>30 else "-")
    print(f"  -{int(d*100):>3}% from 21d high" + "".join(f"{c:>13}" for c in cells))
