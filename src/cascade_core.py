"""Core position + cascade-style redeployment on SMALL corrections.
DK: 'Not even a crash, but a 5-10% correction, similar to how our cascade
trader deploys.' The cash comes back in on a modest dip FROM THE TRIM PRICE,
not from the all-time high - so it is rarely idle and recycles often."""
import sys; sys.path.insert(0,"/home/claude/qlab/src")
import warnings; warnings.filterwarnings("ignore")
import glob,os
import numpy as np, pandas as pd
COST=0.0010; STABLE=("USDT","USDC","DAI","PYUSD","USDS","GUSD")

def load(minbars=900):
    out={}
    for f in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        s=os.path.basename(f)[:-4]
        if any(s.startswith(x) for x in STABLE): continue
        d=pd.read_csv(f)
        if "t" not in d.columns or len(d)<minbars: continue
        d.index=pd.to_datetime(d.t,unit="ms",utc=True)
        d=d[~d.index.duplicated(keep="last")].sort_index()
        out[s]=d.close.astype(float)
    return out

def run(px,stretch,slice_frac,dip,ma_n=100,max_cash=0.20):
    """Trim when price is `stretch` above its average; redeploy when price
    falls `dip` BELOW THE PRICE WE TRIMMED AT. Cash capped at max_cash."""
    p=px.dropna()
    if len(p)<400: return None
    ma=p.rolling(ma_n).mean()
    units=1.0/p.iloc[0]; cash=0.0; trim_px=None
    curve=[]; rounds=0
    for i in range(ma_n,len(p)):
        price=p.iloc[i]; m=ma.iloc[i]
        val=units*price+cash; curve.append(val)
        if not np.isfinite(m) or m<=0: continue
        dev=price/m-1; cs=cash/val if val>0 else 0
        if dev>stretch and cs<max_cash and units>0:
            room=(max_cash-cs)*val
            sv=min(slice_frac*units*price,room); sell=sv/price
            if sell>0:
                cash+=sell*price*(1-COST); units-=sell
                trim_px=price if trim_px is None else max(trim_px,price)
        elif cash>0 and trim_px is not None and price<=trim_px*(1-dip):
            buy=cash/(price*(1+COST)); units+=buy; cash=0.0
            trim_px=None; rounds+=1
    if not curve: return None
    E=pd.Series(curve); mdd=(E/E.cummax()-1).min()
    return E.iloc[-1],mdd,rounds

data=load(); print(f"{len(data)} products.\n")
CFG=[("trim 20% at +25%, redeploy -5%",(0.25,0.20,0.05)),
     ("trim 20% at +25%, redeploy -10%",(0.25,0.20,0.10)),
     ("trim 20% at +15%, redeploy -5%",(0.15,0.20,0.05)),
     ("trim 20% at +15%, redeploy -10%",(0.15,0.20,0.10)),
     ("trim 15% at +10%, redeploy -5%",(0.10,0.15,0.05)),
     ("trim 20% at +40%, redeploy -10%",(0.40,0.20,0.10))]
btc=[k for k in data if k.startswith("BTC")]
if btc:
    b=data[btc[0]]; hv=b.iloc[-1]/b.iloc[0]
    hp=b.dropna(); hdd=(hp/hp.cummax()-1).min()
    print(f"BITCOIN {str(b.index[0])[:10]} -> {str(b.index[-1])[:10]}")
    print(f"  {'variant':<36}{'$1 becomes':>12}{'vs hold':>10}{'maxDD':>9}{'round trips':>13}")
    print(f"  {'hold — never trim':<36}{hv:>11.2f}x{'—':>10}{hdd*100:>8.1f}%{'—':>13}")
    for lbl,c in CFG:
        r=run(b,*c)
        if r: print(f"  {lbl:<36}{r[0]:>11.2f}x{(r[0]/hv-1)*100:>+9.1f}%{r[1]*100:>8.1f}%{r[2]:>13}")
print(f"\nALL {len(data)} PRODUCTS")
print(f"  {'variant':<36}{'median':>9}{'mean':>9}{'med maxDD':>12}{'% beat hold':>13}{'avg trips':>11}")
holds={}
for s,p in data.items():
    q=p.dropna()
    if len(q)>=400: holds[s]=(q.iloc[-1]/q.iloc[0],(q/q.cummax()-1).min())
hv=np.array([v for v,_ in holds.values()]); hd=np.array([d for _,d in holds.values()])
print(f"  {'hold — never trim':<36}{np.median(hv):>9.2f}{hv.mean():>9.2f}{np.median(hd)*100:>11.1f}%{'—':>13}{'—':>11}")
for lbl,c in CFG:
    vals,dds,beat,tr=[],[],[],[]
    for s,p in data.items():
        if s not in holds: continue
        r=run(p,*c)
        if r is None or not np.isfinite(r[0]): continue
        vals.append(r[0]); dds.append(r[1]); tr.append(r[2]); beat.append(r[0]>holds[s][0])
    if len(vals)<30: continue
    print(f"  {lbl:<36}{np.median(vals):>9.2f}{np.mean(vals):>9.2f}{np.median(dds)*100:>11.1f}%{np.mean(beat)*100:>12.0f}%{np.mean(tr):>11.1f}")
