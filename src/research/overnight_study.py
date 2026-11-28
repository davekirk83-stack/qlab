"""Doc 284: overnight hold on US indices (buy the cash close, sell the next cash open) - every night is a trade, so if it holds it fixes
the frequency problem. Data: Alpaca SPY / QQQ / IWM 15-min 2021-26 (regular session; close = last bar's close, open = next day's first
bar open). IG cost per night: spread 0.005% (NQ 1 pt) + IG overnight funding ~0.019%/night (SONIA + 2.5% / 365), x3 over a weekend.
Variants by condition at the close: S&P above/below its 200-day, the day down/up, daily RSI(2) < 10 / > 90, day of week.
(Long NQ history version runs when the Dukascopy 2020-25 download lands.)"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I
rows = []
for s in ("SPY", "QQQ", "IWM"):
    d = I.rth(f"data_alpaca/{s}_15m.csv.gz"); g = d.groupby(d.index.normalize())
    D = pd.DataFrame({"o": g.open.first(), "c": g.close.last(), "n": g.size()}); D = D[D.n >= 20]
    D["ret_on"] = D.o.shift(-1) / D.c - 1; D["gap_days"] = (D.index.to_series().shift(-1) - D.index.to_series()).dt.days.values
    D["cost"] = 0.00005 + 0.00019 * D.gap_days.clip(upper=4)
    D["net"] = D.ret_on - D.cost; D["ret_day"] = D.c / D.o - 1; D["up200"] = D.c > D.c.rolling(200).mean()
    dd = D.c.diff(); u = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean(); D["rsi2"] = 100 - 100 / (1 + u / dn)
    D["dow"] = D.index.dayofweek; D = D.dropna(subset=["ret_on"]).iloc[200:]
    for lab, m in (("all nights", D.index == D.index), ("S&P/self above 200d", D.up200), ("below 200d", ~D.up200), ("day down", D.c < D.c.shift()), ("day up", D.c > D.c.shift()),
                   ("RSI2<10", D.rsi2 < 10), ("RSI2>90", D.rsi2 > 90), ("Mon-Thu nights", D.dow < 4), ("Friday (weekend)", D.dow == 4),
                   ("above 200d + day down", D.up200 & (D.c < D.c.shift()))):
        x = D[m]; r = 100 * x.net; h = len(r) // 2
        rows.append(dict(mkt=s, cond=lab, n=len(r), gross_bp=round(10000 * x.ret_on.mean(), 2), net_bp=round(100 * r.mean(), 2), h1=round(100 * r[:h].mean(), 2), h2=round(100 * r[h:].mean(), 2),
                         win=round((r > 0).mean(), 2), t=round(r.mean() / (r.std() / np.sqrt(len(r))), 2), years=" ".join(f"{k}:{v:+.1f}" for k, v in r.groupby(x.index.year).sum().items())))
R = pd.DataFrame(rows); R.to_csv("runs/research/overnight_study.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
print("\nnet_bp = basis points per night after IG spread + overnight funding (1 bp = 0.01%; on NQ ~20,000, 1 bp = 2 points)")
