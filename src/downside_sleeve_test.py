"""Doc 147: downside cover for the IG plan — a daily-trend SHORT on US Tech 100 / US 500 (QQQ / SPY daily as proxies).
Pre-registered 27 Oct 2026 before any result:
  SLOW  short at the close when close < SMA200 AND close < close 60 trading days ago; cover when either fails. Held next day.
  FAST  same with SMA50 and 20 days.
Costs: 0.03% per side (IG index spread), short financing 1.0% a year (IG: benchmark - 2.5%, net of the rate on cash; conservative).
Returns from dividend-adjusted closes (a short pays the dividend). Dev to 2018-12-31; holdout 2019-01-01 on (includes 2020, 2022).
Control: the same days-short fraction placed at random (block-shuffled episodes, 200 draws) -> what 'being short that often' costs.
Hedge value: the sleeve's return on the index's worst 5% of days, and through each big drawdown. Trials: 2 rules x 2 markets = 4."""
import numpy as np, pandas as pd
COST, FIN = 0.0003, 0.010
def load(s):
    d = pd.read_csv(f"data_eqd/{s}.csv", parse_dates=["t"]).set_index("t"); return d
def sleeve(d, n_ma, n_mom):
    c = d.close; sig = ((c < c.rolling(n_ma).mean()) & (c < c.shift(n_mom))).astype(float)
    r = d.adj.pct_change().fillna(0); pos = -sig.shift(1).fillna(0)
    return pos * r - COST * pos.diff().abs().fillna(0) - (pos != 0) * FIN / 252, pos, r
def perf(x):
    eq = (1 + x).cumprod(); yrs = len(x) / 252
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, (eq / eq.cummax() - 1).min() * 100
def rand_ctrl(pos, r, rng):
    on = (pos != 0).values; ep = []; i = 0; n = len(on)
    while i < n:
        j = i
        while j < n and on[j] == on[i]: j += 1
        ep.append((on[i], j - i)); i = j
    rng.shuffle(ep); p = np.concatenate([np.full(L, -1.0 if o else 0.0) for o, L in ep])
    p = pd.Series(p, index=pos.index)
    return p * r - COST * p.diff().abs().fillna(0) - (p != 0) * FIN / 252
DD = {"2000-02 dot-com": ("2000-03-24", "2002-10-09"), "2008 GFC": ("2007-10-09", "2009-03-09"), "2020 Covid": ("2020-02-19", "2020-03-23"),
      "2022 bear": ("2021-11-19", "2022-10-12"), "2025 tariff": ("2025-02-19", "2025-04-08")}
out = []
for s in ("QQQ", "SPY"):
    d = load(s)
    for name, ma, mom in (("SLOW 200/60", 200, 60), ("FAST 50/20", 50, 20)):
        x, pos, r = sleeve(d, ma, mom); x = x[d.index >= d.index[ma]]; r2 = r[x.index]; pos = pos[x.index]
        lines = [f"{s} {name}: short {100*(pos!=0).mean():.0f}% of days"]
        for seg, m in (("DEV ", x.index < "2019-01-01"), ("HOLD", x.index >= "2019-01-01")):
            cg, dd = perf(x[m]); bh, bdd = perf(r2[m])
            ctrl = np.array([perf(rand_ctrl(pos[m], r2[m], np.random.default_rng(k)))[0] for k in range(200)])
            worst = r2[m] <= r2[m].quantile(0.05)
            lines.append(f"  {seg} sleeve {cg:+5.1f}%/yr maxDD {dd:5.1f}% | index {bh:+5.1f}%/yr maxDD {bdd:5.1f}% | random-timed short {np.median(ctrl):+5.1f}%/yr, sleeve beats {100*(ctrl<cg).mean():.0f}% | on index's worst 5% days: index {100*r2[m][worst].mean():+.2f}%/day, sleeve {100*x[m][worst].mean():+.2f}%/day | corr {np.corrcoef(x[m], r2[m])[0,1]:+.2f}")
        for k, (a, b) in DD.items():
            mm = (x.index >= a) & (x.index <= b)
            if mm.sum(): lines.append(f"    {k:15} index {100*((1+r2[mm]).prod()-1):+6.1f}%  sleeve {100*((1+x[mm]).prod()-1):+6.1f}%")
        out.append("\n".join(lines)); print(out[-1], flush=True)
open("runs/downside_sleeve_test.txt", "w").write("\n\n".join(out) + "\n")
