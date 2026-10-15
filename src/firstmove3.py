"""DK: the one-sidedness of the first-move rule probably depends on the
prevailing market direction. Split the US-open first-move test by trailing
regime and see whether the asymmetry flips.
Regime = trailing 20-day return of the symbol, measured at 13:30Z (causal).
Research only."""
import glob,os
import numpy as np, pandas as pd

FILES=sorted(glob.glob('data_1m/*.csv'))+sorted(glob.glob('data_1m_oos/*.csv'))
rows=[]
for f in FILES:
    sym=os.path.basename(f)[:-4]
    d=pd.read_csv(f); d.index=pd.to_datetime(d.t,unit='ms',utc=True)
    # daily closes for the trailing-regime measure
    dc=d.close.resample('1D').last().dropna()
    r20=(dc/dc.shift(20)-1)
    for day,g in d.groupby(d.index.date):
        ts=pd.Timestamp(day)
        # causal: regime from the PREVIOUS day's close
        prev=r20.index[r20.index<ts.tz_localize('UTC')]
        if len(prev)==0: continue
        reg=r20.loc[prev[-1]]
        if not np.isfinite(reg): continue
        t0=pd.Timestamp(f'{day} 13:30',tz='UTC')
        fm=g[(g.index>=t0)&(g.index<t0+pd.Timedelta(minutes=60))]
        if len(fm)<48: continue
        o,c=float(fm.open.iloc[0]),float(fm.close.iloc[-1])
        if o==c: continue
        fwd=g[(g.index>=t0+pd.Timedelta(hours=1))&(g.index<t0+pd.Timedelta(hours=7.5))]
        if len(fwd)<120: continue
        rows.append(dict(sym=sym,day=str(day),reg=reg,
            first='UP' if c>o else 'DOWN',
            ret_first=c/o-1, ret_rest=float(fwd.close.iloc[-1])/c-1))
T=pd.DataFrame(rows)
print(f"n={len(T)}  trailing-20d regime: median {T.reg.median()*100:+.1f}%, "
      f"{(T.reg>0).mean()*100:.0f}% of day-symbols in an uptrend\n")

T['bucket']=pd.cut(T.reg,[-9,-0.15,-0.05,0.05,0.15,9],
    labels=['bear <-15%','soft bear','flat +-5%','soft bull','bull >+15%'])

print(f"{'regime':<12} {'first':<5} {'n':>6} {'rest-of-session':>16} {'t':>7}")
print("-"*52)
for b in T.bucket.cat.categories:
    for d in ('DOWN','UP'):
        S=T[(T.bucket==b)&(T.first==d)]
        if len(S)<100: continue
        m=S.ret_rest.mean(); se=S.ret_rest.std()/len(S)**.5
        print(f"{b:<12} {d:<5} {len(S):>6} {m*100:>15.3f}% {m/se:>7.1f}")
    print()

print("DK's question directly: is the DOWN-minus-UP gap a function of the trend?")
print(f"{'regime':<12} {'DOWN':>9} {'UP':>9} {'DOWN-UP':>9}")
for b in T.bucket.cat.categories:
    D=T[(T.bucket==b)&(T.first=='DOWN')]; U=T[(T.bucket==b)&(T.first=='UP')]
    if len(D)<100 or len(U)<100: continue
    print(f"{b:<12} {D.ret_rest.mean()*100:>8.3f}% {U.ret_rest.mean()*100:>8.3f}% "
          f"{(D.ret_rest.mean()-U.ret_rest.mean())*100:>8.3f}%")
