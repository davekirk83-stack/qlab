"""Doc 224 addendum 2 — DK 16:03: "once the last cluster is gone in a region, logic dictates it will reverse to the other extremity".
At every first tap of a LONG liquidation level (15-min BTC, 2020-26): count live long levels still below within the region (R = 5% / 10%).
'Cleared' = none left. Target = live SHORT liquidation levels above at that moment: the NEAREST one, and the FARTHEST within the region ('the
other extremity'). Race over the next 7 days: does price reach the target before it falls S% below the tapped level (S = 1.5% / 3%)?
Trade = buy at the level, sell at the target or the stop, else at 7 days; 0.04% costs. Compared with taps that still have levels below."""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import liq_levels_test as LT
H, L, C, N, IX = LT.H, LT.L, LT.C, LT.N, LT.IX
def arr(kind):
    lv = LT.levels(kind); S = np.array([s for s, _, _ in lv]); LV = np.array([l for _, l, _ in lv]); tb = []
    for s, l, _ in lv:
        seg = np.nonzero((L[s:] <= l) if kind == "long" else (H[s:] >= l))[0]; tb.append(s + seg[0] if len(seg) else N + 10)
    return S, LV, np.array(tb)
SL, LL, TL = arr("long"); SS, LS, TS = arr("short"); W = 4 * 24 * 7
def race(j, lvl, tgt, stop):
    e = min(N - 1, j + W)
    for k in range(j + 1, e + 1):
        if L[k] <= stop: return (stop / lvl - 1) * 100 - 0.04, "stop", k - j
        if H[k] >= tgt: return (tgt / lvl - 1) * 100 - 0.04, "target", k - j
    return (C[e] / lvl - 1) * 100 - 0.04, "time", e - j
rows = []
for k in np.argsort(TL):
    j = TL[k]; lvl = LL[k]
    if j >= N - W - 2: continue
    liveL = (SL <= j) & (TL > j); liveS = (SS <= j) & (TS > j)
    for R in (0.05, 0.10):
        below = (liveL & (LL < lvl) & (LL > lvl * (1 - R))).sum()
        up = LS[liveS & (LS > lvl) & (LS < lvl * (1 + R))]
        if not len(up): continue
        for which, tgt in (("nearest", up.min()), ("farthest", up.max())):
            for S in (0.015, 0.03):
                r, how, bars = race(j, lvl, tgt, lvl * (1 - S))
                rows.append((IX[j], R, below == 0, which, S, (tgt / lvl - 1) * 100, r, how, bars / 4))
t = pd.DataFrame(rows, columns=["t", "R", "cleared", "tgt", "stop", "dist", "ret", "how", "hours"]).drop_duplicates(subset=["t", "R", "tgt", "stop"])
print("Taps of LONG liquidation levels; target = live SHORT liquidation level above; 7-day race vs a stop below the tapped level; 0.04% costs\n")
for R in (0.05, 0.10):
    for which in ("nearest", "farthest"):
        for S in (0.015, 0.03):
            print(f"region {R:.0%}, target = {which} short cluster, stop {S:.1%} under the level")
            for nm, g in (("CLEARED (none left below)", t[(t.R == R) & (t.tgt == which) & (t.stop == S) & t.cleared]),
                          ("levels still below", t[(t.R == R) & (t.tgt == which) & (t.stop == S) & ~t.cleared])):
                if len(g) < 10: print(f"   {nm:26s} n{len(g)}"); continue
                tt = g.ret.mean() / g.ret.std() * np.sqrt(len(g)); h = lambda y: g[g.t.dt.year.isin(y)].ret.mean()
                print(f"   {nm:26s} n{len(g):5d} | target {g.dist.median():.1f}% away | reached {100 * (g.how == 'target').mean():.0f}%, stopped {100 * (g.how == 'stop').mean():.0f}% "
                      f"| avg trade {g.ret.mean():+.3f}% (t {tt:+.2f}) | 2020-22 {h(range(2020, 2023)):+.3f}%, 2023-26 {h(range(2023, 2027)):+.3f}% | median hours to target {g[g.how == 'target'].hours.median():.0f}")
