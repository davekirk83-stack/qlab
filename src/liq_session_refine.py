"""Doc 224 addendum 4 — refine the session-open magnet (DK 16:07: "3 times in 4 is still an edge, which can be refined").
Trade toward the NEARER cluster from the open with the stop set by multiples of the target distance (k = 1, 1.5, 2), not at the opposite cluster,
so the random-walk win rate is known exactly: k / (1 + k). Exit at target / stop / session end (8h). Then split by the nearer cluster's leverage
tier, its age, how lopsided the distances are, session, and the 200-day trend, to find where the pull is strongest."""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import liq_session_test as S
H, L, C, O, N, IX = S.H, S.L, S.C, S.O, S.N, S.IX
ma = pd.Series(C).rolling(4 * 24 * 200).mean().values
rows = []
for sess, ts in S.opens.items():
    for t in ts:
        j = S.pos[t]
        if j < 2000 or j + S.W >= N: continue
        p = O[j]; mL = (S.SL <= j - 1) & (S.TL > j - 1) & (S.LL < p) & (S.LL > p * 0.95); mS = (S.SS <= j - 1) & (S.TS > j - 1) & (S.LS > p) & (S.LS < p * 1.05)
        if not mL.any() or not mS.any(): continue
        iL = np.nonzero(mL)[0][np.argmax(S.LL[mL])]; iS = np.nonzero(mS)[0][np.argmin(S.LS[mS])]
        dL, dS = p / S.LL[iL] - 1, S.LS[iS] / p - 1
        side, d, lev, age = (1, dS, S.VS[iS], j - S.SS[iS]) if dS < dL else (-1, dL, S.VL[iL], j - S.SL[iL])
        res = {}
        for k in (1.0, 1.5, 2.0):
            tgt, stp = p * (1 + side * d), p * (1 - side * k * d); r = None
            for b in range(j, j + S.W):
                hs = L[b] <= stp if side == 1 else H[b] >= stp; ht = H[b] >= tgt if side == 1 else L[b] <= tgt
                if hs: r = (-k * d * 100 - 0.04, 0); break
                if ht: r = (d * 100 - 0.04, 1); break
            if r is None: r = (side * (C[j + S.W - 1] / p - 1) * 100 - 0.04, np.nan)
            res[k] = r
        rows.append(dict(t=t, sess=sess, side=side, d=d * 100, ratio=min(dL, dS) / max(dL, dS), lev=lev, age_h=age / 4,
                         trend=np.sign(p - ma[j]) if np.isfinite(ma[j]) else 0, **{f"r{k}": res[k][0] for k in res}, **{f"w{k}": res[k][1] for k in res}))
t = pd.DataFrame(rows)
def show(nm, g, k=1.0):
    w = g[f"w{k}"].dropna(); r = g[f"r{k}"]; tt = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 else np.nan
    print(f"   {nm:34s} n{len(g):5d} | target hit first {100 * w.mean():5.1f}% vs chance {100 * k / (1 + k):.0f}% (decided {len(w)}) | avg {r.mean():+.3f}% (t {tt:+.2f}) "
          f"| 2020-22 {r[g.t.dt.year <= 2022].mean():+.3f}  2023-26 {r[g.t.dt.year >= 2023].mean():+.3f}")
for k in (1.0, 1.5, 2.0):
    print(f"\n== Toward the nearer cluster, stop = {k}x the target distance (chance {100 * k / (1 + k):.0f}%)"); show("all opens", t, k)
k = 1.0; print(f"\n== Splits (stop = 1x target distance, chance 50%)")
for s in ("Asia", "London", "New York"): show(f"session {s}", t[t.sess == s], k)
for lv in (100, 50, 25, 10, 5): show(f"nearer cluster {lv}x", t[t.lev == lv], k)
for a, b in ((0, .4), (.4, .7), (.7, 1.01)): show(f"near/far distance ratio {a}-{b}", t[(t.ratio >= a) & (t.ratio < b)], k)
for a, b in ((0, .5), (.5, 1), (1, 2), (2, 9)): show(f"target {a}-{b}% away", t[(t.d >= a) & (t.d < b)], k)
for a, b in ((0, 6), (6, 24), (24, 1e9)): show(f"cluster age {a}-{b}h", t[(t.age_h >= a) & (t.age_h < b)], k)
show("target above (buy)", t[t.side == 1], k); show("target below (sell)", t[t.side == -1], k)
show("buy, above 200-day", t[(t.side == 1) & (t.trend == 1)], k); show("sell, below 200-day", t[(t.side == -1) & (t.trend == -1)], k)
show("with the trend (either side)", t[t.side == t.trend], k); show("against the trend", t[t.side == -t.trend], k)
t.to_csv("runs/gate/liq_session_refine.csv", index=False)
