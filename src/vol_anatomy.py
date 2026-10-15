"""
THE ANATOMY OF A HIGH-VOLUME MOMENT — what is actually happening?

Volume alone cannot tell you whether buyers are initiating or sellers are being
stopped out: every trade has both sides. But OPEN INTEREST can, because it says
whether contracts were CREATED or DESTROYED:

    volume high + OI RISING   = new positions opened        -> fresh conviction
    volume high + OI FALLING  = positions closed            -> stops, liquidations,
                                                               profit-taking
    volume high + OI FLAT     = transfer between holders    -> churn / rotation

And TAKER FLOW says who was the aggressor — who crossed the spread and paid up.

Cross those with price direction and you can name the event:

  price UP   + OI UP   + taker BUY   = genuine demand, new longs initiating
  price UP   + OI DOWN               = SHORT COVERING - forced, not demand
  price DOWN + OI UP   + taker SELL  = genuine supply, new shorts initiating
  price DOWN + OI DOWN               = LONG LIQUIDATION - stops being hit

Then measure what each one actually predicts.
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
    d=p.join(o.reindex(p.index,method="ffill"),how="inner")
    d=d.dropna(subset=["close","sum_open_interest"])
    d["vol_z"]=(d.volume-d.volume.rolling(168).mean())/d.volume.rolling(168).std()
    d["oi_chg"]=d.sum_open_interest.pct_change()
    d["px_chg"]=d.close.pct_change()
    d["taker"]=d.sum_taker_long_short_vol_ratio
    d["taker_z"]=(d.taker-d.taker.rolling(168).mean())/d.taker.rolling(168).std()
    return d.dropna()

acc={}; shares={}
for s in SY:
    try: d=joined(s)
    except Exception: continue
    if len(d)<2000: continue
    hv=d.vol_z>2                               # a high-volume hour
    up=d.px_chg>0; oiup=d.oi_chg>0
    cells={
      "price UP   + OI UP   (new longs)":      hv&up&oiup,
      "price UP   + OI DOWN (short covering)": hv&up&(~oiup),
      "price DOWN + OI UP   (new shorts)":     hv&(~up)&oiup,
      "price DOWN + OI DOWN (long liquidation)":hv&(~up)&(~oiup),
    }
    for k,m in cells.items():
        shares[k]=shares.get(k,0)+int(m.sum())
    for n in (6,24,72):
        f=d.close.shift(-n)/d.close-1
        acc.setdefault(("baseline",n),[]).extend(f.dropna().values)
        acc.setdefault(("ALL high-volume hours",n),[]).extend(f[hv].dropna().values)
        for k,m in cells.items():
            acc.setdefault((k,n),[]).extend(f[m].dropna().values)
    # how big is the move ON the high-volume bar itself, by type?
    for k,m in cells.items():
        acc.setdefault((k+" |move|",0),[]).extend(d.px_chg[m].abs().dropna().values)

tot=sum(shares.values())
print("ANATOMY OF HIGH-VOLUME MOMENTS — real OI + taker flow, 8 symbols, hourly\n")
print("="*88)
print("  WHAT IS A HIGH-VOLUME HOUR ACTUALLY MADE OF?")
print("="*88)
for k,v in sorted(shares.items(),key=lambda x:-x[1]):
    print(f"    {k:42s} {v:6d}  {v/tot*100:5.1f}% of high-volume hours")
print()
print("="*88)
print("  WHAT DOES EACH TYPE PREDICT?")
print("="*88)
for n in (6,24,72):
    print(f"\n  forward {n}h:")
    for k in ("baseline","ALL high-volume hours",
              "price UP   + OI UP   (new longs)",
              "price UP   + OI DOWN (short covering)",
              "price DOWN + OI UP   (new shorts)",
              "price DOWN + OI DOWN (long liquidation)"):
        v=acc.get((k,n))
        if v and len(v)>=100:
            v=np.array(v); t=v.mean()/(v.std()/np.sqrt(len(v)))
            print(f"    {k:42s} n={len(v):6d}  fwd {v.mean()*100:+7.3f}%  t={t:+6.2f}  "
                  f"up {float((v>0).mean())*100:5.1f}%")
print()
print("="*88)
print("  HOW VIOLENT IS THE BAR ITSELF?  (mean absolute move on the high-volume hour)")
print("="*88)
for k in list(shares):
    v=acc.get((k+" |move|",0))
    if v: print(f"    {k:42s} {np.mean(v)*100:6.3f}%")
