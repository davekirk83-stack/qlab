"""Verification of the 4h 'confirmed golden cross, hold N' lead: 5 controls per trade, hold sweep,
wide safety stop, barrier race, by year, split-half, with/without BTC-bull gate."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X, golden_scaled as G, golden_tight as T, golden_tight2 as T2
X.CAP = 180; X.X_MIN_GAP = 2
RNG = np.random.default_rng(99)

def hold_stop(C, H, L, a, i, s, N, k):
    """hold N bars, but a fixed k*ATR stop under entry, worst tick."""
    e = C[i]; stop = e - k*a[i]
    for j in range(i+1, min(i+N+1, len(C))):
        if L[j] <= stop: return (stop/e - 1) - X.COST, j-i, "stop"
    j = min(i+N, len(C)-1); return (C[j]/e - 1) - X.COST, j-i, "hold"

def race(C, H, L, a, i):
    e = C[i]; atr = a[i]
    for j in range(i+1, min(i+181, len(C))):
        up = H[j] >= e+2*atr; dn = L[j] <= e-2*atr
        if up and dn: return 0.5
        if up: return 1.0
        if dn: return 0.0
    return np.nan

def run(P, gate, efn, nctrl=5):
    rows, ctrl = [], []
    for s in P:
        p = P[s]; C, H, L, a = p["C"], p["H"], p["L"], p["a"]; last = -10**9
        for i in T2.entries(P, s, gate):
            if i - last < X.X_MIN_GAP: continue
            last = i
            r, b, how = efn(C, H, L, a, i, 1); rows.append((s, p["idx"][i], r, race(C,H,L,a,i), how))
            for _ in range(nctrl):
                j = int(RNG.integers(250, len(C)-2)); r2, _, _ = efn(C, H, L, a, j, 1); ctrl.append((s, p["idx"][j], r2, race(C,H,L,a,j), ""))
    return pd.DataFrame(rows, columns=["sym","ts","ret","race","how"]), pd.DataFrame(ctrl, columns=["sym","ts","ret","race","how"])

def line(lbl, R, Cc):
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    by = R.groupby("sym").ret.mean()-Cc.groupby("sym").ret.mean()
    print(f"  {lbl:<28}{len(R):>6,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>5.0f}%{Cc.ret.mean()*100:>+8.3f}%"
          f"{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>7.0f}%{R.race.mean()*100:>7.0f}%{Cc.race.mean()*100:>6.0f}%", flush=True)

data = X.load(); P = T.build(data, "4h")
print(f"4-HOUR, confirmed golden cross 20/50 (ribbon open >0.5 ATR, close above EMA20), {len(P)} coins, 5 random controls per trade")
print(f"  {'variant':<28}{'n':>6}{'per ep':>9}{'t':>6}{'win':>6}{'ctrl':>9}{'edge':>7}{'coins':>8}{'race':>8}{'ctrl':>6}")
for gate in ("confirmed", "bull+confirmed"):
    for N in (6, 12, 18, 24, 36):
        R, Cc = run(P, gate, lambda *q, N=N: G.hold(*q, N)); line(f"{gate} hold {N}", R, Cc)
    for k in (2.0, 3.0):
        R, Cc = run(P, gate, lambda *q, k=k: hold_stop(*q, 12, k)); line(f"{gate} hold 12 stop {k}ATR", R, Cc)
    print()
R, Cc = run(P, "confirmed", lambda *q: G.hold(*q, 12))
R["y"] = R.ts.dt.year; Cc["y"] = Cc.ts.dt.year
print("  confirmed hold 12 by year (real / control / n):")
for y in sorted(R.y.unique()):
    print(f"    {y}: {R[R.y==y].ret.mean()*100:+.2f}% / {Cc[Cc.y==y].ret.mean()*100:+.2f}%  n={int((R.y==y).sum())}")
h = len(R)//2; R = R.sort_values("ts")
print(f"  split-half by time: first {R.iloc[:h].ret.mean()*100:+.3f}%  second {R.iloc[h:].ret.mean()*100:+.3f}%")
print(f"  per-coin mean (worst 5): {R.groupby('sym').ret.mean().sort_values().round(4).head(5).to_dict()}")
print(f"  worst single trade {R.ret.min()*100:+.1f}%, 5th pct {R.ret.quantile(.05)*100:+.1f}%, share of P&L from top 5%: {R.ret.nlargest(max(1,len(R)//20)).sum()/R.ret.sum()*100:.0f}%")
print(f"  trades per month across 27 coins: {len(R)/((R.ts.max()-R.ts.min()).days/30.4):.1f}")
