"""Exit-free check of the delta ingredient: barrier race P(+k ATR before -k ATR) and fixed-horizon returns
after strong taker imbalances, with and without trend agreement, plus absorption (price down, delta up)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, glob, os
import flow_score as F
RNG = np.random.default_rng(1)
def race(H, L, C, a, i, s, k, horizon=48):
    e = C[i]
    for j in range(i+1, min(i+horizon+1, len(C))):
        up = (H[j] >= e + k*a[i]) if s == 1 else (L[j] <= e - k*a[i]); dn = (L[j] <= e - k*a[i]) if s == 1 else (H[j] >= e + k*a[i])
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan
def fwd(C, i, s, n): return s*(C[min(i+n, len(C)-1)]/C[i] - 1)
syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{F.D1M}/*.csv")) if os.path.exists(f"{F.DOI}/{os.path.basename(f)[:-4]}.csv")]
B = {s: F.features(F.load(s)) for s in syms}
def study(name, cond_fn):
    out = {"race1": [], "race2": [], "f6": [], "f24": [], "f96": [], "cr1": [], "cr2": [], "cf6": [], "cf24": [], "cf96": [], "n": 0}
    for sym, b in B.items():
        H, L, C, a = b.high.values, b.low.values, b.close.values, b.atr.values
        for s in (1, -1):
            sig = cond_fn(b, s).values; idx = np.where(sig)[0]; idx = idx[(idx > 300) & (idx < len(C)-100)]
            last = -99
            for i in idx:
                if i - last < 6: continue
                last = i
                out["race1"].append(race(H,L,C,a,i,s,1)); out["race2"].append(race(H,L,C,a,i,s,2))
                out["f6"].append(fwd(C,i,s,6)); out["f24"].append(fwd(C,i,s,24)); out["f96"].append(fwd(C,i,s,96))
                j = int(RNG.integers(300, len(C)-100))
                out["cr1"].append(race(H,L,C,a,j,s,1)); out["cr2"].append(race(H,L,C,a,j,s,2))
                out["cf6"].append(fwd(C,j,s,6)); out["cf24"].append(fwd(C,j,s,24)); out["cf96"].append(fwd(C,j,s,96))
    n = len(out["f6"]); m = lambda k: np.nanmean(out[k])
    print(f"  {name:<34}{n:>8,}  race1 {m('race1')*100:4.1f}% vs {m('cr1')*100:4.1f}%   race2 {m('race2')*100:4.1f}% vs {m('cr2')*100:4.1f}%"
          f"   fwd30m {m('f6')*1e4:+5.1f}bp vs {m('cf6')*1e4:+5.1f}   2h {m('f24')*1e4:+5.1f} vs {m('cf24')*1e4:+5.1f}   8h {m('f96')*1e4:+5.1f} vs {m('cf96')*1e4:+5.1f}", flush=True)
print("Exit-free: share reaching +k ATR before -k ATR within 4h, and raw forward return (bp, signed by side), vs random. Costs not deducted.\n")
study("delta z>1.5", lambda b,s: (b.dz*s > 1.5))
study("delta z>2.5", lambda b,s: (b.dz*s > 2.5))
study("delta z>3.5", lambda b,s: (b.dz*s > 3.5))
study("delta z>2.5 + trend agrees", lambda b,s: (b.dz*s > 2.5) & ((b.trend==1) if s==1 else (b.trend==0)))
study("delta z>2.5 + trend + Asia", lambda b,s: (b.dz*s > 2.5) & ((b.trend==1) if s==1 else (b.trend==0)) & (b.hour<8))
study("delta z>2.5 AGAINST trend (fade)", lambda b,s: (b.dz*s > 2.5) & ((b.trend==0) if s==1 else (b.trend==1)))
study("raw 5m delta >+0.3 (buy 65%+)", lambda b,s: (b.delta*s > 0.3))
study("absorption: px -1ATR/3bars, delta z>+1.5", lambda b,s: ((b.close-b.close.shift(3))*s < -1.0*b.atr) & (b.dz*s > 1.5))
study("exhaustion: px +1ATR/3bars, delta z<-1.5 (fade)", lambda b,s: ((b.close-b.close.shift(3))*s > 1.0*b.atr) & (b.dz*s < -1.5))
study("trend + vwap + level, no delta", lambda b,s: ((b.trend==1) if s==1 else (b.trend==0)) & ((b.close>b.vwap) if s==1 else (b.close<b.vwap)) & (np.minimum(np.abs(b.close-b.vwap), np.minimum(np.abs(b.close-b.pdh), np.abs(b.close-b.pdl))) < 0.5*b.atr))
