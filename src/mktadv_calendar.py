"""Catch on the previous run: a flag that is IDENTICAL across all symbols at a
given timestamp (in-NY, weekend, turn-of-month) is annihilated by cross-sectional
demeaning - it cannot be anything but zero. Those got 0.000 for structural
reasons, not because they were measured and found dead. Re-tested on RAW
forward returns, which is the only way a panel-wide calendar flag can be seen."""
import warnings; warnings.filterwarnings("ignore")
import os,glob
import numpy as np, pandas as pd
import elements_mktadv as M
PX="/home/claude/qlab/data_1h_33"; H=20
rows={}
for p in sorted(glob.glob(f"{PX}/*.csv")):
    s=os.path.basename(p)[:-4]
    d=pd.read_csv(p); d["dt"]=pd.to_datetime(d.date,utc=True)
    d=d.set_index("dt").sort_index()
    if len(d)<1500: continue
    d["fwd"]=d.close.shift(-H)/d.close-1
    rows[s]=d
print(f"{len(rows)} symbols, RAW (not demeaned) {H}-bar forward returns\n")
print(f"{'flag':<22}{'fires%':>8}{'on':>10}{'off':>10}{'diff':>10}{'t':>7}{'syms+':>8}")
print("-"*76)
F0=M.build(rows[list(rows)[0]])
flags=["cal_turn_of_month","cal_is_weekend","sess_in_ny","sess_in_ldn",
       "sess_in_asia","sess_ldn_standing"]
out=[]
for k in flags:
    dd=[];rt=[];on_=[];off_=[]
    for s,d in rows.items():
        x=pd.Series(M.build(d)[k],index=d.index); y=d.fwd
        m=np.isfinite(x)&np.isfinite(y)
        on=y[m&(x==1)];off=y[m&(x==0)]
        if len(on)<40 or len(off)<400: continue
        dd.append(on.mean()-off.mean()); rt.append((x[m]==1).mean())
        on_.append(on.mean()); off_.append(off.mean())
    if len(dd)<10: continue
    a=np.array(dd); t=a.mean()/(a.std(ddof=1)/np.sqrt(len(a)))
    out.append((k,np.mean(rt),np.mean(on_),np.mean(off_),a.mean(),t,
                int((np.sign(a)==np.sign(a.mean())).sum()),len(a)))
for k,r,o,of,d,t,ag,n in sorted(out,key=lambda z:-abs(z[5])):
    print(f"{k:<22}{r*100:>7.1f}%{o*100:>9.3f}%{of*100:>9.3f}%{d*100:>9.3f}%{t:>7.2f}{ag:>5}/{n}")
