"""Doc 202 follow-up (DK 23:21): the fallow-period test on the 50-ideas candidates. Same method as doc 201's per-condition test:
one condition at a time (month, weekday, VIX band at the previous close); for each year, the buckets to skip are chosen ONLY from earlier
years (>= 8 of them; bucket >= 15 earlier trades with a negative average); adopted only if, out of sample, it raises the total AND keeps
>= 50% of the trades."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import fifty_ideas as F
KEEP = ("14 ", "37 ", "39 ", "47 ", "7 ", "2 ", "1 ", "12 ", "4 ", "21 ", "5 ", "40 ")
vix = F.D["VIX"].close.shift(1)
def test(t, cond):
    t = t.assign(y=t.t.dt.year); rows = []; last_off = set()
    for y in sorted(t.y.unique()):
        past, cur = t[t.y < y], t[t.y == y]
        if past.y.nunique() < 8: continue
        off = set(k for k, g in past.groupby(cond).R if len(g) >= 15 and g.mean() < 0)
        rows.append((cur.R.sum(), cur[~cur[cond].isin(off)].R.sum(), len(cur), int((~cur[cond].isin(off)).sum()))); last_off = off
    if not rows: return None
    a = np.array(rows); return a[:, 0].sum(), a[:, 1].sum(), int(a[:, 2].sum()), int(a[:, 3].sum()), sorted(last_off)
out = []
for name, fam, mk, fn in F.IDEAS:
    if not name.startswith(KEEP): continue
    T = []
    for k in mk: T += [(t, r) for t, r in fn(k)]
    t = pd.DataFrame(T, columns=["t", "R"]).dropna(); t["t"] = pd.to_datetime(t.t)
    t["month"] = t.t.dt.month_name().str[:3]; t["weekday"] = t.t.dt.day_name().str[:3]
    t["vix"] = pd.cut(vix.reindex(t.t).ffill().values, [0, 15, 20, 30, 200], labels=["VIX<15", "VIX15-20", "VIX20-30", "VIX>30"]).astype(str)
    line = [f"{name[:64]:64s}"]; adopted = []
    for c in ("month", "weekday", "vix"):
        r = test(t, c)
        if r is None: continue
        a, s, n, kk, off = r; ok = s > a and kk >= 0.5 * n and off
        line.append(f"{c}: {a:+.1f}->{s:+.1f} kept {kk}/{n}{' ADOPT ' + ','.join(off) if ok else ''}")
        if ok: adopted.append(f"{c} off: {', '.join(off)} ({a:+.1f} -> {s:+.1f})")
    s = " | ".join(line) + ("\n      => " + "; ".join(adopted) if adopted else "\n      => run every signal (no switch helps out of sample)")
    print(s, flush=True); out.append(s)
open("runs/gate/fifty_ideas_fallow.txt", "w").write("\n".join(out) + "\n")
