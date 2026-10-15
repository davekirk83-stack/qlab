"""
VOLUME SPIKES AND REVERSALS.

DK: "when large volume enters, you often see a major reversal."

The idea is exhaustion/climax: a surge of volume marks the last buyers or
sellers being filled, after which price turns. Testable directly.

Tested:
  1. Raw volume spike -> forward returns (no conditioning). Probably nothing.
  2. Volume spike AFTER A RUN -> the climax version. Conditioned on the
     preceding move, because exhaustion only makes sense at an extreme.
  3. Spike WITH a wide range (climax) vs spike with a NARROW range (absorption).
     These are opposite tape-reading signals and should behave differently.
  4. Spike at a 20-bar extreme vs spike mid-range.
Costs applied. Both daily and 15-min.
"""
import os, numpy as np, pandas as pd

def load(path, sym):
    d=pd.read_csv(f"{path}/{sym}.csv")
    d["date"]=pd.to_datetime(d["date"],errors="coerce")
    d=d.dropna(subset=["date"]).set_index("date").sort_index()
    d=d[~d.index.duplicated()]
    d["ret"]=d.close.pct_change()
    d["vma"]=d.volume.rolling(20).mean()
    d["vspike"]=d.volume/d.vma
    d["rng"]=(d.high-d.low)/d.close
    d["rma"]=d.rng.rolling(20).mean()
    d["run5"]=d.close/d.close.shift(5)-1
    d["hi20"]=d.high.rolling(20).max()
    d["lo20"]=d.low.rolling(20).min()
    d["at_hi"]=(d.close>=d.hi20*0.995)
    d["at_lo"]=(d.close<=d.lo20*1.005)
    return d.dropna()

def fwd(d, mask, n):
    f=(d.close.shift(-n)/d.close-1)
    x=f[mask].dropna()
    return x

def line(lbl,x,cost=0.0):
    if len(x)<50: return None
    m=x.mean()-cost; t=m/(x.std()/np.sqrt(len(x)))
    print(f"    {lbl:46s} n={len(x):6d}  fwd {m*100:+7.3f}%  t={t:+6.2f}  "
          f"up {float((x>0).mean())*100:5.1f}%")
    return m

def analyse(path, syms, horizons, label, cost):
    print("="*94); print(f"  {label}"); print("="*94)
    acc={}
    for s in syms:
        try: d=load(path,s)
        except Exception: continue
        if len(d)<500: continue
        for n in horizons:
            f=(d.close.shift(-n)/d.close-1)
            base=f.dropna()
            acc.setdefault(("baseline",n),[]).extend(base.values)
            spike=d.vspike>3
            acc.setdefault(("spike x3",n),[]).extend(f[spike].dropna().values)
            # climax: spike after an UP run -> expect reversal DOWN
            up=spike&(d.run5>0.05)
            dn=spike&(d.run5<-0.05)
            acc.setdefault(("spike after UP run",n),[]).extend(f[up].dropna().values)
            acc.setdefault(("spike after DOWN run",n),[]).extend(f[dn].dropna().values)
            # wide-range spike (climax) vs narrow-range spike (absorption)
            wide=spike&(d.rng>d.rma*1.5); narrow=spike&(d.rng<d.rma*0.8)
            acc.setdefault(("spike + WIDE range",n),[]).extend(f[wide].dropna().values)
            acc.setdefault(("spike + NARROW range",n),[]).extend(f[narrow].dropna().values)
            # at extremes
            acc.setdefault(("spike at 20-bar HIGH",n),[]).extend(f[spike&d.at_hi].dropna().values)
            acc.setdefault(("spike at 20-bar LOW",n),[]).extend(f[spike&d.at_lo].dropna().values)
    for n in horizons:
        print(f"\n  forward {n} bars:")
        for k in ("baseline","spike x3","spike after UP run","spike after DOWN run",
                  "spike + WIDE range","spike + NARROW range",
                  "spike at 20-bar HIGH","spike at 20-bar LOW"):
            v=acc.get((k,n))
            if v: line(k,pd.Series(v),cost)

if __name__=="__main__":
    DD="/home/claude/qlab/data"
    ds=[f[:-4] for f in sorted(os.listdir(DD)) if f.endswith(".csv") and not f.startswith("_")]
    analyse(DD,ds,[1,3,5],"DAILY BARS — 13 instruments",0.0015)
    D15="/home/claude/qlab/data_15m"
    s15=[f[:-4] for f in sorted(os.listdir(D15)) if f.endswith(".csv")]
    analyse(D15,s15,[4,16],"15-MIN BARS — 4 crypto symbols (4 bars = 1h, 16 = 4h)",0.0006)
