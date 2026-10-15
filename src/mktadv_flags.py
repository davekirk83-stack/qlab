"""The binary flags my IC scorer dropped. Spearman on a 0/1 variable is weak,
so these get the right test: mean forward return when the flag is on vs off,
per symbol, on panel-demeaned forward returns, with a paired t across symbols."""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats
import elements_mktadv as M

PX="/home/claude/qlab/data_1h_33"; H=20
frames={}
for p in sorted(glob.glob(f"{PX}/*.csv")):
    s=os.path.basename(p)[:-4]
    d=pd.read_csv(p); d["dt"]=pd.to_datetime(d.date,utc=True)
    d=d.set_index("dt").sort_index()
    if len(d)<1500: continue
    d["fwd"]=d.close.shift(-H)/d.close-1
    frames[s]=d
fwd=pd.DataFrame({s:d.fwd for s,d in frames.items()})
fwd=fwd.sub(fwd.mean(axis=1),axis=0)
feats={s:M.build(d) for s,d in frames.items()}

FLAGS=[k for k in sorted(feats[list(feats)[0]]) if
       set(np.unique(feats[list(feats)[0]][k][np.isfinite(feats[list(feats)[0]][k])]))<={0.0,1.0}]
print(f"{len(FLAGS)} binary flags, {len(frames)} symbols, {H}-bar horizon, "
      f"forward returns demeaned across the panel\n")
print(f"{'flag':<24}{'fires%':>7}{'on ret':>10}{'off ret':>10}{'diff':>10}{'t':>7}{'syms+':>7}")
print("-"*75)
rows=[]
for k in FLAGS:
    diffs=[]; rate=[]; ons=[]; offs=[]
    for s,F in feats.items():
        x=pd.Series(F[k],index=frames[s].index); y=fwd[s].reindex(x.index)
        m=np.isfinite(x)&np.isfinite(y)
        on=y[m&(x==1)]; off=y[m&(x==0)]
        if len(on)<40 or len(off)<400: continue
        diffs.append(on.mean()-off.mean()); rate.append((x[m]==1).mean())
        ons.append(on.mean()); offs.append(off.mean())
    if len(diffs)<10: continue
    d=np.array(diffs); t=d.mean()/(d.std(ddof=1)/np.sqrt(len(d)))
    rows.append((k,np.mean(rate),np.mean(ons),np.mean(offs),d.mean(),t,
                 int((np.sign(d)==np.sign(d.mean())).sum()),len(d)))
for k,r,o,of,d,t,ag,n in sorted(rows,key=lambda z:-abs(z[5])):
    print(f"{k:<24}{r*100:>6.1f}%{o*100:>9.3f}%{of*100:>9.3f}%{d*100:>9.3f}%{t:>7.2f}{ag:>4}/{n}")
print("\nReference: a 20-bar hourly horizon is ~20h. A diff of 0.10% over 20h is")
print("about 1.1%/month before costs IF it fired every bar, which none of these do.")
