"""Second pass on the two leads from golden_tight.py, plus the fixed 'confirmed' gate."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X, golden_scaled as G, golden_tight as T
X.CAP = 180; X.X_MIN_GAP = 2
RNG = np.random.default_rng(5)

def entries(P, s, gate):
    p = P[s]; C, L, ef, es, a, up = p["C"], p["L"], p["ef"], p["es"], p["a"], p["up"]
    idx = np.where(up)[0]; idx = idx[(idx > 250) & (idx < len(C)-2)]
    btc = P.get("BTCUSD"); out = []
    for i in idx:
        j = i
        if "pullback" in gate:
            j = None
            for k in range(i+1, min(i+31, len(C)-2)):
                if ef[k] < es[k]: break
                if L[k] <= ef[k] and C[k] > ef[k]: j = k; break
            if j is None: continue
        if "confirmed" in gate:
            j = None
            for k in range(i+1, min(i+21, len(C)-2)):
                if ef[k] < es[k]: break
                if C[k] > ef[k] > es[k] and (ef[k]-es[k]) > 0.5*a[k]: j = k; break
            if j is None: continue
        if "bull" in gate:
            t = p["idx"][j]; kb = int(np.searchsorted(btc["idx"], t, side="right")) - 1
            if kb < 0 or btc["C"][kb] <= btc["e200"][kb]: continue
        if "slope" in gate and not (es[j] > es[j-10]): continue
        if "notUS" in gate and 13 <= p["idx"][j].hour < 21: continue
        if "alts" in gate and s in T.MAJ: continue
        out.append(j)
    return out

def run(P, gate, exit_fn):
    rows, ctrl = [], []
    for s in P:
        p = P[s]; C, H, L, a = p["C"], p["H"], p["L"], p["a"]; last = -10**9
        for i in entries(P, s, gate):
            if i - last < X.X_MIN_GAP: continue
            last = i
            r, b, _ = exit_fn(C, H, L, a, i, 1); rows.append((s, p["idx"][i].year, r, b))
            j = int(RNG.integers(250, len(C)-2)); r2, _, _ = exit_fn(C, H, L, a, j, 1); ctrl.append((s, p["idx"][j].year, r2, 0))
    return pd.DataFrame(rows, columns=["sym","y","ret","bars"]), pd.DataFrame(ctrl, columns=["sym","y","ret","bars"])

def line(gate, ename, R, Cc):
    if len(R) < 60: print(f"  {gate:<22}{ename:<9}{len(R):>6} too few"); return
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    by = R.groupby("sym").ret.mean()-Cc.groupby("sym").ret.mean(); byy = R.groupby("y").ret.mean()-Cc.groupby("y").ret.mean()
    print(f"  {gate:<22}{ename:<9}{len(R):>6,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>5.0f}"
          f"{Cc.ret.mean()*100:>+8.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>8.0f}%{(byy>0).sum():>4}/{len(byy)}", flush=True)

data = X.load()
hdr = f"  {'gate':<22}{'exit':<9}{'n':>6}{'per ep':>9}{'t':>6}{'win':>6}{'hold':>5}{'ctrl':>9}{'edge':>7}{'coins':>9}{'yrs':>6}"
P = T.build(data, "4h"); print("4-HOUR, cross 20/50 LONG"); print(hdr)
for gate in ["confirmed", "bull", "bull+slope", "bull+notUS", "bull+confirmed", "bull+alts", "bull+slope+notUS"]:
    for ename, efn in (("scaled", G.scaled), ("hold 12", lambda *q: G.hold(*q, 12)), ("hold 24", lambda *q: G.hold(*q, 24))):
        R, Cc = run(P, gate, efn); line(gate, ename, R, Cc)
R, Cc = run(P, "bull", G.scaled)
print("  bull/scaled by year:", {int(y): f"{v*100:+.2f}/{c*100:+.2f}" for (y, v), c in zip(R.groupby('y').ret.mean().items(), Cc.groupby('y').ret.mean())})
P = T.build(data, "1D"); print("\nDAILY, cross 20/50 LONG"); print(hdr)
for gate in ["confirmed", "bull", "pullback", "bull+pullback", "bull+pullback+slope", "bull+pullback+alts", "bull+confirmed"]:
    for ename, efn in (("scaled", G.scaled), ("hold 10", lambda *q: G.hold(*q, 10)), ("hold 20", lambda *q: G.hold(*q, 20)), ("trail 3", lambda C,H,L,a,i,s: X.trail(C,H,L,a,i,s,3)[:2]+("t",))):
        R, Cc = run(P, gate, efn); line(gate, ename, R, Cc)
R, Cc = run(P, "bull+pullback", G.scaled)
print("  bull+pullback/scaled by year:", {int(y): f"{v*100:+.2f}/{c*100:+.2f} n={n}" for (y, v), c, n in zip(R.groupby('y').ret.mean().items(), Cc.groupby('y').ret.mean(), R.groupby('y').size())})
print("  per coin (top/bottom 5):", R.groupby("sym").ret.mean().sort_values().round(4).iloc[[0,1,2,3,4,-5,-4,-3,-2,-1]].to_dict())
