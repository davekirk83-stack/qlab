"""Doc 281 follow-up: the momentum scans (Minervini trend template + new 52-week high; 55-day Donchian breakout) on markets WITHOUT the
current-S&P-500 survivorship bias: 7 indices, 5 commodities, 5 FX majors, 10 coins (daily). Entry at the signal close; exits: hold 20d,
or trail (first close under the 50-day, 60-day max). Costs as doc 279. Split by S&P regime."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import cross_asset_s3 as X
U = X.load(); spx = U[("indices", "SPX")]; DN = spx.c < spx.c.rolling(200).mean()
rows = []
for (cls, s), x in U.items():
    if cls in ("US stocks", "UK stocks", "bonds"): continue
    D = x[["o", "h", "l", "c"]].astype(float).dropna(); D = D[D.c > 0]; c = D.c.values; n = len(c)
    cost = {"FX": 0.0002, "crypto": 0.0014}.get(cls, 0.001)
    m50, m150, m200 = (D.c.rolling(k).mean().values for k in (50, 150, 200)); m200_1m = pd.Series(m200).shift(21).values
    hi252 = D.c.rolling(252).max().shift(1).values; lo252 = D.c.rolling(252).min().values; hi55 = D.c.rolling(55).max().shift(1).values
    reg = DN.reindex(D.index).ffill().fillna(False).values
    for i in range(260, n - 61):
        R = "S&P<200d" if reg[i] else "S&P>200d"
        sigs = []
        if c[i] > m50[i] > m150[i] > m200[i] and m200[i] > m200_1m[i] and c[i] >= 1.3 * lo252[i] and c[i] > hi252[i] and c[i - 1] <= hi252[i]: sigs.append("MTT 52w-high")
        if c[i] > hi55[i] and c[i - 1] <= hi55[i]: sigs.append("Donchian 55d")
        for sg in sigs:
            px = c[min(n - 1, i + 60)]
            for k in range(i + 1, min(n, i + 61)):
                if c[k] < m50[k]: px = c[k]; break
            rows.append((sg + ", trail 50d", cls, s, R, D.index[i], px * (1 - cost) / (c[i] * (1 + cost)) - 1))
            rows.append((sg + ", hold 20d", cls, s, R, D.index[i], c[i + 20] * (1 - cost) / (c[i] * (1 + cost)) - 1))
T = pd.DataFrame(rows, columns=["scan", "cls", "sym", "reg", "t", "r"]).sort_values("t")
out = []
for keys, g in T.groupby(["scan", "cls"]):
    r = 100 * g.r; h = len(r) // 2
    out.append(dict(scan=keys[0], cls=keys[1], n=len(r), mean=round(r.mean(), 2), h1=round(r[:h].mean(), 2), h2=round(r[h:].mean(), 2), win=round((r > 0).mean(), 2),
                    calm=round(100 * g[g.reg == "S&P>200d"].r.mean(), 2), fear=round(100 * g[g.reg == "S&P<200d"].r.mean(), 2), syms_pos=f"{(g.groupby('sym').r.mean() > 0).sum()}/{g.sym.nunique()}"))
R = pd.DataFrame(out); R.to_csv("runs/research/breakout_nosurv.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
