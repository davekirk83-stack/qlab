"""OVERHEATED, properly defined. DK means a blow-off top, not 'above average'.
Price 2-3x its own 200-day average happens twice a decade in bitcoin; +40%
happens constantly. All profit stays in the pot and compounds."""
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
def run(px,stretch,slc,dip,ma_n=200,max_cash=0.30):
    p=px.dropna()
    if len(p)<400: return None
    ma=p.rolling(ma_n).mean(); units=1.0/p.iloc[0]; cash=0.0; tp=None
    curve=[]; trims=0; buys=0
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
            units+=cash/(price*(1+COST)); cash=0.0; tp=None; buys+=1
    if not curve: return None
    E=pd.Series(curve)
    return E.iloc[-1],(E/E.cummax()-1).min(),trims,buys
data=load()
CFG=[("trim 20% at +100% over 200d, buy -30%",(1.00,0.20,0.30)),
     ("trim 30% at +100% over 200d, buy -30%",(1.00,0.30,0.30)),
     ("trim 30% at +150% over 200d, buy -30%",(1.50,0.30,0.30)),
     ("trim 30% at +200% over 200d, buy -30%",(2.00,0.30,0.30)),
     ("trim 30% at +150% over 200d, buy -50%",(1.50,0.30,0.50)),
     ("trim 30% at +200% over 200d, buy -50%",(2.00,0.30,0.50))]
btc=[k for k in data if k.startswith("BTC")]
if btc:
    b=data[btc[0]]; hv=b.iloc[-1]/b.iloc[0]
    hp=b.dropna(); hdd=(hp/hp.cummax()-1).min()
    print(f"BITCOIN {str(b.index[0])[:10]} -> {str(b.index[-1])[:10]}  (blow-off triggers only)")
    print(f"  {'variant':<42}{'$1 becomes':>12}{'vs hold':>10}{'maxDD':>9}{'trims':>7}{'buys':>6}")
    print(f"  {'hold — never trim':<42}{hv:>11.2f}x{'—':>10}{hdd*100:>8.1f}%{'—':>7}{'—':>6}")
    for lbl,c in CFG:
        r=run(b,*c)
        if r: print(f"  {lbl:<42}{r[0]:>11.2f}x{(r[0]/hv-1)*100:>+9.1f}%{r[1]*100:>8.1f}%{r[2]:>7}{r[3]:>6}")
print(f"\nALL {len(data)} PRODUCTS")
print(f"  {'variant':<42}{'median':>9}{'mean':>9}{'% beat hold':>13}")
holds={}
for s,p in data.items():
    q=p.dropna()
    if len(q)>=400: holds[s]=q.iloc[-1]/q.iloc[0]
hv=np.array(list(holds.values()))
print(f"  {'hold — never trim':<42}{np.median(hv):>9.2f}{hv.mean():>9.2f}{'—':>13}")
for lbl,c in CFG:
    vals,beat=[],[]
    for s,p in data.items():
        if s not in holds: continue
        r=run(p,*c)
        if r is None or not np.isfinite(r[0]): continue
        vals.append(r[0]); beat.append(r[0]>holds[s])
    if len(vals)<30: continue
    print(f"  {lbl:<42}{np.median(vals):>9.2f}{np.mean(vals):>9.2f}{np.mean(beat)*100:>12.0f}%")
