"""BTC around the CME futures reopen on Sunday (avenue 2, 26 Oct 2026). CME Bitcoin futures halt Fri 16:00 CT and reopen Sun 17:00 CT
(= 22:00 UTC in US summer time, 23:00 UTC in winter). Coinbase BTC-USD 15-min, Oct 2021 - Oct 2026. Questions:
 1. Is the first hour after the reopen biased (vs all other hours, vs other Sunday hours)?
 2. Does the reopen fade the weekend move (Fri CME close -> Sun reopen), i.e. a 'gap fill'?
 3. First 1h / 4h / to Monday 08:00 UTC."""
import numpy as np, pandas as pd
d = pd.read_csv("/home/claude/qlab/data_15m/BTCUSD.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); c = d.close
ct = c.index.tz_convert("America/Chicago")
rows = []
for sun in pd.date_range(c.index[0].normalize(), c.index[-1].normalize(), freq="W-SUN", tz="UTC"):
    sun_ct = pd.Timestamp(sun.date()).tz_localize("America/Chicago")
    reopen = (sun_ct + pd.Timedelta(hours=17)).tz_convert("UTC"); friclose = (sun_ct - pd.Timedelta(days=2) + pd.Timedelta(hours=16)).tz_convert("UTC")
    def px(t):
        k = c.index.searchsorted(t); return c.iloc[k-1] if 0 < k <= len(c) else np.nan
    p_f, p_o = px(friclose), px(reopen)
    if np.isnan(p_f) or np.isnan(p_o): continue
    r1, r4 = px(reopen + pd.Timedelta(hours=1))/p_o - 1, px(reopen + pd.Timedelta(hours=4))/p_o - 1
    mon8 = px(pd.Timestamp(sun.date() + pd.Timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=8))/p_o - 1
    pre1 = p_o/px(reopen - pd.Timedelta(hours=1)) - 1
    rows.append(dict(sun=sun.date(), wk=p_o/p_f - 1, pre1=pre1, r1=r1, r4=r4, mon8=mon8))
r = pd.DataFrame(rows).dropna()
hr = c.resample("1h").last().pct_change().dropna()
print(f"weekends {len(r)} ({r.sun.iloc[0]} -> {r.sun.iloc[-1]})")
for k, lab in (("r1", "first hour after reopen"), ("r4", "first 4 hours"), ("mon8", "reopen -> Monday 08:00 UTC")):
    x = r[k]; h = len(x)//2
    print(f"  {lab:28s} mean {x.mean()*100:+.3f}%  median {x.median()*100:+.3f}%  up {100*(x>0).mean():.0f}%  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  H1 {x.iloc[:h].mean()*100:+.3f} H2 {x.iloc[h:].mean()*100:+.3f}")
print(f"  baseline: any 1h {hr.mean()*100:+.3f}% (sd {hr.std()*100:.2f}%), |first hour| median {r.r1.abs().median()*100:.2f}% vs |any hour| median {hr.abs().median()*100:.2f}%")
print("\n  gap-fill: does the reopen fade the weekend move?")
for lab, m in (("weekend up > +1%", r.wk > 0.01), ("weekend down < -1%", r.wk < -0.01), ("weekend flat", r.wk.abs() <= 0.01)):
    s = r[m]
    if len(s) < 5: continue
    print(f"    {lab:20s} n {len(s):3d}  first hour {s.r1.mean()*100:+.3f}% (up {100*(s.r1>0).mean():.0f}%)  first 4h {s.r4.mean()*100:+.3f}%  to Mon 08:00 {s.mon8.mean()*100:+.3f}%")
print(f"  corr(weekend move, first 4h) {r.wk.corr(r.r4):+.2f}   corr(weekend move, to Mon 08:00) {r.wk.corr(r.mon8):+.2f}")
print("\n  last 6 weekends:"); print(r.tail(6).assign(**{k: (r.tail(6)[k]*100).round(2) for k in ("wk", "r1", "r4", "mon8")})[["sun", "wk", "r1", "r4", "mon8"]].to_string(index=False))
