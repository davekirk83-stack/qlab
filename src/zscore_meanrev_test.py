"""Carm1ne/gs-quant post rule: z = (close - SMA20)/SD20; buy at z < -2, sell at z >= 0. Long only, daily close fills
(signal at close t, fill at close t+1 to avoid lookahead). Costs per side: ETFs/stocks 2bp, BTC 10bp. Compare to buy-and-hold,
and per unit of time-in-market. No fitted parameters, so 'walk-forward' = report the two halves separately."""
import pandas as pd, numpy as np, glob, os
def load(p):
    d = pd.read_csv(p); col = d.columns[0]
    if col == "t": d["date"] = pd.to_datetime(d.t, unit="ms", utc=True)
    else: d["date"] = pd.to_datetime(d[col], utc=True)
    return d.set_index("date").close.sort_index().dropna()
def run(c, cost, n=20, z_in=-2.0, z_out=0.0):
    m, s = c.rolling(n).mean(), c.rolling(n).std(); z = (c - m) / s
    pos = pd.Series(0.0, index=c.index); held = 0
    for i, t in enumerate(c.index):
        if held == 0 and z.iloc[i] < z_in: held = 1
        elif held == 1 and z.iloc[i] >= z_out: held = 0
        pos.iloc[i] = held
    p = pos.shift(1).fillna(0)                      # act next close
    r = c.pct_change().fillna(0)
    strat = p * r - cost * p.diff().abs().fillna(0)
    return strat, p, r
def stats(strat, p, r):
    yrs = len(r) / 252 if r.index.freq is None and len(r) < 6000 else len(r)/252
    tot = (1 + strat).prod() - 1; bh = (1 + r).prod() - 1; tim = p.mean()
    trades = int((p.diff() == 1).sum())
    dd = ((1 + strat).cumprod() / (1 + strat).cumprod().cummax() - 1).min()
    # matched-exposure baseline: buy-and-hold scaled to same time-in-market
    return dict(strat=tot, bh=bh, tim=tim, trades=trades, dd=dd, sharpe=strat.mean()/strat.std()*np.sqrt(252) if strat.std()>0 else 0,
                bh_sharpe=r.mean()/r.std()*np.sqrt(252))
out = []
sets = [("SPY", "data_wide/SPY.csv", 0.0002), ("QQQ", "data_wide/QQQ.csv", 0.0002), ("GS", "data_stocks20/GS.csv", 0.0002),
        ("BTC", "data_daily/BTCUSD.csv", 0.0010)]
for name, path, cost in sets:
    c = load(path)
    if name == "GS": c = c[c.index >= c.index[-1] - pd.Timedelta(days=365*10)]
    for label, sl in (("full", slice(None)), ("1st half", slice(0, len(c)//2)), ("2nd half", slice(len(c)//2, None))):
        cc = c.iloc[sl]; s = stats(*run(cc, cost))
        out.append(f"{name:4} {label:8} {cc.index[0].date()}→{cc.index[-1].date()}  rule {s['strat']*100:+7.1f}%  B&H {s['bh']*100:+8.1f}%  "
                   f"in-mkt {s['tim']*100:4.0f}%  trades {s['trades']:3}  maxDD {s['dd']*100:5.1f}%  Sharpe {s['sharpe']:.2f} vs B&H {s['bh_sharpe']:.2f}")
# stock universe breadth: how many of the 20+ stocks does the rule beat B&H Sharpe on (last 10y)
win = 0; tot = 0
for p in sorted(glob.glob("data_stocks20/*.csv")):
    c = load(p); c = c[c.index >= c.index[-1] - pd.Timedelta(days=3650)]
    if len(c) < 1500: continue
    s = stats(*run(c, 0.0002)); tot += 1; win += s["sharpe"] > s["bh_sharpe"]
out.append(f"Stocks (10y): rule Sharpe beats buy-and-hold Sharpe on {win}/{tot}")
txt = "\n".join(out); print(txt); open("runs/zscore_meanrev_test.txt", "w").write(txt + "\n")
