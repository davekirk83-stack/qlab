"""Death-cross short on 4h, taken apart: by year, by coin, wider trails, BTC/ETH excluded."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X
X.CAP = 180; X.X_MIN_GAP = 2
data = X.load(); P = {}; IDX = {}
for s, d in data.items():
    d4 = d.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    C, H, L, a = X.prep(d4); IDX[s] = d4.index
    P[s] = (C, H, L, a, {p: X.signals(C, a, *p) for p in [(9,21),(20,50)]})

def run_dated(pair, k, which):
    rows, ctrl = [], []
    for s, (C, H, L, a, sig) in P.items():
        up, dn, au, ad = sig[pair]; src = dn if which == "cross" else ad
        idx = np.where(src)[0]; idx = idx[(idx > 250) & (idx < len(C)-2)]; last = -10**9
        for i in idx:
            if i - last < 2: continue
            last = i
            r, b, br = X.trail(C, H, L, a, i, -1, k); rows.append((s, IDX[s][i].year, r))
            j = int(X.RNG.integers(250, len(C)-2)); r2, b2, br2 = X.trail(C, H, L, a, j, -1, k); ctrl.append((s, IDX[s][j].year, r2))
    return pd.DataFrame(rows, columns=["sym","y","ret"]), pd.DataFrame(ctrl, columns=["sym","y","ret"])

for which in ("cross", "ant"):
    for pair in [(9,21),(20,50)]:
        for k in (3, 4, 5):
            R, C = run_dated(pair, k, which)
            t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
            ex = R[~R.sym.isin(["BTCUSD","ETHUSD"])]; cx = C[~C.sym.isin(["BTCUSD","ETHUSD"])]
            yr = R.groupby("y").ret.mean()*100; cy = C.groupby("y").ret.mean()*100
            pc = (R.groupby("sym").ret.mean() > C.groupby("sym").ret.mean()).mean()
            print(f"{which} {pair[0]}/{pair[1]} SHORT k={k}: n={len(R):,} {R.ret.mean()*100:+.2f}% t={t:+.1f} ctrl {C.ret.mean()*100:+.2f}% | ex BTC/ETH {ex.ret.mean()*100:+.2f}% vs ctrl {cx.ret.mean()*100:+.2f}% | coins beating ctrl {pc*100:.0f}%")
            print("    by year (real / ctrl): " + "  ".join(f"{y}: {yr[y]:+.1f}/{cy.get(y, float('nan')):+.1f}" for y in yr.index))
