"""DK: 'the first move is the wrong move' at the US open.
Define the opening range 13:30-14:00Z. Whichever extreme printed FIRST is the
'first move'. Test: from 14:00Z to 21:00Z, which side of the opening range breaks
first? The rule predicts the OPPOSITE side to the first move.
Control: the identical test on every other 30-min window of the day, so the
barrier geometry and the day's drift are held constant.
Research only."""
import glob,os,sys
import numpy as np, pandas as pd

OPEN_H,OPEN_M = 13,30
def run(open_h,open_m,label,hold_h=7):
    rows=[]
    for f in sorted(glob.glob('data_1m/*.csv'))+sorted(glob.glob('data_1m_oos/*.csv')):
        sym=os.path.basename(f)[:-4]
        d=pd.read_csv(f)
        d['ts']=pd.to_datetime(d.t,unit='ms',utc=True)
        d=d.set_index('ts')
        for day,g in d.groupby(d.index.date):
            o=g.between_time(f'{open_h:02d}:{open_m:02d}',
                             f'{(open_h+(open_m+29)//60)%24:02d}:{(open_m+29)%60:02d}')
            if len(o)<25: continue
            hi,lo=o.high.max(),o.low.min()
            if hi<=lo: continue
            t_hi=o.high.idxmax(); t_lo=o.low.idxmin()
            if t_hi==t_lo: continue
            first='UP' if t_hi<t_lo else 'DOWN'
            end=o.index[-1]+pd.Timedelta(hours=hold_h)
            fwd=g[(g.index>o.index[-1])&(g.index<=end)]
            if len(fwd)<60: continue
            up=fwd.index[fwd.high>=hi]; dn=fwd.index[fwd.low<=lo]
            if len(up)==0 and len(dn)==0: continue
            if len(up)==0: broke='DOWN'
            elif len(dn)==0: broke='UP'
            else: broke='UP' if up[0]<dn[0] else 'DOWN'
            rows.append(dict(sym=sym,day=str(day),first=first,broke=broke,
                             wrong=int(broke!=first),rng=(hi/lo-1)))
    T=pd.DataFrame(rows)
    if T.empty: return None
    n=len(T); w=T.wrong.mean()
    se=(w*(1-w)/n)**.5
    z=(w-0.5)/se
    print(f"{label:>12}  n={n:6d}  wrong-move rate {w*100:5.1f}%  "
          f"(+-{se*196:.1f}pp)  z={z:+5.2f}")
    return T,w,n,z

print("Does the first move at the open get faded? "
      "'wrong-move rate' = % of days the OPPOSITE side of the opening range broke first.\n")
res={}
for h,m in [(13,30),(0,0),(4,0),(8,0),(12,0),(16,0),(20,0)]:
    lab=f"{h:02d}:{m:02d}Z" + ("  <-US open" if (h,m)==(13,30) else "")
    r=run(h,m,lab)
    if r: res[(h,m)]=r
