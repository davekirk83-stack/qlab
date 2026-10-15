"""Does a DOWN open reach the Asia high more often than an UP open, once you
hold the DISTANCE to that high constant? The raw comparison is confounded:
UP opens sit closer to the Asia high, so they tag it more by geometry alone."""
import glob,os
import numpy as np, pandas as pd
FILES=sorted(glob.glob('data_1m/*.csv'))+sorted(glob.glob('data_1m_oos/*.csv'))
rows=[]
for f in FILES:
    d=pd.read_csv(f); d.index=pd.to_datetime(d.t,unit='ms',utc=True)
    atr=(d.high-d.low).rolling(60).mean()
    for day,g in d.groupby(d.index.date):
        asia=g.between_time('00:00','07:59')
        if len(asia)<300: continue
        ah=float(asia.high.max())
        t0=pd.Timestamp(f'{day} 13:30',tz='UTC')
        fm=g[(g.index>=t0)&(g.index<t0+pd.Timedelta(minutes=60))]
        if len(fm)<48: continue
        o,c=float(fm.open.iloc[0]),float(fm.close.iloc[-1])
        if o==c or ah<=c: continue
        fwd=g[(g.index>=t0+pd.Timedelta(hours=1))&(g.index<t0+pd.Timedelta(hours=7.5))]
        if len(fwd)<120: continue
        a=atr.reindex([fm.index[-1]]).iloc[0]
        if not np.isfinite(a) or a<=0: continue
        rows.append(dict(first='UP' if c>o else 'DOWN',
                         dist_atr=(ah-c)/a, dist_pct=(ah/c-1)*100,
                         hit=int((fwd.high>=ah).any())))
T=pd.DataFrame(rows)
T['bin']=pd.qcut(T.dist_atr,8,labels=False,duplicates='drop')
print("Asia high tagged later in the session, by distance to it (ATR-60 units).")
print(f"{'bin':>3} {'dist ATR':>9} {'n DOWN':>7} {'hit%':>6} {'n UP':>6} {'hit%':>6} {'DOWN-UP':>8}")
tot_d=tot_u=0; wsum=0; wn=0
for b,G in T.groupby('bin'):
    D=G[G.first=='DOWN']; U=G[G.first=='UP']
    if len(D)<30 or len(U)<30: continue
    hd,hu=D.hit.mean(),U.hit.mean()
    print(f"{int(b):>3} {G.dist_atr.median():>9.1f} {len(D):>7} {hd*100:>5.1f}% "
          f"{len(U):>6} {hu*100:>5.1f}% {(hd-hu)*100:>+7.1f}pp")
    w=min(len(D),len(U)); wsum+=(hd-hu)*w; wn+=w
print(f"\ndistance-matched DOWN minus UP: {wsum/wn*100:+.1f}pp")
print(f"raw (unmatched):                "
      f"{(T[T.first=='DOWN'].hit.mean()-T[T.first=='UP'].hit.mean())*100:+.1f}pp")
