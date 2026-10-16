"""RIPS AND DIPS AS SPEED, NOT LEVEL.
DK: 'Even bitcoin, at least now, is not so volatile that you never see a rip
or real dip. We do.' Every earlier test defined overheated as price ELEVATED
above a long average. A rip is a RATE - up X% in N days - and bitcoin can rip
hard while still below its 200-day average. Different trigger, never tested.
Grid drawn in full before any cell is quoted (doc 128's rule)."""
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
def run(px,rip,dip,win=21,slc=0.20,max_cash=0.20):
    """Trim when price is up `rip` over `win` days; redeploy when it has
    fallen `dip` from the trim price. Speed, not elevation."""
    p=px.dropna()
    if len(p)<400: return None
    roc=p.pct_change(win)
    units=1.0/p.iloc[0]; cash=0.0; tp=None; curve=[]; trims=0
    for i in range(win+5,len(p)):
        price=p.iloc[i]; r=roc.iloc[i]; val=units*price+cash; curve.append(val)
        if not np.isfinite(r): continue
        cs=cash/val if val>0 else 0
        if r>rip and cs<max_cash and units>0:
            room=(max_cash-cs)*val; sv=min(slc*units*price,room); sell=sv/price
            if sell>0:
                cash+=sell*price*(1-COST); units-=sell; trims+=1
                tp=price if tp is None else max(tp,price)
        elif cash>0 and tp is not None and price<=tp*(1-dip):
            units+=cash/(price*(1+COST)); cash=0.0; tp=None
    if not curve: return None
    E=pd.Series(curve); return E.iloc[-1],(E/E.cummax()-1).min(),trims
data=load()
holds={s:p.dropna().iloc[-1]/p.dropna().iloc[0] for s,p in data.items() if len(p.dropna())>=400}
hmean=np.mean(list(holds.values()))
btc=data[[k for k in data if k.startswith("BTC")][0]]; bh=btc.iloc[-1]/btc.iloc[0]
RIP=[0.15,0.25,0.35,0.50,0.75]; DIP=[0.10,0.15,0.20,0.30]
print(f"BITCOIN — % versus holding ({bh:.1f}x).  Rip measured over 21 days, trim 20%.\n")
print("  rip trigger  " + "".join(f"{'dip -'+str(int(d*100))+'%':>11}" for d in DIP) + f"{'trims':>8}")
for r in RIP:
    cells=[]; tr=0
    for d in DIP:
        o=run(btc,r,d)
        cells.append(f"{(o[0]/bh-1)*100:+.0f}%" if o else "-")
        if o: tr=max(tr,o[2])
    print(f"  +{int(r*100):>3}% in 21d" + "".join(f"{c:>11}" for c in cells) + f"{tr:>8}")
print(f"\nALL {len(holds)} PRODUCTS — mean versus holding ({hmean:.2f}x)\n")
print("  rip trigger  " + "".join(f"{'dip -'+str(int(d*100))+'%':>11}" for d in DIP))
for r in RIP:
    cells=[]
    for d in DIP:
        vals=[]
        for s,p in data.items():
            if s not in holds: continue
            o=run(p,r,d)
            if o and np.isfinite(o[0]): vals.append(o[0])
        cells.append(f"{(np.mean(vals)/hmean-1)*100:+.0f}%" if len(vals)>30 else "-")
    print(f"  +{int(r*100):>3}% in 21d" + "".join(f"{c:>11}" for c in cells))
