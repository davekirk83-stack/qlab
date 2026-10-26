"""Index short overlay for the IG account (avenue 5, doc 130). SPY / QQQ / DIA daily 2003-2026 as proxies for IG's US 500 / US Tech 100 /
Wall Street. Short only when the index is below its trend; flat otherwise. IG daily funding on a short ~ -2.5%/yr above/below the
benchmark - modelled as a 2.5%/yr cost while short, plus a 0.02% spread each switch. Variants: trend = 63-day (3-month) or 126-day
return < 0, or close < 200-day SMA; checked daily or weekly. Judged on: per-year return, the S&P's worst 10% of months, drawdown, and
what it does to a long-only book held alongside (the hedge test)."""
import numpy as np, pandas as pd
P = {}
for s in ("SPY", "QQQ", "DIA"):
    d = pd.read_csv(f"/home/claude/qlab/data_etf20/{s}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True).normalize(); P[s] = d.close
P = pd.DataFrame(P).dropna(); R = P.pct_change().fillna(0)
spym = P.SPY.resample("ME").last().pct_change(); worst = spym.nsmallest(int(len(spym)*0.1)).index
def short_book(rule, freq):
    if rule == "63d": sig = P/P.shift(63) - 1 < 0
    elif rule == "126d": sig = P/P.shift(126) - 1 < 0
    else: sig = P < P.rolling(200).mean()
    if freq == "W": sig = sig.resample("W-FRI").last().reindex(P.index, method="ffill")
    pos = -sig.astype(float).shift(1).fillna(0)                 # decided at yesterday's close
    pnl = pos*R - (pos != 0)*0.025/252 - pos.diff().abs().fillna(0)*0.0002
    return pnl.mean(axis=1)
for rule in ("63d", "126d", "200sma"):
    for freq in ("D", "W"):
        x = short_book(rule, freq); x = x[x.index >= "2003-01-01"]; m = (1+x).resample("ME").prod() - 1
        eq = (1+x).cumprod(); dd = (eq/eq.cummax() - 1).min()
        hedge = 0.5*R.mean(axis=1)[x.index] + 0.5*x       # 50/50 with a long-index holding
        long_only = R.mean(axis=1)[x.index]
        def stats(y): e = (1+y).cumprod(); return y.mean()*252*100, (e/e.cummax()-1).min()*100
        h_ann, h_dd = stats(hedge); l_ann, l_dd = stats(0.5*long_only)
        yr = (1+x).groupby(x.index.year).prod() - 1
        print(f"{rule:6s} {freq}: {x.mean()*252*100:+.1f}%/yr  maxDD {dd*100:.0f}%  time short {100*(x!=0).mean():.0f}%  | SPY worst 10% months: {m.reindex(worst).mean()*100:+.2f}%/mo"
              f"  | 2008 {yr.get(2008)*100:+.0f}% 2020 {yr.get(2020)*100:+.0f}% 2022 {yr.get(2022)*100:+.0f}%  | half-long alone {l_ann:+.1f}%/yr dd {l_dd:.0f}% -> with overlay {h_ann:+.1f}%/yr dd {h_dd:.0f}%")
