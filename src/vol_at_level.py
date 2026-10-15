"""
VOLUME AT A LEVEL — DK's actual claim, which my first test did not measure.

DK: "when a price trend meets a major reversal point, big volume comes in to
push it back the other way."

The claim is conditional on LOCATION, not on volume alone. A spike mid-range is
a different event from a spike into major resistance. Tested here:

  spike AT a major high  (50d / 100d / 200d)  -> does price REVERSE DOWN?
  spike AT a major low                        -> does price REVERSE UP?
  spike MID-RANGE                             -> the control
and the key discriminator: at the level, does a spike reverse MORE OFTEN than
a non-spike touch of the same level?
"""
import os, numpy as np, pandas as pd
D="/home/claude/qlab/data"
SY=[f[:-4] for f in sorted(os.listdir(D)) if f.endswith(".csv") and not f.startswith("_")]

def load(s):
    d=pd.read_csv(f"{D}/{s}.csv"); d["date"]=pd.to_datetime(d["date"],errors="coerce")
    d=d.dropna(subset=["date"]).set_index("date").sort_index()
    d=d[~d.index.duplicated()]
    d["vspike"]=d.volume/d.volume.rolling(20).mean()
    for n in (50,100,200):
        d[f"hi{n}"]=d.high.rolling(n).max()
        d[f"lo{n}"]=d.low.rolling(n).min()
    d["pos50"]=(d.close-d.lo50)/(d.hi50-d.lo50)
    return d.dropna()

acc={}
for s in SY:
    try: d=load(s)
    except Exception: continue
    if len(d)<600: continue
    for n in (1,3,5,10):
        f=d.close.shift(-n)/d.close-1
        spike=d.vspike>2.5
        for lb in (50,100,200):
            at_hi=d.close>=d[f"hi{lb}"]*0.99     # within 1% of the N-day high
            at_lo=d.close<=d[f"lo{lb}"]*1.01
            acc.setdefault((f"spike AT {lb}d HIGH",n),[]).extend(f[spike&at_hi].dropna().values)
            acc.setdefault((f"NO spike at {lb}d HIGH",n),[]).extend(f[(~spike)&at_hi].dropna().values)
            acc.setdefault((f"spike AT {lb}d LOW",n),[]).extend(f[spike&at_lo].dropna().values)
            acc.setdefault((f"NO spike at {lb}d LOW",n),[]).extend(f[(~spike)&at_lo].dropna().values)
        mid=(d.pos50>0.35)&(d.pos50<0.65)
        acc.setdefault(("spike MID-RANGE",n),[]).extend(f[spike&mid].dropna().values)
        acc.setdefault(("baseline",n),[]).extend(f.dropna().values)

print("VOLUME AT A LEVEL — does a spike at resistance/support reverse price?\n")
print(f"  {len(SY)} instruments, daily bars, spike = volume > 2.5x 20-day average\n")
for n in (1,3,5,10):
    print(f"  ── forward {n} day(s) ──")
    rows=["baseline","spike MID-RANGE",
          "spike AT 50d HIGH","NO spike at 50d HIGH",
          "spike AT 100d HIGH","NO spike at 100d HIGH",
          "spike AT 200d HIGH","NO spike at 200d HIGH",
          "spike AT 50d LOW","NO spike at 50d LOW",
          "spike AT 100d LOW","NO spike at 100d LOW",
          "spike AT 200d LOW","NO spike at 200d LOW"]
    for k in rows:
        v=acc.get((k,n))
        if v and len(v)>=60:
            v=np.array(v); t=v.mean()/(v.std()/np.sqrt(len(v)))
            mark=""
            if "spike AT" in k and "HIGH" in k and v.mean()<0: mark="  <- reverses DOWN"
            if "spike AT" in k and "LOW" in k and v.mean()>0: mark="  <- reverses UP"
            print(f"    {k:26s} n={len(v):6d}  fwd {v.mean()*100:+7.3f}%  t={t:+6.2f}  "
                  f"up {float((v>0).mean())*100:5.1f}%{mark}")
    print()
