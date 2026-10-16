"""THE TRADE-OFF CURVE. DK: 'increase the frequency / reduce the extremity
somewhat'. Six scattered points suggested a cliff near +100%. This maps the
shape so a point on the curve can be chosen knowingly, and reports ALL 199
products alongside bitcoin because two bitcoin cycles will fit any grid."""
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
def run(px,stretch,dip,slc=0.30,ma_n=200,max_cash=0.30):
    p=px.dropna()
    if len(p)<400: return None
    ma=p.rolling(ma_n).mean(); units=1.0/p.iloc[0]; cash=0.0; tp=None
    curve=[]; trims=0
    for i in range(ma_n,len(p)):
        price=p.iloc[i]; m=ma.iloc[i]; val=units*price+cash; curve.append(val)
        if not np.isfinite(m) or m<=0: continue
        dev=price/m-1; cs=cash/val if val>0 else 0
        if dev>stretch and cs<max_cash and units>0:
            room=(max_cash-cs)*val; sv=min(slc*units*price,room); sell=sv/price
            if sell>0:
                cash+=sell*price*(1-COST); units-=sell; trims+=1
                tp=price if tp is None else max(tp,price)
        elif cash>0 and tp is not None and price<=tp*(1-dip):
            units+=cash/(price*(1+COST)); cash=0.0; tp=None
    if not curve: return None
    E=pd.Series(curve); return E.iloc[-1],(E/E.cummax()-1).min(),trims
data=load()
holds={}
for s,p in data.items():
    q=p.dropna()
    if len(q)>=400: holds[s]=q.iloc[-1]/q.iloc[0]
hmean=np.mean(list(holds.values())); hmed=np.median(list(holds.values()))
btc=data[[k for k in data if k.startswith("BTC")][0]]
bh=btc.iloc[-1]/btc.iloc[0]
S=[0.50,0.75,1.00,1.25,1.50,1.75,2.00]; D=[0.20,0.30,0.40,0.50]
print(f"BITCOIN — % versus holding ({bh:.1f}x). Rows = trim trigger, cols = redeploy depth.\n")
print("  trigger      " + "".join(f"{'-'+str(int(d*100))+'%':>10}" for d in D) + f"{'trims':>8}")
for s in S:
    cells=[]; tr=0
    for d in D:
        r=run(btc,s,d)
        cells.append(f"{(r[0]/bh-1)*100:+.0f}%" if r else "-")
        if r: tr=max(tr,r[2])
    print(f"  +{int(s*100):>3}% over 200d" + "".join(f"{c:>10}" for c in cells) + f"{tr:>8}")
print(f"\nALL 199 PRODUCTS — mean outcome as % versus holding (hold mean {hmean:.2f}x)\n")
print("  trigger      " + "".join(f"{'-'+str(int(d*100))+'%':>10}" for d in D))
for s in S:
    cells=[]
    for d in D:
        vals=[]
        for sym,p in data.items():
            if sym not in holds: continue
            r=run(p,s,d)
            if r and np.isfinite(r[0]): vals.append(r[0])
        cells.append(f"{(np.mean(vals)/hmean-1)*100:+.0f}%" if len(vals)>30 else "-")
    print(f"  +{int(s*100):>3}% over 200d" + "".join(f"{c:>10}" for c in cells))
