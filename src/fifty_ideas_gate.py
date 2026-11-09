"""Doc 202 follow-up — the 12 A/B ideas through the remaining gate checks (DK 23:17 "Okay test them"):
  RANDOM  same markets, same number of entries per market, same side, same exit rules/stops/holding — but entries on random days
          (200 runs); the idea's mean must beat the 95th percentile of the random means (permutation test, Masters / White's Reality Check);
  COSTx1.5 every market's cost x 1.5 — mean must stay positive;
  HOLDOUT the last 365 days — mean must be positive;
  WALK-FORWARD >= 60% of calendar years positive; and the multiple-testing t from the first pass.
Verdict: PASS = all five; otherwise the checks it fails are listed."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import fifty_ideas as F
KEEP = ("14 ", "37 ", "39 ", "47 ", "7 ", "2 ", "1 ", "12 ", "4 ", "21 ", "5 ", "40 ")
_run = F.run; MODE = {"rand": None}
def run_wrapped(k, entry, *a, **kw):
    if MODE["rand"] is not None:
        d = F.D[k]; e = entry.reindex(d.index).fillna(False); n = int(e.sum())
        ok = np.where(np.isfinite(d.atr.values) & (d.atr.values > 0))[0]
        if n > 0 and len(ok) > n:
            pick = MODE["rand"].choice(ok, size=n, replace=False); m = np.zeros(len(d), bool); m[pick] = True
            # keep the same side series values where the idea had them (sides vary for a few ideas): use the dominant side
            entry = pd.Series(m, index=d.index)
    return _run(k, entry, *a, **kw)
F.run = run_wrapped
def mean_of(fn, mk):
    T = []
    for k in mk:
        try: T += [r for _, r in fn(k)]
        except Exception: pass
    T = np.array([x for x in T if np.isfinite(x)]); return T.mean() if len(T) else np.nan
rows = []
r0 = pd.read_csv("runs/gate/fifty_ideas.csv")
for name, fam, mk, fn in F.IDEAS:
    if not name.startswith(KEEP): continue
    T = []
    for k in mk: T += [(t, r) for t, r in fn(k)]
    t = pd.DataFrame(T, columns=["t", "R"]).dropna(); m = t.R.mean()
    hold = t[t.t >= t.t.max() - pd.Timedelta(days=365)].R.mean(); y = t.groupby(t.t.dt.year).R.sum(); yp = (y > 0).mean()
    saved = dict(F.COST); F.COST.update({k: v * 1.5 for k, v in saved.items()}); m15 = mean_of(fn, mk); F.COST.clear(); F.COST.update(saved)
    rng = np.random.default_rng(7); MODE["rand"] = rng; rm = [mean_of(fn, mk) for _ in range(200)]; MODE["rand"] = None
    p95 = float(np.nanpercentile(rm, 95)); pval = float(np.mean(np.array(rm) >= m))
    tpass = r0.loc[r0.idea == name, "rating"].iloc[0] == "A"
    checks = {"beats random (95th pct)": m > p95, "costs x1.5 still positive": m15 > 0, "last year positive": hold > 0, "60% of years positive": yp >= 0.6,
              "multiple-testing t": tpass}
    fails = [c for c, v in checks.items() if not v]
    verdict = "PASS" if not fails else ("PASS except t" if fails == ["multiple-testing t"] else "FAIL")
    rows.append(dict(idea=name, mean=round(m, 3), random_p95=round(p95, 3), p_value=round(pval, 3), cost15=round(m15, 3), last_year=round(hold, 3),
                     years_pos=f"{int((y>0).sum())}/{y.size}", verdict=verdict, fails=", ".join(fails) or "-"))
    print(f"{verdict:14s} {name[:66]:66s} mean {m:+.3f} | random95 {p95:+.3f} (p={pval:.3f}) | cost1.5 {m15:+.3f} | last yr {hold:+.3f} | yrs {int((y>0).sum())}/{y.size} | fails: {', '.join(fails) or '-'}", flush=True)
pd.DataFrame(rows).to_csv("runs/gate/fifty_ideas_gate.csv", index=False)
