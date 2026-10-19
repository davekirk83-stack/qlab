"""Refinements on Golden-cross long v1 (bull + confirmed, hold 18, 3-ATR stop). Each vs the same exit on random entries."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X, golden_scaled as G, golden_tight as T, golden_tight2 as T2, golden_verify as V
X.CAP = 180; X.X_MIN_GAP = 2
RNG = np.random.default_rng(3)

def base(C,H,L,a,i,s): return V.hold_stop(C,H,L,a,i,s,18,3.0)
def scale_half(C,H,L,a,i,s):
    """half off at +2 ATR, stop to breakeven on the rest, rest held to 18 or stopped"""
    e=C[i]; atr=a[i]; stop=e-3*atr; pnl=0; rem=1.0; be=False
    for j in range(i+1, min(i+19, len(C))):
        if L[j] <= stop: return pnl + rem*((stop/e-1)-X.COST), j-i, "stop"
        if not be and H[j] >= e+2*atr: pnl += 0.5*((2*atr/e)-X.COST); rem=0.5; stop=e*(1+2*X.COST); be=True
    j=min(i+18,len(C)-1); return pnl + rem*((C[j]/e-1)-X.COST), j-i, "hold"
def ride(C,H,L,a,i,s):
    """hold while EMA20 > EMA50 (ribbon intact), 3-ATR stop, cap 60"""
    e=C[i]; stop=e-3*a[i]
    ef=pd.Series(C[:i+61]).ewm(span=20,adjust=False).mean().values; es=pd.Series(C[:i+61]).ewm(span=50,adjust=False).mean().values
    for j in range(i+1, min(i+61, len(C))):
        if L[j] <= stop: return (stop/e-1)-X.COST, j-i, "stop"
        if j < len(ef) and ef[j] < es[j]: return (C[j]/e-1)-X.COST, j-i, "ribbon"
    j=min(i+60,len(C)-1); return (C[j]/e-1)-X.COST, j-i, "cap"
def trail_wide(C,H,L,a,i,s):
    """hold 18 but trail 4 ATR from best after +2 ATR reached"""
    e=C[i]; atr=a[i]; stop=e-3*atr; best=e; armed=False
    for j in range(i+1, min(i+19, len(C))):
        if L[j] <= stop: return (stop/e-1)-X.COST, j-i, "stop"
        best=max(best,H[j])
        if best >= e+2*atr: armed=True
        if armed: stop=max(stop, best-4*atr)
    j=min(i+18,len(C)-1); return (C[j]/e-1)-X.COST, j-i, "hold"

def entries(P, s, variant):
    idx = T2.entries(P, s, "bull+confirmed"); p = P[s]; out=[]
    C, a, ef, es = p["C"], p["a"], p["ef"], p["es"]
    vol = p.get("vol")
    last=-10**9
    for j in idx:
        if variant == "strong" and not ((ef[j]-es[j]) > 0.8*a[j]): continue
        if variant == "fresh" and not ((ef[j]-es[j]) < 1.2*a[j]): continue
        if variant == "cooldown24" and j-last < 24: continue
        if variant == "slope" and not (es[j] > es[j-10]): continue
        if variant == "above200" and not (C[j] > p["e200"][j]): continue
        if variant == "notweekend" and p["idx"][j].dayofweek >= 5: continue
        if variant == "asia" and not (0 <= p["idx"][j].hour < 8): continue
        out.append(j); last=j
    return out

def run(P, variant, efn):
    rows, ctrl = [], []
    for s in P:
        p=P[s]; C,H,L,a = p["C"],p["H"],p["L"],p["a"]
        for i in entries(P, s, variant):
            r,b,how = efn(C,H,L,a,i,1); rows.append((s,p["idx"][i].year,r,b))
            for _ in range(3):
                j=int(RNG.integers(250,len(C)-2)); r2,_,_=efn(C,H,L,a,j,1); ctrl.append((s,p["idx"][j].year,r2,0))
    return pd.DataFrame(rows,columns=["sym","y","ret","bars"]), pd.DataFrame(ctrl,columns=["sym","y","ret","bars"])

def line(lbl,R,Cc):
    if len(R)<60: print(f"  {lbl:<34}{len(R):>6} too few"); return
    t=R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R))); by=R.groupby("sym").ret.mean()-Cc.groupby("sym").ret.mean(); byy=R.groupby("y").ret.mean()-Cc.groupby("y").ret.mean()
    top=R.ret.nlargest(max(1,len(R)//20)).sum()/R.ret.sum()*100 if R.ret.sum()>0 else float('nan')
    print(f"  {lbl:<34}{len(R):>6,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>5.0f}{Cc.ret.mean()*100:>+8.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>7.0f}%{(byy>0).sum():>3}/{len(byy)}{R.ret.min()*100:>+8.1f}%{top:>7.0f}%", flush=True)

data = X.load(); P = T.build(data, "4h")
print("Golden-cross long v1 refinements (bull+confirmed base), 4h, 27 coins, 3 controls/trade")
print(f"  {'variant':<34}{'n':>6}{'per ep':>9}{'t':>6}{'win':>6}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>8}{'yrs':>6}{'worst':>9}{'top5%':>8}")
for lbl, efn in (("REGISTERED hold18 stop3", base), ("half off +2ATR, BE, hold18", scale_half), ("ride ribbon, stop3, cap60", ride), ("hold18, trail 4ATR after +2", trail_wide)):
    R,Cc = run(P,"base",efn); line(lbl,R,Cc)
print()
for v in ("strong","fresh","cooldown24","slope","above200","notweekend","asia"):
    R,Cc = run(P,v,base); line(f"gate {v} (hold18 stop3)",R,Cc)
