"""
OPEN INTEREST SPIKES — DK: a crowd piling in late, then getting taken out.

Real OI data (Binance archive), 5-min resolution, 8 symbols, 400 days.
Unlike volume, OI tells you whether positions are being OPENED or CLOSED.

Key distinction, which is the whole point:
  OI UP   + price UP   = new LONGS entering          (late longs -> squeeze fuel)
  OI UP   + price DOWN = new SHORTS entering
  OI DOWN + price UP   = shorts COVERING             (exhaustion)
  OI DOWN + price DOWN = longs capitulating
"""
import os, numpy as np, pandas as pd
OI="/home/claude/qlab/data_oi"; PX="/home/claude/qlab/data_1h"
SY=[f[:-4] for f in sorted(os.listdir(OI)) if f.endswith(".csv")
    and os.path.exists(f"{PX}/{f}")]

def joined(s):
    o=pd.read_csv(f"{OI}/{s}.csv",parse_dates=["create_time"]).set_index("create_time").sort_index()
    o=o.select_dtypes("number").resample("1h").last()
    p=pd.read_csv(f"{PX}/{s}.csv",parse_dates=["date"]).set_index("date").sort_index()
    p=p[~p.index.duplicated()]
    d=p.join(o.reindex(p.index,method="ffill").shift(1),how="inner").dropna(subset=["close"])
    d=d.dropna(subset=["sum_open_interest"])
    d["oi"]=d.sum_open_interest
    d["oi_chg"]=d.oi.pct_change(6)                    # 6h change
    d["oi_z"]=((d.oi_chg-d.oi_chg.rolling(168).mean())/d.oi_chg.rolling(168).std())
    d["px_chg"]=d.close.pct_change(6)
    d["ret"]=d.close.pct_change()
    return d.dropna()

def fwd(d,n): return d.close.shift(-n)/d.close-1

acc={}
for s in SY:
    try: d=joined(s)
    except Exception: continue
    if len(d)<2000: continue
    for n in (6,24,72):
        f=fwd(d,n)
        acc.setdefault(("baseline",n),[]).extend(f.dropna().values)
        spike=d.oi_z>2
        acc.setdefault(("OI spike (z>2)",n),[]).extend(f[spike].dropna().values)
        acc.setdefault(("OI up + price UP (new longs)",n),[]).extend(f[spike&(d.px_chg>0)].dropna().values)
        acc.setdefault(("OI up + price DOWN (new shorts)",n),[]).extend(f[spike&(d.px_chg<0)].dropna().values)
        drop=d.oi_z<-2
        acc.setdefault(("OI DROP + price UP (short cover)",n),[]).extend(f[drop&(d.px_chg>0)].dropna().values)
        acc.setdefault(("OI DROP + price DOWN (capitulation)",n),[]).extend(f[drop&(d.px_chg<0)].dropna().values)
        # the specific DK case: big OI build on a big up move = late longs
        late=spike&(d.px_chg>0.03)
        acc.setdefault(("LATE LONGS (OI z>2 + price +3%)",n),[]).extend(f[late].dropna().values)

print(f"OPEN INTEREST SPIKES — real OI, {len(SY)} symbols, hourly\n")
for n in (6,24,72):
    print(f"  forward {n}h:")
    for k in ("baseline","OI spike (z>2)","OI up + price UP (new longs)",
              "OI up + price DOWN (new shorts)","OI DROP + price UP (short cover)",
              "OI DROP + price DOWN (capitulation)","LATE LONGS (OI z>2 + price +3%)"):
        v=acc.get((k,n))
        if v and len(v)>=60:
            v=np.array(v); t=v.mean()/(v.std()/np.sqrt(len(v)))
            print(f"    {k:38s} n={len(v):6d}  fwd {v.mean()*100:+7.3f}%  t={t:+6.2f}  "
                  f"up {float((v>0).mean())*100:5.1f}%")
    print()
