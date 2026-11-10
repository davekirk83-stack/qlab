"""Doc 220 — reviewer 2 section 4 (DK 11:05): an 'intelligent portfolio manager'. Layer 1 = regime from completed data (US 500 + VIX at the
signal close); Layer 2 = which books run / how much, by regime. Tested on our live books' own trade lists (next-open execution, IG costs).
Regimes (fixed in advance): SHOCK = VIX > 30 or US 500 down > 7% over 5 days; BEAR = US 500 below its 200-day (no shock);
BULL-CALM = above the 200-day and VIX < 20; BULL-NERVOUS = above the 200-day and VIX >= 20.
Tests: (a) each book's result by regime; (b) the reviewer's rules as written (shock: no new positions; bear: dip books off; calm bull: all on);
(c) walk-forward allocation: each year, weight per book per regime = that regime's mean / the book's overall mean in EARLIER years only,
clipped 0–2 (0 = off), normalised to the same average risk; scored out of sample 2008–26 on monthly results."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF, std_books as B
spx, vix = F.D["SPX"], F.D["VIX"].close
def regime(dates):
    d = pd.DatetimeIndex(dates).normalize(); c = spx.close; m200 = c.rolling(200).mean(); r5 = c / c.shift(5) - 1
    v = vix.reindex(d, method="ffill").values; cc = c.reindex(d, method="ffill").values; mm = m200.reindex(d, method="ffill").values; rr = r5.reindex(d, method="ffill").values
    return np.where((v > 30) | (rr < -0.07), "SHOCK", np.where(cc < mm, "BEAR", np.where(v < 20, "BULL-CALM", "BULL-NERVOUS")))
def books():
    out = {"RSI(4) dip": B.rsi4()[["t", "R"]], "Turn of month": B.tom()[["t", "R"]]}
    with B.cost(1.0):
        tp = sum([RF.tps_o(F.D[k]) for k in F.IXG], []); out["TPS ladder (% of budget)"] = pd.DataFrame([(t, 100 * p) for t, p, *_ in tp], columns=["t", "R"])
    def santa(d):
        s = pd.Series((d.index.month == 12) & (d.index.day >= 22) & (d.index.day <= 24) & (d.index.dayofweek < 5), index=d.index); return s & ~s.shift(1, fill_value=False)
    out["Santa"] = pd.DataFrame([(t, R) for k in F.IX for t, R in F.run(k, santa(F.D[k]), 1, None, 7, stop=5.0)], columns=["t", "R"])
    for k, t in out.items(): t["t"] = pd.to_datetime(t.t); t["g"] = regime(t.t)
    return out
RULES = {"RSI(4) dip": {"SHOCK": 0, "BEAR": 0, "BULL-CALM": 1, "BULL-NERVOUS": 1}, "TPS ladder (% of budget)": {"SHOCK": 0, "BEAR": 0, "BULL-CALM": 1, "BULL-NERVOUS": 0.5},
         "Turn of month": {"SHOCK": 0, "BEAR": 0.5, "BULL-CALM": 1, "BULL-NERVOUS": 1}, "Santa": {"SHOCK": 0, "BEAR": 0.5, "BULL-CALM": 1, "BULL-NERVOUS": 1}}
def score(t, w):
    x = t.assign(W=t.R * w); m = x.groupby(x.t.dt.to_period("M")).W.sum(); y = x.groupby(x.t.dt.year).W.sum()
    return f"total {x.W.sum():+7.1f} | monthly Sharpe {m.mean() / m.std() * np.sqrt(12):.2f} | worst 12m {m.rolling(12).sum().min():+6.1f} | years + {(y > 0).sum()}/{len(y)} | avg weight {w.mean():.2f}"
if __name__ == "__main__":
    BK = books()
    print("== (a) result per trade by regime at the signal")
    for nm, t in BK.items():
        print(f"  {nm}: " + " | ".join(f"{g} n{len(x)} {x.R.mean():+.3f}" for g, x in t.groupby("g")))
    print("\n== (b) reviewer's rules as written vs (c) walk-forward allocation — out of sample 2008-26")
    for nm, t in BK.items():
        t = t[t.t.dt.year >= 2008].reset_index(drop=True); full = BK[nm]
        w_rule = t.g.map(RULES[nm]).astype(float); w_wf = pd.Series(1.0, index=t.index)
        for y in range(2008, t.t.dt.year.max() + 1):
            past = full[full.t.dt.year < y]; mu = past.R.mean(); raw = (past.groupby("g").R.mean() / mu).clip(0, 2)
            norm = raw.reindex(past.g).fillna(1).mean(); cur = t.t.dt.year == y; w_wf[cur] = (raw / norm).reindex(t.g[cur]).fillna(1.0).values
        print(f"  {nm}\n     all signals : {score(t, pd.Series(1.0, index=t.index))}\n     reviewer    : {score(t, w_rule)}\n     walk-forward: {score(t, w_wf)}")

def bear_off():
    BK = books()
    for nm in ("RSI(4) dip", "TPS ladder (% of budget)", "Turn of month", "Santa"):
        t = BK[nm]; o = t[t.t.dt.year >= 2008].reset_index(drop=True); w = (o.g != "BEAR").astype(float)
        yb = t[t.g == "BEAR"].groupby(t.t.dt.year).R.mean(); first = [y for y in range(2008, 2027) if (t[(t.g == "BEAR") & (t.t.dt.year < y)].R.mean() < 0)]
        print(f"  {nm}\n     all signals    : {score(o, pd.Series(1.0, index=o.index))}\n     off in BEAR    : {score(o, w)}"
              f"\n     BEAR trades' mean in earlier years was negative from {first[0] if first else 'never'} (walk-forward would have switched it off then); BEAR by year: "
              + " ".join(f"{y}:{v:+.2f}" for y, v in yb.items()))
if __name__ == "__main__" and "bear" in sys.argv: print("\n== (d) one rule: dip books off while the US 500 is below its 200-day"); bear_off()
