"""Doc 284: Zarattini & Aziz (2023) 5-minute opening-range breakout, as published: direction of the FIRST 5-min candle (09:30-09:35 ET);
enter at the open of the second candle; stop at the first candle's low (long) / high (short); profit target 10R; otherwise exit at the
close. Doji first candles skipped. Alpaca 5-min bars 2021-26 (SPY, QQQ, IWM, 7 large stocks). Costs per side: index ETFs 0.0075%
(IG index level), stocks 0.03%. Also their 'stocks in play' idea on the 7 stocks: trade only the stock(s) whose first-5-min volume is
highest relative to its own 14-day average (top 1 and top 3 of 7)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I
def orb(x, cost, tr=10.0):
    out = []
    for day, g in x.groupby(x.index.normalize()):
        if len(g) < 70: continue
        f = g.iloc[0]; s = np.sign(f.close - f.open)
        if s == 0: continue
        e = g.open.iloc[1]; st = f.low if s == 1 else f.high; risk = abs(e - st)
        if risk <= 0 or (s == 1 and st >= e) or (s == -1 and st <= e): continue
        tgt = e + s * tr * risk; px = g.close.iloc[-1]
        for k in range(1, len(g)):
            lo, hi, op = g.low.iloc[k], g.high.iloc[k], g.open.iloc[k]
            if (s == 1 and lo <= st) or (s == -1 and hi >= st): px = st if ((s == 1 and op > st) or (s == -1 and op < st)) else op; break
            if (s == 1 and hi >= tgt) or (s == -1 and lo <= tgt): px = tgt; break
        r = s * (px / e - 1) - 2 * cost; out.append((day, s, r, r / (risk / e), f.vol))
    return pd.DataFrame(out, columns=["t", "side", "r", "R", "v1"])
def summ(T, lab):
    T = T.sort_values("t"); r = 100 * T.r; h = len(r) // 2; y = r.groupby(pd.to_datetime(T.t).dt.year.values).sum()
    return dict(test=lab, n=len(r), win=round((r > 0).mean(), 3), mean_pct=round(r.mean(), 4), mean_R=round(T.R.mean(), 3), h1=round(r[:h].mean(), 4), h2=round(r[h:].mean(), 4),
                t=round(r.mean() / (r.std() / np.sqrt(len(r))), 2), years=" ".join(f"{k}:{v:+.1f}" for k, v in y.items()))
rows = []; ST = {}
for f in sorted(glob.glob("data_alpaca/*_5m.csv.gz")):
    s = os.path.basename(f).split("_")[0]; x = I.rth(f); cost = 0.000075 if s in I.IDXE else 0.0003
    T = orb(x, cost); rows.append(summ(T, s)); ST[s] = T
    if s == "QQQ": rows.append(summ(orb(x, cost, tr=1e9), "QQQ no target (EOD)"))
stk = [k for k in ST if k not in I.IDXE]
A = pd.concat([ST[k].assign(sym=k) for k in stk]); A["rel"] = A.groupby("sym").v1.transform(lambda v: v / v.rolling(14, min_periods=10).mean().shift(1))
A = A.dropna(subset=["rel"]); A["rk"] = A.groupby("t").rel.rank(ascending=False)
rows.append(summ(A, "7 stocks, all")); rows.append(summ(A[A.rk <= 1], "stocks in play: top 1 by relative volume")); rows.append(summ(A[A.rk <= 3], "stocks in play: top 3"))
R = pd.DataFrame(rows); R.to_csv("runs/research/orb_5m.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
