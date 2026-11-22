"""doc 260: does dealer gamma (SqueezeMetrics GEX, 2011-2026, free) change how our book types behave on the S&P?
Regime = previous day's GEX sign (known before the trade). Tests: next-day move size; RSI(4) dip long (our PASS book, mean reversion);
2-day momentum follow-through (breakout-type). Halves 2011-18 / 2019-26."""
import pandas as pd, numpy as np
d = pd.read_csv("runs/gex/squeezemetrics_dix.csv", parse_dates=["date"]).set_index("date")
c = d.price; r = c.pct_change(); g = d.gex.shift(1); neg = g < 0
up = r.clip(lower=0).ewm(alpha=1/4).mean(); dn = (-r.clip(upper=0)).ewm(alpha=1/4).mean(); rsi = 100 - 100/(1 + up/dn)
out = [f"days {len(d)}, negative-GEX days {int(neg.sum())} ({neg.mean():.0%})", ""]
nxt = r.shift(-1)
for name, m in (("positive GEX", ~neg & g.notna()), ("negative GEX", neg)):
    out.append(f"{name:13} next-day |move| {100*nxt[m].abs().mean():.2f}%  next-day mean {100*nxt[m].mean():+.3f}%  n {int(m.sum())}")
out.append("")
# RSI(4) dip: buy close when RSI4 < 20 and above nothing else; exit at first close with RSI4 > 55, max 5 days
def dip(mask):
    res = []; i = 0; idx = list(d.index); n = len(idx)
    while i < n - 6:
        if rsi.iloc[i] < 20 and mask.iloc[i]:
            for k in range(i+1, min(i+6, n)):
                if rsi.iloc[k] > 55 or k == i+5: res.append((idx[i], c.iloc[k]/c.iloc[i]-1)); i = k; break
        i += 1
    return pd.Series([x for _, x in res], index=[t for t, _ in res])
for name, m in (("all", pd.Series(True, index=d.index)), ("positive GEX", ~neg & g.notna()), ("negative GEX", neg)):
    R = dip(m); h = R[R.index < "2019-01-01"]; h2 = R[R.index >= "2019-01-01"]
    out.append(f"RSI(4)<20 dip long, {name:13} n {len(R):3} mean {100*R.mean():+.2f}% win {(R>0).mean():.0%} worst {100*R.min():+.1f}% | 2011-18 {100*h.mean():+.2f} / 2019-26 {100*h2.mean():+.2f}")
out.append("")
# momentum: after a 2-day move > 1.5% either way, follow it for 2 days
m2 = c.pct_change(2); sig = np.sign(m2.where(m2.abs() > 0.015)); fwd = c.shift(-2)/c - 1
for name, m in (("positive GEX", ~neg & g.notna()), ("negative GEX", neg)):
    x = (sig * fwd)[m & sig.notna()].dropna(); a, b = x[x.index < "2019-01-01"], x[x.index >= "2019-01-01"]
    out.append(f"2-day momentum follow, {name:13} n {len(x):3} mean {100*x.mean():+.3f}% win {(x>0).mean():.0%} | 2011-18 {100*a.mean():+.3f} / 2019-26 {100*b.mean():+.3f}")
open("runs/research/gex_regime_test.txt", "w").write("\n".join(out)); print("\n".join(out))
