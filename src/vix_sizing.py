"""Doc 218 — walk-forward VIX sizing for the RSI(4) dip. For each year Y, the size multiplier for a trade = (mean result of trades in its VIX
band in years before Y) / (mean of all trades before Y), clipped to [0.5, 2.0], then normalised so the average multiplier over the earlier
years' trades is 1 (same average risk). Compared with flat sizing on the same trades, out of sample only (Y from 2008)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, std_books as B
t = B.rsi4().sort_values("t").reset_index(drop=True); v = F.D["VIX"].close.reindex(t.t.dt.normalize()).ffill().values
for name, cuts in (("two bands: VIX < 20 / >= 20", [0, 20, 300]), ("five bands", [0, 15, 20, 25, 30, 300])):
    t["b"] = pd.cut(v, cuts, labels=False); w = pd.Series(np.nan, index=t.index)
    for y in range(2008, t.t.dt.year.max() + 1):
        past = t[t.t.dt.year < y]; mb = past.groupby("b").R.mean(); mu = past.R.mean()
        raw = (mb / mu).clip(0.5, 2.0); norm = raw.reindex(past.b).mean(); cur = t.t.dt.year == y
        w[cur] = (raw / norm).reindex(t.b[cur]).fillna(1.0).values
    o = t[w.notna()].copy(); o["W"] = o.R * w[w.notna()]
    mf, mw = o.groupby(o.t.dt.to_period("M")).R.sum(), o.groupby(o.t.dt.to_period("M")).W.sum()
    yf, yw = o.groupby(o.t.dt.year).R.sum(), o.groupby(o.t.dt.year).W.sum()
    print(f"{name}: out of sample 2008-26 | flat: total {o.R.sum():+.0f} ATR, monthly Sharpe {mf.mean() / mf.std() * np.sqrt(12):.2f}, worst 12m {mf.rolling(12).sum().min():+.1f}, years + {(yf > 0).sum()}/{len(yf)} | "
          f"VIX-sized: total {o.W.sum():+.0f}, Sharpe {mw.mean() / mw.std() * np.sqrt(12):.2f}, worst 12m {mw.rolling(12).sum().min():+.1f}, years + {(yw > 0).sum()}/{len(yw)} | avg multiplier {w.mean():.2f}")
    print("   multipliers now:", {int(k): round(float(x), 2) for k, x in ((t.groupby("b").R.mean() / t.R.mean()).clip(0.5, 2) / ((t.groupby("b").R.mean() / t.R.mean()).clip(0.5, 2)).reindex(t.b).mean()).items()})
