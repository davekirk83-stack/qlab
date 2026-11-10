"""THE STANDARD TEST v3 (doc 217; DK 10 Nov 10:46: "This should all be part of our new standardised testing system").
Every book, old or new, goes through exactly this, and every run is written to the permanent register runs/research_register.csv.

Builder contract: builder(cm=1.0, rnd=None) -> DataFrame [t, R, m]
  t = signal date (decided on that day's CLOSE), R = result in ATR at entry (or % of budget for ladders), m = market.
  Execution must be next-open for close-decided signals (entries AND exits; stops on every bar; gaps fill at the open) —
  use review2_fixes.run_o / review2_new_books.run_side. Calendar books known in advance may trade at the close.
  cm multiplies costs; rnd(k, entry_series) -> a random entry series with the same count (random-entry benchmark).

Checks (all must hold for PASS):
  1. same-day-clustered t >= t* (Sidak, 5% family-wise, n = every idea in the register)  [trade-level t also shown]
  2. year-block bootstrap 95% CI of the mean above zero (resamples whole calendar years)
  3. >= 60% of FULL calendar years positive (the current part-year is excluded)
  4. last 5 years positive and last 12 months positive
  5. still positive at 1.5x costs
  6. beats the 95th percentile of 100 random-entry runs
WEAK = positive mean with checks 2-5 passing but t or the random test failing; FAIL otherwise.
Also reported (informational, never used to pass a book):
  - walk-forward 'worst periods' switches: month, weekday, VIX band, market, and 'paradigm' (trade a year only if its previous 3 were
    positive) — chosen only from earlier years (>= 8), adopted only if out of sample they raise the total and keep >= 50% of trades;
  - portfolio contribution vs the core books: monthly correlation, combined mean, combined worst 12 months, result in the core's 10 worst
    months. A book is only promoted if it PASSES and improves the portfolio (more return, or a shallower worst 12 months).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, csv, datetime as dt, numpy as np, pandas as pd
from statistics import NormalDist
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
REG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "research_register.csv")
BASE_TRIED = 276          # ideas tried before the register existed (docs 196-216)
_rng = np.random.default_rng(17)

def n_tried():
    return BASE_TRIED + (sum(1 for _ in open(REG)) - 1 if os.path.exists(REG) else 0)
def tstar(n): return NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / n)) / 2)
def shuffler(k, e):
    d = F.D[k]; e = e.reindex(d.index).fillna(False); n = int(e.sum()); idx = d.index[220:-3]
    return pd.Series(d.index.isin(_rng.choice(idx, size=min(n, len(idx)), replace=False)), index=d.index)

def _wf(t, key, years_min=8):
    yrs = t.t.dt.year; keep = base = 0.0; kept = tot = 0
    for y in sorted(yrs.unique()):
        past = t[yrs < y]
        if past.t.dt.year.nunique() < years_min: continue
        m = past.groupby(key[yrs < y]).R.mean(); c = past.groupby(key[yrs < y]).R.size(); off = set(m[(m < 0) & (c >= 10)].index)
        cur = t[yrs == y]; on = cur[~key[yrs == y].isin(off)]; keep += on.R.sum(); base += cur.R.sum(); kept += len(on); tot += len(cur)
    return base, keep, kept, tot

def judge(name, family, markets, builder, core=None, register=True, random_runs=100, quiet=False):
    t = builder().dropna(subset=["R"]).sort_values("t").reset_index(drop=True); t["t"] = pd.to_datetime(t.t)
    r = t.R; n = len(r); out = {"date": dt.date.today().isoformat(), "name": name, "family": family, "markets": " ".join(markets), "n": n}
    N = n_tried() + 1; ts = tstar(N)
    tt = r.mean() / r.std(ddof=1) * np.sqrt(n)
    c = t.groupby(t.t.dt.normalize()).R.sum(); ct = c.mean() / c.std(ddof=1) * np.sqrt(len(c))
    yrs = sorted(t.t.dt.year.unique()); by = {y: t.R[t.t.dt.year == y].values for y in yrs}
    boot = [np.concatenate([by[y] for y in _rng.choice(yrs, len(yrs))]).mean() for _ in range(2000)]; lo, hi = np.percentile(boot, [2.5, 97.5])
    ys = t.groupby(t.t.dt.year).R.sum(); full = ys[ys.index < dt.date.today().year]
    l5 = r[t.t.dt.year >= dt.date.today().year - 5].mean(); l1 = r[t.t >= t.t.max() - pd.Timedelta(days=365)].mean()
    c15 = builder(cm=1.5).R.mean()
    rnd95 = np.nan
    if random_runs:
        try: rnd95 = sorted(builder(rnd=shuffler).R.mean() for _ in range(random_runs))[int(0.95 * random_runs) - 1]
        except TypeError: pass
    checks = {"clustered t >= t*": ct >= ts, "year-block CI > 0": lo > 0, ">= 60% full years +": (full > 0).mean() >= 0.6,
              "last 5y and 12m +": l5 > 0 and l1 > 0, "1.5x costs +": c15 > 0, "beats random 95th": (r.mean() > rnd95) if np.isfinite(rnd95) else True}
    core_ok = all(v for k, v in checks.items() if k in ("year-block CI > 0", ">= 60% full years +", "last 5y and 12m +", "1.5x costs +"))
    verdict = "PASS" if all(checks.values()) else ("WEAK" if r.mean() > 0 and core_ok else "FAIL")
    out.update(mean=round(r.mean(), 4), t=round(tt, 2), clustered_t=round(ct, 2), tstar=round(ts, 2), ci_lo=round(lo, 4), ci_hi=round(hi, 4),
               years_pos=f"{int((full > 0).sum())}/{len(full)}", last5y=round(l5, 4), last12m=round(l1, 4), costs15=round(c15, 4),
               random95=round(rnd95, 4) if np.isfinite(rnd95) else "", verdict=verdict)
    lines = [f"{verdict:5s} {name} [{family}] — n {n} ({n / max(len(yrs), 1):.0f}/yr), mean {r.mean():+.3f}, t {tt:+.2f}, clustered t {ct:+.2f} (t* {ts:.2f}, idea #{N}), "
             f"year-block CI [{lo:+.3f}, {hi:+.3f}], full years + {out['years_pos']}, last 5y {l5:+.3f}, last 12m {l1:+.3f}, costs x1.5 {c15:+.3f}, random 95th {rnd95:+.3f}",
             "      failed: " + (", ".join(k for k, v in checks.items() if not v) or "none")]
    # walk-forward worst-period switches
    v = F.D["VIX"].close.shift(1).reindex(t.t.dt.normalize()).ffill().values
    keys = {"month": t.t.dt.month, "weekday": t.t.dt.dayofweek, "VIX band": pd.Series(pd.cut(v, [0, 15, 20, 30, 300], labels=[0, 1, 2, 3]), index=t.index).astype(float)}
    if t.m.nunique() > 1: keys["market"] = t.m
    adopt = []
    for dim, key in keys.items():
        base, keep, kept, tot = _wf(t, key)
        if tot and keep > base and kept >= 0.5 * tot: adopt.append(f"{dim} ({base:+.0f} -> {keep:+.0f})")
    on_y = [y for y in ys.index if y - 3 in ys.index and ys.loc[y - 3:y - 1].sum() > 0]
    pb, pk = ys[ys.index >= ys.index.min() + 3].sum(), ys.loc[on_y].sum() if on_y else 0.0
    if pk > pb and len(on_y) >= 0.5 * (len(ys) - 3): adopt.append(f"paradigm 3y ({pb:+.0f} -> {pk:+.0f})")
    out["switches"] = "; ".join(adopt); lines.append("      walk-forward switches that help: " + (out["switches"] or "none"))
    # portfolio contribution
    if core is not None and len(core):
        cm_ = core.groupby(pd.to_datetime(core.t).dt.to_period("M")).R.sum(); m = t.groupby(t.t.dt.to_period("M")).R.sum().reindex(cm_.index, fill_value=0)
        sc = cm_.std() / m.std() if m.std() > 0 else 0.0; comb = cm_ + sc * m; w12 = lambda x: x.rolling(12).sum().min()
        better = comb.mean() > cm_.mean() and w12(comb) >= w12(cm_) - 0.1 * abs(w12(cm_))
        out.update(corr=round(cm_.corr(m), 2), adds=("yes" if better else "no"))
        lines.append(f"      portfolio (risk-matched): corr {cm_.corr(m):+.2f}, mean/month {comb.mean():+.2f} vs core {cm_.mean():+.2f}, worst 12m {w12(comb):+.1f} vs {w12(cm_):+.1f}, "
                     f"in the core's 10 worst months {sc * m[cm_.nsmallest(10).index].sum():+.1f} -> {'ADDS' if better else 'does not add'}")
    if not quiet: print("\n".join(lines), flush=True)
    if register:
        new = not os.path.exists(REG); cols = ["date", "name", "family", "markets", "n", "mean", "t", "clustered_t", "tstar", "ci_lo", "ci_hi", "years_pos",
                                               "last5y", "last12m", "costs15", "random95", "verdict", "switches", "corr", "adds"]
        with open(REG, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if new: w.writeheader()
            w.writerow({k: out.get(k, "") for k in cols})
    return out, t
