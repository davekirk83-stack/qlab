"""Doc 207 — the external reviewer's frequency ideas, through the same checks as docs 202-203 (DK 10 Nov 05:10).
Same honest daily simulator (src/fifty_ideas.py), 7 indices + gold, 2000-2026. Overnight = enter at the close, exit at the next OPEN
(close-entry is fine here only if the signal is decided on the final close; live would decide ~20 min early — see doc 206).
Checks: t vs t* (registry now 246 ideas), >= 60% of years +, last 5 years +, last year +, costs x1.5 +, beats 95th pct of 100 random-entry runs."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
from statistics import NormalDist
NTRIED = 246; TSTAR = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / NTRIED)) / 2)
up = lambda d: d.close > d.close.rolling(200).mean(); ma = lambda c, n: c.rolling(n).mean()

def overnight(k, entry, cm=1.0):
    d = F.D[k]; O, C, A = d.open.values, d.close.values, d.atr.values; E = entry.reindex(d.index).fillna(False).values; cost = F.COST[k] * cm
    out = []
    for i in np.where(E[:-1])[0]:
        if np.isfinite(A[i]) and A[i] > 0: out.append((d.index[i], (O[i + 1] - C[i] - cost * C[i] * 2 - 0.06 / 365 * 1.4 * C[i]) / A[i]))
    return out
def runc(k, entry, exit_, maxd, stop, cm=1.0):
    old = F.COST[k]; F.COST[k] = old * cm
    try: return F.run(k, entry, 1, exit_, maxd, stop=stop)
    finally: F.COST[k] = old

def tom(d):
    t = d.index; return pd.Series(t == (t + pd.offsets.BMonthEnd(0)), index=t)
def mdd(d):
    dn = (d.close.diff() < 0).astype(int).rolling(5).sum() >= 4; return up(d) & (d.close < ma(d.close, 5)) & dn
IDEAS = {
  "ON1 overnight every day (close -> next open)":            ("on", lambda d: pd.Series(True, index=d.index)),
  "ON2 overnight above 200-day":                             ("on", lambda d: up(d)),
  "ON3 overnight after 2 down closes, above 200-day":        ("on", lambda d: up(d) & (d.close.diff() < 0) & (d.close.diff().shift(1) < 0)),
  "ON4 overnight after RSI(2) < 10, above 200-day":          ("on", lambda d: up(d) & (F.rsi(d.close, 2) < 10)),
  "TOM last day of month -> close of day 3, stop 5 ATR":     ("run", lambda d: (tom(d), None, 3, 5.0)),
  "MDD 4 of 5 days down, < 5MA, above 200MA, exit > 5MA":    ("run", lambda d: (mdd(d), d.close > ma(d.close, 5), 10, 3.0)),
  "RSI(4) < 25 above 200MA, exit RSI(4) > 55":               ("run", lambda d: (up(d) & (F.rsi(d.close, 4) < 25), F.rsi(d.close, 4) > 55, 10, 3.0)),
  "RSI(2) < 10 above 200MA, exit > 5MA (Connors base)":      ("run", lambda d: (up(d) & (F.rsi(d.close, 2) < 10), d.close > ma(d.close, 5), 10, 3.0)),
}
def go(kind, fn, cm=1.0, rnd=None):
    out = []
    for k in F.IXG:
        d = F.D[k]
        if kind == "on":
            e = fn(d) if rnd is None else rnd(k, fn(d)); out += overnight(k, e, cm)
        else:
            e, x, md, st = fn(d); e = e if rnd is None else rnd(k, e); out += runc(k, e, x, md, st, cm)
    return pd.DataFrame(out, columns=["t", "R"])
rng = np.random.default_rng(7)
def shuffler(k, e):
    e = e.reindex(F.D[k].index).fillna(False); n = int(e.sum()); idx = F.D[k].index[220:-2]
    return pd.Series(F.D[k].index.isin(rng.choice(idx, size=min(n, len(idx)), replace=False)), index=F.D[k].index)

if __name__ == "__main__":
    print(f"t* = {TSTAR:.2f} ({NTRIED} ideas tried)")
    for name, (kind, fn) in IDEAS.items():
        t = go(kind, fn); r = t.R; tt = r.mean() / r.std(ddof=1) * np.sqrt(len(r)); y = t.groupby(t.t.dt.year).R.sum()
        l5 = r[t.t.dt.year >= 2022].mean(); l1 = r[t.t >= t.t.max() - pd.Timedelta(days=365)].mean(); c15 = go(kind, fn, 1.5).R.mean()
        rnd = sorted(go(kind, fn, rnd=shuffler).R.mean() for _ in range(100))[94] if kind != "on" or "every day" not in name else np.nan
        ok = [tt >= TSTAR, (y > 0).mean() >= 0.6, l5 > 0, l1 > 0, c15 > 0, (r.mean() > rnd) if np.isfinite(rnd) else True]
        verdict = "PASS" if all(ok) else ("PASS except t" if all(ok[1:]) and tt >= 2 else "FAIL")
        print(f"{verdict:13s} | {name:55s} | n{len(r):5d} ({len(r)/max(len(y),1):.0f}/yr) mean {r.mean():+.3f} t {tt:+.2f} | years + {int((y>0).sum())}/{len(y)} | last5y {l5:+.3f} last1y {l1:+.3f} | costs x1.5 {c15:+.3f} | random95 {rnd:+.3f}", flush=True)
