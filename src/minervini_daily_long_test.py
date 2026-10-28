"""Doc 151b: Minervini VCP pivot, as in doc 151, on 20 years of DAILY data (4,700 US stocks, 2005-2026). Same rules — his entry is a buy-stop
at the pivot with the stop fixed in advance, so daily bars can model it: fill at max(open, pivot); if the entry day's low also reaches the stop
it counts as stopped out (worst case). Stop = max(prior 10-day low, entry x 0.925). Half off at +20%, breakeven after a close >= +2R,
rest exits on a close below SMA50. Market: SPY above SMA50 > SMA200 with SMA50 rising. Costs 0.20%/side + 6.5%/yr.
Control (50 draws): random eligible days (price >= $10, $5m volume, SPY filter on), entry at the open, stop = max(prior 10-day low,
entry x 0.925), same management. Dev 2005-2018, holdout 2019 on."""
import glob, os, numpy as np, pandas as pd, multiprocessing as mp
COST, FIN = 0.002, 0.065; HOLD = pd.Timestamp("2019-01-01")
spy = pd.read_csv("data_eqd/SPY.csv", parse_dates=["t"]).set_index("t").adj
s50, s200 = spy.rolling(50).mean(), spy.rolling(200).mean(); sok = ((spy > s50) & (s50 > s200) & (s50 > s50.shift(10))).shift(1)
D = {}
for f in glob.glob("data_stk2/*.csv"):
    d = pd.read_csv(f, parse_dates=["t"]).set_index("t"); d = d[~d.index.duplicated()].dropna(); d = d[(d.low > 0)]
    if len(d) > 300: D[os.path.basename(f)[:-4]] = d
rs = pd.DataFrame({s: d.close / d.close.shift(252) - 1 for s, d in D.items()}).rank(axis=1, pct=True)
X = {}
for s, d in D.items():
    o, c, h, l, v = d.open, d.close, d.high, d.low, d.volume
    m50, m150, m200 = (c.rolling(n).mean() for n in (50, 150, 200))
    tt = (c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(21)) & (m50 > m150) & (c > m50) & \
         (c >= 1.3 * l.rolling(252).min()) & (c >= 0.75 * h.rolling(252).max()) & (rs[s].reindex(d.index) >= 0.70)
    rg = lambda a, b: (h.shift(a).rolling(b - a).max() - l.shift(a).rolling(b - a).min()) / h.shift(a).rolling(b - a).max()
    r1, r2, r3 = rg(0, 10), rg(10, 25), rg(25, 50)
    liq = (c >= 10) & ((c * v).rolling(20).median() >= 5e6)
    vcp = tt & (r1 < 0.75 * r2) & (r2 < 0.75 * r3) & (r1 <= 0.12) & (v.rolling(10).mean() < v.rolling(50).mean()) & liq
    mk = sok.reindex(d.index).fillna(False)
    X[s] = dict(idx=d.index, O=o.values, H=h.values, L=l.values, C=c.values, m50=m50.values,
                piv=h.rolling(10).max().shift(1).values, plo=l.rolling(10).min().shift(1).values,
                sig=(vcp.shift(1).fillna(False) & mk).values.astype(bool), el=(liq.shift(1).fillna(False) & mk).values.astype(bool))
del D, rs
def trade(x, i, rnd):
    O, H, L, C, M = x["O"], x["H"], x["L"], x["C"], x["m50"]; n = len(C)
    e = O[i] if rnd else max(O[i], x["piv"][i]); stop = max(x["plo"][i], e * 0.925)
    if not stop < e: return None
    risk = (e - stop) / e; eC = e * (1 + COST)
    if L[i] <= stop: return x["idx"][i], (stop * (1 - COST) / eC - 1), risk, i
    legs = []; w = 1.0; st = stop
    for j in range(i + 1, n):
        if L[j] <= st: legs.append((w, min(st, O[j]))); w = 0; break
        if w == 1.0 and H[j] >= e * 1.2: legs.append((0.5, max(e * 1.2, O[j]))); w = 0.5
        if C[j] >= e * (1 + 2 * risk): st = max(st, e)
        if C[j] < M[j]: legs.append((w, C[j])); w = 0; break
    if w > 0: legs.append((w, C[n - 1])); j = n - 1
    days = (x["idx"][j] - x["idx"][i]).days
    return x["idx"][i], sum(ww * (px * (1 - COST) / eC - 1) for ww, px in legs) - FIN * days / 365, risk, j
def run(hold, rnd=False, counts=None, seed=0):
    rng = np.random.default_rng(seed); out = []; cnt = {}
    for s, x in X.items():
        seg = (x["idx"] >= HOLD) == hold
        if not rnd: cand = np.flatnonzero(x["sig"][:-1] & seg[:-1] & (x["H"][:-1] > x["piv"][:-1]))
        else:
            m = counts.get(s, 0); pool = np.flatnonzero(x["el"][:-1] & seg[:-1] & np.isfinite(x["plo"][:-1]))
            if not m or not len(pool): continue
            cand = np.sort(rng.choice(pool, min(m * 3, len(pool)), replace=False))
        busy = -1; k = 0
        for i in cand:
            if i <= busy: continue
            if rnd and k >= counts[s]: break
            r = trade(x, i, rnd)
            if r is None: continue
            out.append(r); busy = r[3]; k += 1
        cnt[s] = k
    return out, cnt
def summ(t):
    r = np.array([a[1] for a in t]); R = r / np.maximum([a[2] for a in t], 0.002)
    return f"n{len(r):5} win {100*(r>0).mean():3.0f}% avg {R.mean():+.2f}R {100*r.mean():+.2f}%/trade sum {R.sum():+.0f}R", R.mean()
_C = None
def _draw(k):
    hold, cnt = _C; return summ(run(hold, True, cnt, k)[0])[1]
lines = []
for seg, hold in (("DEV 2005-2018", False), ("HOLD 2019-2026", True)):
    real, cnt = run(hold); txt, mR = summ(real)
    yrs = sorted(set(a[0].year for a in real))
    by = " ".join(f"{y}:{np.mean([a[1]/max(a[2],0.002) for a in real if a[0].year==y]):+.2f}R" for y in yrs)
    _C = (hold, cnt)
    with mp.get_context("fork").Pool(2) as p: ms = np.array(p.map(_draw, range(50)))
    lines.append(f"{seg}: {txt} | random {np.median(ms):+.2f}R, setup beats {100*(ms<mR).mean():.0f}%\n  by year {by}"); print(lines[-1], flush=True)
open("runs/minervini_daily_long_test.txt", "w").write("\n".join(lines) + "\n")
