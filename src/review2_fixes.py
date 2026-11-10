"""Doc 216 — second external review (10 Nov 10:18). Execution fix + statistics it asked for.
run_o(): close-decided signals trade at the NEXT OPEN for entries AND exits (incl. max-days); stop checked on every bar from the entry bar,
a gap through the stop fills at that open. tps_o(): first buy, each rung and the exit all at the next open after the close that decides them.
Stats: trade t; date-clustered t (all trades entered the same day summed into one observation); year-block bootstrap 95% CI of the mean."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review_ideas_test as V
rng = np.random.default_rng(11)
TR6 = ["SPX", "NDX", "DJI", "DAX", "FTSE", "GOLD"]; IX8 = F.IXG
def good_open(d): return (abs(d.open - d.close.shift(1)) > 1e-9)   # Yahoo FTSE/early-SPX opens = previous close (doc 209)

def run_o(k, entry, exit_=None, maxd=10, stop=3.0, cm=1.0):
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = entry.reindex(d.index).fillna(False).values.astype(bool); X = exit_.reindex(d.index).fillna(False).values.astype(bool) if exit_ is not None else np.zeros(len(d), bool)
    cost = F.COST[k] * cm; fy = 0.06 / 365 * 1.4; out = []; i = 0; n = len(C)
    while i < n - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        j0 = i + 1; e = O[j0]; st = e - stop * A[i]; j = j0; px = None
        while j < n:
            if L[j] <= st: px = min(st, O[j]) if j > j0 else (O[j] if O[j] < st else st); break
            if (X[j] or (j - j0 + 1) >= maxd) and j + 1 < n: px = O[j + 1]; j += 1; break   # decided at close j, traded next open
            j += 1
        if px is None: break
        out.append((d.index[i], (px - e - cost * e * 2 - fy * e * max(j - j0, 0)) / A[i])); i = j
    return out

def tps_o(d, cost=.0003, fund=0.06, maxd=30, kill=0.15, ladder=(0.1, 0.2, 0.3, 0.4), min_gap=0.0):
    O, C = d.open.values, d.close.values; r = F.rsi(d.close, 2).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 2:
        if not (C[i] > ma[i] and r[i] < 25 and r[i - 1] < 25): i += 1; continue
        qty, spent, lastfill, k, j0 = 0.0, 0.0, None, 0, i; buy_next = True; j = i; worst = 0.0
        while j < n - 1:
            if buy_next and k < len(ladder):
                px = O[j + 1]; w = ladder[k]; qty += w / (px * (1 + cost)); spent += w; lastfill = px; k += 1
            buy_next = False; jj = j + 1          # now at the close of day jj
            if jj >= n: break
            avg = spent / qty; worst = min(worst, qty * C[jj] - spent)
            if r[jj] > 70 or (jj - j0) >= maxd or C[jj] <= avg * (1 - kill):
                if jj + 1 >= n: break
                val = qty * O[jj + 1] * (1 - cost) - spent * fund / 365 * 1.4 * (jj + 1 - j0) * 0.5
                out.append((d.index[j0], val - spent, spent, jj + 1 - j0, k, worst)); break
            if k < len(ladder) and C[jj] < lastfill * (1 - min_gap): buy_next = True
            j = jj
        i = j + 2
    return out

def stats(name, t):
    t = pd.DataFrame(t, columns=["t", "R"]) if not isinstance(t, pd.DataFrame) else t
    r = t.R; tt = r.mean() / r.std(ddof=1) * np.sqrt(len(r)); y = t.groupby(t.t.dt.year).R.sum()
    c = t.groupby(t.t.dt.normalize()).R.sum(); tc = c.mean() / c.std(ddof=1) * np.sqrt(len(c)) * 1.0
    yrs = sorted(t.t.dt.year.unique()); by = {yy: t.R[t.t.dt.year == yy].values for yy in yrs}
    boot = [np.concatenate([by[yy] for yy in rng.choice(yrs, len(yrs))]).mean() for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5]); full = y[y.index < 2026]
    print(f"{name:52s} n{len(r):5d} mean {r.mean():+.3f} t {tt:+.2f} | same-day-clustered t {tc * np.sqrt(len(r) / len(c)) / np.sqrt(len(r) / len(c)):+.2f} (n days {len(c)}) | "
          f"year-block 95% CI [{lo:+.3f}, {hi:+.3f}] | full years + {int((full > 0).sum())}/{len(full)} | last5y {r[t.t.dt.year >= 2022].mean():+.3f}", flush=True)
    return t

if __name__ == "__main__":
    up = lambda d: d.close > d.close.rolling(200).mean(); r4 = lambda d: F.rsi(d.close, 4)
    print("== 1. corrected execution (entries AND exits at the next open)")
    def book(mk, fn, **kw): return pd.DataFrame(sum([run_o(k, *fn(F.D[k]), **kw) for k in mk], []), columns=["t", "R"])
    R4 = stats("RSI(4) dip, 8 markets, next-open in & out", book(IX8, lambda d: (up(d) & (r4(d) < 25), r4(d) > 55), maxd=10, stop=3.0))
    stats("RSI(4) dip, 6 traded markets", book(TR6, lambda d: (up(d) & (r4(d) < 25), r4(d) > 55), maxd=10, stop=3.0))
    stats("RSI(4) dip, 8 markets, costs x1.5", book(IX8, lambda d: (up(d) & (r4(d) < 25), r4(d) > 55), maxd=10, stop=3.0, cm=1.5))
    tom = lambda d: (V.tom(d), None); TOM6 = stats("TOM (decided in advance: in at close, out at close day 3), 6 mk", pd.DataFrame(sum([F.run(k, V.tom(F.D[k]), 1, None, 3, stop=5.0) for k in TR6], []), columns=["t", "R"]))
    stats("TOM, all 8 markets", pd.DataFrame(sum([F.run(k, V.tom(F.D[k]), 1, None, 3, stop=5.0) for k in IX8], []), columns=["t", "R"]))
    def santa(d):
        s = pd.Series((d.index.month == 12) & (d.index.day >= 22) & (d.index.day <= 24) & (d.index.dayofweek < 5), index=d.index); return s & ~s.shift(1, fill_value=False)
    SAN = stats("Santa, 7 indices", pd.DataFrame(sum([F.run(k, santa(F.D[k]), 1, None, 7, stop=5.0) for k in F.IXG if k != "GOLD"], []), columns=["t", "R"]))
    print("== 2. TPS with next-open buys, rungs and exits (7 indices + gold), % of budget per episode")
    for nm, kw in [("TPS as published (4 rungs)", {}), ("stop after 2 rungs", {"ladder": (0.1, 0.2)}), ("stop after 3 rungs", {"ladder": (0.1, 0.2, 0.3)}),
                   ("4 rungs, each >= 1% below the last fill", {"min_gap": 0.01}), ("4 rungs, each >= 2% below the last fill", {"min_gap": 0.02})]:
        E = sum([tps_o(F.D[k], **kw) for k in IX8], []); t = pd.DataFrame(E, columns=["t", "pnl", "spent", "days", "rungs", "mae"]); t["R"] = 100 * t.pnl  # % of FULL budget
        w, l = t.R[t.R > 0], t.R[t.R <= 0]
        stats(f"TPS {nm}", t[["t", "R"]])
        print(f"      win {100 * len(w) / len(t):.0f}% | avg win {w.mean():+.2f}% avg loss {l.mean():+.2f}% | worst {t.R.min():+.1f}% | worst open loss (MAE) {100 * t.mae.min():+.1f}% | "
              f"avg days {t.days.mean():.1f} | avg budget used {100 * t.spent.mean():.0f}% | longest losing run {max((len(list(g)) for kk, g in __import__('itertools').groupby(t.R <= 0) if kk), default=0)}")
    print("== 3. robustness")
    for x in (45, 50, 55, 60):
        stats(f"RSI(4) exit > {x}", book(IX8, lambda d, x=x: (up(d) & (r4(d) < 25), r4(d) > x), maxd=10, stop=3.0))
    stats("RSI(4) fixed 5-day hold", book(IX8, lambda d: (up(d) & (r4(d) < 25), None), maxd=5, stop=3.0))
    R4["m"] = np.concatenate([[k] * len(run_o(k, up(F.D[k]) & (r4(F.D[k]) < 25), r4(F.D[k]) > 55, 10, 3.0)) for k in IX8])
    print("   RSI(4) by market:", " ".join(f"{k}:{g.R.sum():+.0f}ATR/{len(g)}" for k, g in R4.groupby("m")))
    best = R4.groupby("m").R.sum().idxmax(); stats(f"RSI(4) without its best market ({best})", R4[R4.m != best][["t", "R"]])
    ys = SAN.groupby(SAN.t.dt.year).R.sum().sort_values(); print("   Santa by year (ATR):", " ".join(f"{k}:{v:+.1f}" for k, v in ys.sort_index().items()))
    for drop in (3, 4):
        keep = SAN[~SAN.t.dt.year.isin(ys.index[-drop:])]; print(f"   Santa without its best {drop} years: mean {keep.R.mean():+.3f} n{len(keep)} t {keep.R.mean() / keep.R.std() * np.sqrt(len(keep)):+.2f}")
    yt = TOM6.groupby(TOM6.t.dt.year).R.sum(); print("   TOM by year (ATR, 6 markets):", " ".join(f"{k}:{v:+.1f}" for k, v in yt.items()))
    print("   Yahoo open audit (share of days open == previous close, since 2010):", " ".join(f"{k}:{100 * (~good_open(F.D[k]))[F.D[k].index.year >= 2010].mean():.0f}%" for k in IX8))
