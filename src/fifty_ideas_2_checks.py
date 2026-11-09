"""Doc 203 — the A/B ideas from #51-100 through the remaining gate checks (random entries x200, costs x1.5, last year, 60% of years,
multiple-testing t) and the per-condition fallow test (month / weekday / VIX; walk-forward by year; adopt only if it raises the
out-of-sample total and keeps >= 50% of trades). Same code paths as doc 202."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import fifty_ideas as F, fifty_ideas_2 as F2
r0 = pd.read_csv("runs/gate/fifty_ideas_2.csv"); keep = set(r0[r0.rating.isin(["A", "B"])].idea)
_run = F.run; MODE = {"rand": None}
def run_wrapped(k, entry, *a, **kw):
    if MODE["rand"] is not None:
        d = F.D[k]; e = entry.reindex(d.index).fillna(False); n = int(e.sum()); ok = np.where(np.isfinite(d.atr.values) & (d.atr.values > 0))[0]
        if 0 < n < len(ok): m = np.zeros(len(d), bool); m[MODE["rand"].choice(ok, size=n, replace=False)] = True; entry = pd.Series(m, index=d.index)
    return _run(k, entry, *a, **kw)
F.run = run_wrapped; F2.run = run_wrapped
def mean_of(fn, mk):
    T = []
    for k in mk:
        try: T += [r for _, r in fn(k)]
        except Exception: pass
    T = np.array([x for x in T if np.isfinite(x)]); return T.mean() if len(T) else np.nan
vix = F.D["VIX"].close.shift(1)
def fallow(t, cond):
    t = t.assign(y=t.t.dt.year); rows = []; off_last = []
    for y in sorted(t.y.unique()):
        past, cur = t[t.y < y], t[t.y == y]
        if past.y.nunique() < 8: continue
        off = set(k for k, g in past.groupby(cond).R if len(g) >= 15 and g.mean() < 0)
        rows.append((cur.R.sum(), cur[~cur[cond].isin(off)].R.sum(), len(cur), int((~cur[cond].isin(off)).sum()))); off_last = sorted(off)
    if not rows: return None
    a = np.array(rows); return a[:, 0].sum(), a[:, 1].sum(), int(a[:, 2].sum()), int(a[:, 3].sum()), off_last
out = []
for name, fam, mk, fn in F2.IDEAS:
    if name not in keep: continue
    T = []
    for k in mk: T += [(t, r) for t, r in fn(k)]
    t = pd.DataFrame(T, columns=["t", "R"]).dropna(); t["t"] = pd.to_datetime(t.t); m = t.R.mean()
    hold = t[t.t >= t.t.max() - pd.Timedelta(days=365)].R.mean(); y = t.groupby(t.t.dt.year).R.sum(); yp = (y > 0).mean()
    saved = dict(F.COST); F.COST.update({k: v * 1.5 for k, v in saved.items()}); m15 = mean_of(fn, mk); F.COST.clear(); F.COST.update(saved)
    MODE["rand"] = np.random.default_rng(7); rm = [mean_of(fn, mk) for _ in range(200)]; MODE["rand"] = None
    p95 = float(np.nanpercentile(rm, 95)); tpass = r0.loc[r0.idea == name, "rating"].iloc[0] == "A"
    checks = {"beats random": m > p95, "costs x1.5": m15 > 0, "last year +": hold > 0, "60% years +": yp >= 0.6, "multiple-testing t": tpass}
    fails = [c for c, v in checks.items() if not v]; verdict = "PASS" if not fails else ("PASS except t" if fails == ["multiple-testing t"] else "FAIL")
    t["month"] = t.t.dt.month_name().str[:3]; t["weekday"] = t.t.dt.day_name().str[:3]
    t["vix"] = pd.cut(vix.reindex(t.t).ffill().values, [0, 15, 20, 30, 200], labels=["VIX<15", "VIX15-20", "VIX20-30", "VIX>30"]).astype(str)
    adopt = []
    for c in ("month", "weekday", "vix"):
        r = fallow(t, c)
        if r and r[1] > r[0] * 1.05 and r[3] >= 0.5 * r[2] and r[4]: adopt.append(f"{c} off {','.join(r[4])} ({r[0]:+.0f}->{r[1]:+.0f})")
    s = (f"{verdict:14s} {name[:70]:70s} mean {m:+.3f} | random95 {p95:+.3f} | cost1.5 {m15:+.3f} | last yr {hold:+.3f} | yrs {int((y>0).sum())}/{y.size} | "
         f"fails: {', '.join(fails) or '-'} | fallow: {'; '.join(adopt) or 'none helps (>5%)'}")
    print(s, flush=True); out.append(s)
open("runs/gate/fifty_ideas_2_checks.txt", "w").write("\n".join(out) + "\n")
