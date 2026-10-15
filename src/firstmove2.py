"""DK's rule as stated: the 'first move' is the NET direction of the first 30-60
min of the US session (the opening tick is spill). It reverses much of the time,
and the reversal targets the ASIA HIGH resting above.
Asia = 00:00-08:00Z. US open = 13:30Z. Research only."""
import glob,os
import numpy as np, pandas as pd

FILES = sorted(glob.glob('data_1m/*.csv'))+sorted(glob.glob('data_1m_oos/*.csv'))
CACHE={}
def load(f):
    if f not in CACHE:
        d=pd.read_csv(f); d.index=pd.to_datetime(d.t,unit='ms',utc=True)
        CACHE[f]=d
    return CACHE[f]

def build(win_min, open_h=13, open_m=30):
    rows=[]
    for f in FILES:
        sym=os.path.basename(f)[:-4]
        d=load(f)
        for day,g in d.groupby(d.index.date):
            asia=g.between_time('00:00','07:59')
            if len(asia)<300: continue
            ah,al=asia.high.max(),asia.low.min()
            t0=pd.Timestamp(f'{day} {open_h:02d}:{open_m:02d}',tz='UTC')
            fm=g[(g.index>=t0)&(g.index<t0+pd.Timedelta(minutes=win_min))]
            if len(fm)<win_min*0.8: continue
            o,c=float(fm.open.iloc[0]),float(fm.close.iloc[-1])
            if o==c: continue
            first='UP' if c>o else 'DOWN'
            fmh,fml=float(fm.high.max()),float(fm.low.min())
            fwd=g[(g.index>=t0+pd.Timedelta(minutes=win_min))&
                  (g.index< t0+pd.Timedelta(hours=7.5))]
            if len(fwd)<120: continue
            rows.append(dict(sym=sym,first=first,ret_first=c/o-1,
                ret_rest=float(fwd.close.iloc[-1])/c-1,
                ah_above=int(ah>c), hit_ah=int((fwd.high>=ah).any()) if ah>c else np.nan,
                al_below=int(al<c), hit_al=int((fwd.low<=al).any()) if al<c else np.nan,
                d_ah=(ah/c-1), d_al=(1-al/c),
                cont=int((fwd.high>=fmh).any()) if first=='UP' else int((fwd.low<=fml).any()),
                rev =int((fwd.low<=fml).any()) if first=='UP' else int((fwd.high>=fmh).any())))
    return pd.DataFrame(rows)

def report(T,label):
    print(f"\n=== {label}   n={len(T)} ===")
    for d in ('DOWN','UP'):
        S=T[T.first==d]
        if S.empty: continue
        signed = S.ret_rest if d=='DOWN' else -S.ret_rest   # + = reversed
        se=signed.std()/len(S)**.5
        print(f"  first {d:4s} n={len(S):5d} | first-move {S.ret_first.mean()*100:+.2f}% "
              f"| rest-of-session {S.ret_rest.mean()*100:+.3f}% "
              f"| reversal-signed {signed.mean()*100:+.3f}% (t={signed.mean()/se:+.1f})")
        print(f"            broke first-move extreme: same dir {S.cont.mean()*100:5.1f}%  "
              f"opposite {S.rev.mean()*100:5.1f}%")
    A=T[(T.first=='DOWN')&(T.ah_above==1)]
    if len(A):
        print(f"  ASIA-HIGH TARGET  first move DOWN, Asia high above: n={len(A)} "
              f"| tagged {A.hit_ah.mean()*100:.1f}% | mean distance {A.d_ah.mean()*100:.2f}%")
    U=T[(T.first=='UP')&(T.ah_above==1)]
    if len(U):
        print(f"  control           first move UP,   Asia high above: n={len(U)} "
              f"| tagged {U.hit_ah.mean()*100:.1f}% | mean distance {U.d_ah.mean()*100:.2f}%")
    B=T[(T.first=='UP')&(T.al_below==1)]
    if len(B):
        print(f"  mirror            first move UP,   Asia low below:  n={len(B)} "
              f"| tagged {B.hit_al.mean()*100:.1f}% | mean distance {B.d_al.mean()*100:.2f}%")

for w in (30,60):
    report(build(w), f"US OPEN 13:30Z, first-move window {w} min")
print("\n--- CONTROL HOURS (same construction, not the US open) ---")
for h in (4,8,18):
    report(build(60,open_h=h), f"{h:02d}:00Z, 60 min")
