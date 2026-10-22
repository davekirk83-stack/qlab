"""Liquidation-cascade proxy study (doc 110 step 1). Cascade = 15-min bar with an open-interest drop in the extreme tail
AND a range >= 2 ATR. Control = equally wide bars with no OI drop. Session behaviour after each, BTC, Sep 2025 -> Oct 2026."""
import numpy as np, pandas as pd
oi=pd.read_csv("data_oi/BTCUSDT.csv",parse_dates=["create_time"]).set_index("create_time").sort_index()
oi=oi[["sum_open_interest","sum_taker_long_short_vol_ratio"]].resample("15min").last()
p=pd.read_csv("data_15m/BTCUSD.csv"); p["ts"]=pd.to_datetime(p.iloc[:,0]).dt.tz_localize(None); p=p.set_index("ts")[["open","high","low","close"]]
d=p.join(oi,how="inner").dropna(); d["doi"]=d.sum_open_interest.pct_change()*100
tr=np.maximum(d.high-d.low,np.maximum((d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs())); d["atr"]=tr.rolling(96).mean().shift(1)
d["rng"]=(d.high-d.low)/d.atr; d["ret"]=d.close/d.open-1
h=d.index.hour; d["sess"]=np.select([h<7,h<13,h<20],["asia","london","ny"],"late")
lo_tail=d.doi.quantile(0.02); print(f"bars {len(d)}  {d.index[0]} -> {d.index[-1]}  OI-drop 2% tail = {lo_tail:.2f}% per 15m")
d["cascade"]=(d.doi<=lo_tail)&(d.rng>=2)
d["bigbar"]=(d.rng>=2)&(d.doi>d.doi.quantile(0.3))   # wide bar, no OI drop (control)
d["side"]=np.where(d.ret<0,"long-cascade(down)","short-cascade(up)")
print("\ncascades",d.cascade.sum(),"| control big bars",d.bigbar.sum())
print(pd.crosstab(d.sess[d.cascade],d.side[d.cascade]))
C=d.close.values; H=d.high.values; L=d.low.values; idx=d.index; n=len(d)
def fwd(i,k): return C[min(i+k,n-1)]/C[i]-1
def extreme_retest(i,k,down):   # does price return to the cascade bar's extreme within k bars (after first moving 0.5 ATR away)?
    ext=L[i] if down else H[i]; a=d.atr.values[i]
    away=False
    for j in range(i+1,min(i+k,n)):
        if not away: away = (C[j]-ext>=0.5*a) if down else (ext-C[j]>=0.5*a); continue
        if (down and L[j]<=ext) or ((not down) and H[j]>=ext): return True
    return False
def beyond(i,k,down):  # does price continue beyond the cascade extreme by >=1 ATR within k bars
    ext=L[i] if down else H[i]; a=d.atr.values[i]
    return (L[i+1:i+k].min()<=ext-a) if down else (H[i+1:i+k].max()>=ext+a)
rows=[]
for name,mask in (("cascade",d.cascade),("big bar, no OI drop",d.bigbar)):
    ii=np.where(mask.values)[0]; ii=ii[(ii>100)&(ii<n-100)]
    for i in ii:
        down=d.ret.values[i]<0; s=-1 if down else 1
        rows.append(dict(kind=name,sess=d.sess.values[i],down=down,
            cont1h=s*fwd(i,4)*100, cont4h=s*fwd(i,16)*100, cont24h=s*fwd(i,96)*100,
            retest24h=extreme_retest(i,96,down), beyond4h=beyond(i,16,down), beyond24h=beyond(i,96,down)))
r=pd.DataFrame(rows)
print("\n(cont = return in the cascade's direction, %; retest = price comes back to the cascade extreme within 24h; beyond = continues >=1 ATR past it)")
g=r.groupby(["kind","down"]).agg(n=("cont1h","size"),cont1h=("cont1h","mean"),cont4h=("cont4h","mean"),cont24h=("cont24h","mean"),retest24h=("retest24h","mean"),beyond4h=("beyond4h","mean"),beyond24h=("beyond24h","mean")).round(3)
print(g.to_string())
print("\nby session (cascades only):"); print(r[r.kind=="cascade"].groupby(["sess","down"]).agg(n=("cont1h","size"),cont4h=("cont4h","mean"),cont24h=("cont24h","mean"),retest24h=("retest24h","mean"),beyond24h=("beyond24h","mean")).round(3).to_string())
# session-level: after an Asia long-cascade, does NY take the Asia low or the Asia high first?
d["day"]=d.index.floor("D"); out=[]
for day,g in d.groupby("day"):
    a=g[g.sess=="asia"]; ny=g[g.sess=="ny"]
    if len(a)<20 or len(ny)<20: continue
    al,ah=a.low.min(),a.high.max(); casc=a[a.cascade]
    first=None
    for t,row in ny.iterrows():
        if row.low<=al: first="low"; break
        if row.high>=ah: first="high"; break
    out.append(dict(day=day,asia_casc=("long" if (casc.ret<0).any() else "short" if len(casc) else "none"),first=first,ny_ret=ny.close.iloc[-1]/ny.open.iloc[0]-1))
o=pd.DataFrame(out); print("\nNY vs Asia box, by whether Asia had a cascade:")
print(o.groupby("asia_casc").agg(n=("first","size"),low_first=("first",lambda s:(s=="low").mean()),high_first=("first",lambda s:(s=="high").mean()),ny_up=("ny_ret",lambda s:(s>0).mean()),ny_mean=("ny_ret","mean")).round(3).to_string())
# fuel: OI build over 24h (top decile) with flat price -> next 24h range and direction vs taker skew
d["oi24"]=d.sum_open_interest.pct_change(96)*100; d["px24"]=d.close.pct_change(96)*100; d["rng24f"]=(d.high.rolling(96).max().shift(-96)-d.low.rolling(96).min().shift(-96))/d.close*100; d["ret24f"]=d.close.shift(-96)/d.close-1
hi=d.oi24.quantile(0.9); fuel=d[(d.oi24>=hi)&(d.px24.abs()<1)]; base=d.dropna(subset=["rng24f"])
print(f"\nFUEL: OI +{hi:.1f}%/24h (top decile) with |price|<1%: n {len(fuel)}  next-24h range {fuel.rng24f.mean():.2f}% vs base {base.rng24f.mean():.2f}%; next-24h up {(fuel.ret24f>0).mean():.0%} (base {(base.ret24f>0).mean():.0%})")
tk=fuel.sum_taker_long_short_vol_ratio; print(f"  taker ratio>1 (crowd buying) -> next 24h {fuel[tk>1].ret24f.mean()*100:+.2f}% (n{(tk>1).sum()}); taker<1 -> {fuel[tk<1].ret24f.mean()*100:+.2f}% (n{(tk<1).sum()})")

# significance of the fuel lean (overlapping 24h windows -> thin to one obs per 24h)
f=fuel.ret24f.dropna(); f=f[~f.index.duplicated()]; fd=f.resample("24h").first().dropna()
bd=base.ret24f.resample("24h").first().dropna()
import scipy.stats as st
print(f"\nfuel thinned to daily: n {len(fd)} mean {fd.mean()*100:+.2f}% vs base {bd.mean()*100:+.2f}%  t={st.ttest_ind(fd,bd,equal_var=False).statistic:+.2f}")
half=fd.index[len(fd)//2]; print(f"  H1 {fd[:half].mean()*100:+.2f}% (n{len(fd[:half])})  H2 {fd[half:].mean()*100:+.2f}% (n{len(fd[half:])})")
for name,m in (("crowd long (taker>1)",fuel.sum_taker_long_short_vol_ratio>1),("crowd short",fuel.sum_taker_long_short_vol_ratio<1)):
    x=fuel[m].ret24f.dropna(); x=x[~x.index.duplicated()].resample("24h").first().dropna()
    print(f"  {name}: daily n {len(x)} mean {x.mean()*100:+.2f}% t={st.ttest_ind(x,bd,equal_var=False).statistic:+.2f}")
