"""Doc 208 — refine the near-misses (DK 10 Nov 07:15: 'refine the ones that failed narrowly; look for superior published versions').
TOM: published McConnell-Xu window (in at close of day -2 so the last day's return is held, out at close of day +3) — our doc-207 version
entered at the close of the LAST day and so missed day -1, the strongest day. Overnight: Yahoo opens checked — FTSE 'open' = prior close on
95% of days (unusable), SPX/RUT broken pre-2010 on ~25%; bad-open days dropped, FTSE excluded, costs set to IG's published spreads + buffer.
TSMOM: the published multi-asset, vol-scaled, 1/3/12-month blend (Hurst-Ooi-Pedersen) on all 18 daily markets, not 12m on indices only."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
from statistics import NormalDist
NTRIED = 258; TSTAR = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / NTRIED)) / 2)
up = lambda d: d.close > d.close.rolling(200).mean(); ma = lambda c, n: c.rolling(n).mean()
def tdm(d):
    m = d.index.to_period("M"); s = pd.Series(1, index=d.index)
    return s.groupby(m).cumsum(), s.groupby(m).cumsum(ascending=False) if False else s[::-1].groupby(m[::-1]).cumsum()[::-1]
# IG round-trip spread (core hours) + buffer, as a fraction of price, per side
IGC = {"SPX": .00008, "NDX": .00008, "DJI": .00008, "RUT": .00015, "DAX": .00008, "N225": .00015, "GOLD": .0001}
def overnight(k, entry, cm=1.0, cost=None):
    d = F.D[k]; O, C, A = d.open.values, d.close.values, d.atr.values; E = entry.reindex(d.index).fillna(False).values
    good = (abs(d.open - d.close.shift(1)) > 1e-9).values; c = (cost or IGC)[k] * cm; out = []
    for i in np.where(E[:-1])[0]:
        if good[i + 1] and np.isfinite(A[i]) and A[i] > 0: out.append((d.index[i], (O[i + 1] - C[i] - c * C[i] * 2 - 0.06 / 365 * 1.4 * C[i]) / A[i]))
    return out
def runc(k, e, x, md, st, cm=1.0):
    old = F.COST[k]; F.COST[k] = old * cm
    try: return F.run(k, e, 1, x, md, stop=st)
    finally: F.COST[k] = old
def T(n_in, n_out, filt=False):
    def f(d):
        a, b = tdm(d); e = (b == n_in) & (up(d) if filt else True); return (e, a == n_out, n_in + n_out + 2, 5.0)
    return f
ONM = ["SPX", "NDX", "DJI", "RUT", "DAX", "N225", "GOLD"]
IDEAS = {
 "TOM-A McConnell-Xu: in close day -2, out close day +3":        ("run", F.IXG, T(2, 3)),
 "TOM-B same, only above 200-day":                               ("run", F.IXG, T(2, 3, True)),
 "TOM-C wider: in close day -5, out close day +3":               ("run", F.IXG, T(5, 3)),
 "TOM-D in close day -2, out close day +1 (shortest)":           ("run", F.IXG, T(2, 1)),
 "ON-A every night, IG costs":                                   ("on", ONM, lambda d: pd.Series(True, index=d.index)),
 "ON-B after a down close, IG costs":                            ("on", ONM, lambda d: d.close.diff() < 0),
 "ON-C after a down close above 200-day, IG costs":              ("on", ONM, lambda d: up(d) & (d.close.diff() < 0)),
 "ON-D after RSI(2) < 10 above 200-day, IG costs":               ("on", ONM, lambda d: up(d) & (F.rsi(d.close, 2) < 10)),
 "MDD+RSI4 one book: either signal, exit RSI(4) > 55":           ("run", F.IXG, lambda d: ((up(d) & (F.rsi(d.close, 4) < 25)) | (up(d) & (d.close < ma(d.close, 5)) & ((d.close.diff() < 0).astype(int).rolling(5).sum() >= 4)), F.rsi(d.close, 4) > 55, 10, 3.0)),
}
rng = np.random.default_rng(7)
def shuffler(k, e):
    e = e.reindex(F.D[k].index).fillna(False); n = int(e.sum()); idx = F.D[k].index[220:-2]
    return pd.Series(F.D[k].index.isin(rng.choice(idx, size=min(n, len(idx)), replace=False)), index=F.D[k].index)
def go(kind, mk, fn, cm=1.0, rnd=None, cost=None):
    out = []
    for k in mk:
        d = F.D[k]
        if kind == "on": e = fn(d); e = e if rnd is None else rnd(k, e); out += overnight(k, e, cm, cost)
        else:
            e, x, md, st = fn(d); e = e if rnd is None else rnd(k, e); out += runc(k, e, x, md, st, cm)
    return pd.DataFrame(out, columns=["t", "R"])
def report(name, kind, mk, fn):
    t = go(kind, mk, fn); r = t.R; tt = r.mean() / r.std(ddof=1) * np.sqrt(len(r)); y = t.groupby(t.t.dt.year).R.sum()
    l5 = r[t.t.dt.year >= 2022].mean(); l1 = r[t.t >= t.t.max() - pd.Timedelta(days=365)].mean(); c15 = go(kind, mk, fn, 1.5).R.mean()
    rnd = sorted(go(kind, mk, fn, rnd=shuffler).R.mean() for _ in range(60))[56] if "every" not in name else np.nan
    ok = [tt >= TSTAR, (y > 0).mean() >= 0.6, l5 > 0, l1 > 0, c15 > 0, (r.mean() > rnd) if np.isfinite(rnd) else True]
    v = "PASS" if all(ok) else ("PASS except t" if all(ok[1:]) and tt >= 2 else "FAIL")
    extra = f" | at old gate costs {go(kind, mk, fn, cost=F.COST).R.mean():+.3f}" if kind == "on" else ""
    per = " ".join(f"{k}:{g.R.mean():+.2f}" for k, g in [(k, pd.DataFrame(go(kind, [k], fn), columns=['t','R'])) for k in mk])
    print(f"{v:13s} | {name:55s} | n{len(r):5d} ({len(r)/max(len(y),1):.0f}/yr) mean {r.mean():+.3f} t {tt:+.2f} | yrs+ {int((y>0).sum())}/{len(y)} | last5y {l5:+.3f} 1y {l1:+.3f} | x1.5 {c15:+.3f} | rnd95 {rnd:+.3f}{extra}\n              per market: {per}", flush=True)

def tsmom():
    mk = [k for k in F.D if k not in ("VIX", "BTC", "ETH")]
    px = pd.DataFrame({k: F.D[k].close for k in mk}).ffill(); px = px[px.index.year >= 2000]
    me = px.resample("BME").last(); dr = px.pct_change(); vol = dr.rolling(60).std().resample("BME").last() * np.sqrt(252)
    mr = me.pct_change(); res = {}
    for nm, sig in {"12m only, equal size": np.sign(me.pct_change(12)),
                    "1/3/12m blend, vol-scaled (published)": (np.sign(me.pct_change(1)) + np.sign(me.pct_change(3)) + np.sign(me.pct_change(12))) / 3}.items():
        w = sig * ((0.10 / vol) if "vol" in nm else 0.10 / vol.median(axis=1).values[:, None] * 1) / len(mk) * np.sqrt(len(mk))
        w = w.clip(-2, 2); cost = pd.Series({k: F.COST.get(k, .0005) for k in mk})
        g = (w.shift(1) * mr).sum(axis=1) - (w.diff().abs() * cost).sum(axis=1) - w.shift(1).abs().sum(axis=1) * 0.03 / 12
        g = g[g.index.year >= 2002]; tt = g.mean() / g.std() * np.sqrt(len(g)); y = g.groupby(g.index.year).sum()
        print(f"TSMOM {nm:38s} | {len(mk)} markets | ann {g.mean()*12:+.1%} vol {g.std()*np.sqrt(12):.1%} t {tt:+.2f} | yrs+ {int((y>0).sum())}/{len(y)} | last5y ann {g[g.index.year>=2022].mean()*12:+.1%} | 2008 {y.get(2008,0):+.1%} 2022 {y.get(2022,0):+.1%}")
        res[nm] = g
    return res

if __name__ == "__main__":
    print(f"t* = {TSTAR:.2f} ({NTRIED} ideas tried)")
    for name, (kind, mk, fn) in IDEAS.items(): report(name, kind, mk, fn)
    tsmom()
