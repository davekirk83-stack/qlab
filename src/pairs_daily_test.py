"""Doc 216 — reviewer 2's pairs trading (relative value, market-neutral). Daily closes, decided at the close, traded at the next open
(both legs). Spread = log(A) - b*log(B), b = rolling 120-day OLS hedge ratio (known at the close); z = (spread - 60d mean)/60d sd.
Enter when |z| > 2 (long the cheap leg, short the rich leg, equal £ notional scaled by b); exit when z crosses 0, or |z| > 3.5 (stop), or 20 days.
Costs per leg per side (F.COST), funding 6%/yr x 1.4 charged on BOTH legs (conservative: an IG short receives the benchmark less admin).
Returns in % of one leg's notional. Pairs fixed in advance (reviewer's list): SPX/DJI, NDX/SPX, GOLD/SILVER, DAX/FTSE, OIL/(none)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
PAIRS = [("SPX", "DJI"), ("NDX", "SPX"), ("GOLD", "SILVER"), ("DAX", "FTSE"), ("SPX", "DAX"), ("NDX", "DJI")]
def pair(a, b, zin=2.0, zout=0.0, zstop=3.5, maxd=20):
    A, B = F.D[a], F.D[b]; ix = A.index.intersection(B.index)
    ca, cb, oa, ob = (np.log(A.close[ix]), np.log(B.close[ix]), A.open[ix], B.open[ix])
    beta = ca.rolling(120).cov(cb) / cb.rolling(120).var(); sp = ca - beta * cb; z = (sp - sp.rolling(60).mean()) / sp.rolling(60).std()
    ok = (abs(A.open[ix] - A.close[ix].shift(1)) > 1e-9) & (abs(B.open[ix] - B.close[ix].shift(1)) > 1e-9)   # real opens only (doc 209)
    Z, BE, OA, OB, OK = z.values, beta.values, oa.values, ob.values, ok.values; cost = F.COST[a] + F.COST.get(b, .0008); fy = 0.06 / 365 * 1.4
    out = []; i = 200; n = len(ix)
    while i < n - 2:
        if not np.isfinite(Z[i]) or abs(Z[i]) < zin or not OK[i + 1]: i += 1; continue
        s = -np.sign(Z[i]); bb = BE[i]; j0 = i + 1; ea, eb = OA[j0], OB[j0]; j = j0; why = None
        while j < n - 1:
            if s * Z[j] > -zout or abs(Z[j]) > zstop or (j - j0) >= maxd: break
            j += 1
        if j + 1 >= n: break
        xa, xb = OA[j + 1], OB[j + 1]
        ra = np.log(xa / ea); rb = np.log(xb / eb); ret = s * (ra - bb * rb) - cost * 2 * (1 + abs(bb)) / 2 - fy * (j + 1 - j0) * (1 + abs(bb)) / 2
        out.append((ix[i], 100 * ret, j + 1 - j0)); i = j + 1
    return pd.DataFrame(out, columns=["t", "R", "days"])
if __name__ == "__main__":
    allt = []
    for a, b in PAIRS:
        if a not in F.D or b not in F.D: continue
        t = pair(a, b); r = t.R; y = t.groupby(t.t.dt.year).R.sum(); allt.append(t)
        print(f"{a}/{b:7s} n{len(t):4d} ({len(t) / max(len(y), 1):.0f}/yr) mean {r.mean():+.3f}% t {r.mean() / r.std() * np.sqrt(len(r)):+.2f} | years + {(y > 0).sum()}/{len(y)} | last5y {r[t.t.dt.year >= 2022].mean():+.3f}% | avg days {t.days.mean():.1f}")
    T = pd.concat(allt); r = T.R; print(f"ALL PAIRS n{len(T)} mean {r.mean():+.3f}% t {r.mean() / r.std() * np.sqrt(len(r)):+.2f} | years + {(T.groupby(T.t.dt.year).R.sum() > 0).sum()}/{T.t.dt.year.nunique()}")
