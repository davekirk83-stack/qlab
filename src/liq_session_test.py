"""Doc 224 addendum 3 — DK 16:05: "a cluster study based on each session open is also worthy of a look".
At each session open (Asia 00:00 Tokyo = 00:00 UTC, London 08:00 London time, New York 09:30 New York time; DST handled), on 15-min BTC 2020-26:
the nearest LIVE long-liquidation cluster below and short-liquidation cluster above (within 5%). Questions:
 1. MAGNET: is the nearer cluster hit first more often than a random walk says it should (P = far / (near + far))?
 2. Trade toward the nearer cluster from the open: target = that cluster, stop = the opposite cluster, else exit at session end (8h). 0.04% costs.
 3. Same, toward the HEAVIER side (more leverage-weighted clusters within 3%)."""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import liq_levels_test as LT
H, L, C, O, N, IX = LT.H, LT.L, LT.C, LT.d.open.values, LT.N, LT.IX
def arr(kind):
    lv = LT.levels(kind); S = np.array([s for s, _, _ in lv]); LV = np.array([l for _, l, _ in lv]); LEV = np.array([v for _, _, v in lv]); tb = []
    for s, l, _ in lv:
        seg = np.nonzero((L[s:] <= l) if kind == "long" else (H[s:] >= l))[0]; tb.append(s + seg[0] if len(seg) else N + 10)
    return S, LV, np.array(tb), LEV
SL, LL, TL, VL = arr("long"); SS, LS, TS, VS = arr("short"); W = 32
pos = pd.Series(np.arange(N), index=IX)
U = IX.tz_localize("UTC") if IX.tz is None else IX.tz_convert("UTC"); lon = U.tz_convert("Europe/London"); ny = U.tz_convert("America/New_York")
opens = {"Asia": IX[(U.hour == 0) & (U.minute == 0)], "London": IX[(lon.hour == 8) & (lon.minute == 0)], "New York": IX[(ny.hour == 9) & (ny.minute == 30) & (ny.dayofweek < 5)]}
rows = []
for sess, ts in opens.items():
    for t in ts:
        j = pos[t]
        if j < 2000 or j + W >= N: continue
        p = O[j]; mL = (SL <= j - 1) & (TL > j - 1) & (LL < p) & (LL > p * 0.95); mS = (SS <= j - 1) & (TS > j - 1) & (LS > p) & (LS < p * 1.05)
        if not mL.any() or not mS.any(): continue
        lo, hi = LL[mL].max(), LS[mS].min(); dL, dS = p / lo - 1, hi / p - 1
        wL = (1 / VL[mL & (LL > p * 0.97)]).sum(); wS = (1 / VS[mS & (LS < p * 1.03)]).sum()     # weight: higher leverage = smaller 1/lev... use count weighted by 1/lev
        first = None
        for k in range(j, j + W):
            a, b = L[k] <= lo, H[k] >= hi
            if a and b: first = "both"; break
            if a: first = "long"; break
            if b: first = "short"; break
        def trade(side):   # side +1 = buy toward short cluster above, -1 = sell toward long cluster below
            tgt, stp = (hi, lo) if side == 1 else (lo, hi)
            for k in range(j, j + W):
                hs, ht = (L[k] <= stp, H[k] >= tgt) if side == 1 else (H[k] >= stp, L[k] <= tgt)
                if hs: return side * (stp / p - 1) * 100 - 0.04
                if ht: return side * (tgt / p - 1) * 100 - 0.04
            return side * (C[j + W - 1] / p - 1) * 100 - 0.04
        near = 1 if dS < dL else -1; heavy = 1 if wS > wL else -1
        rows.append((t, sess, dL * 100, dS * 100, first, near, trade(near), trade(heavy), trade(-near)))
t = pd.DataFrame(rows, columns=["t", "sess", "dL", "dS", "first", "near", "r_near", "r_heavy", "r_far"])
t["p_rw"] = np.where(t.near == 1, t.dL / (t.dL + t.dS), t.dS / (t.dL + t.dS))       # random-walk chance the nearer one is hit first
t["near_first"] = np.where(t.near == 1, t["first"] == "short", t["first"] == "long")
for sess in ("Asia", "London", "New York", "all"):
    g = t if sess == "all" else t[t.sess == sess]; dec = g[g["first"].isin(["long", "short"])]
    print(f"== {sess} opens: n {len(g)} | median distance to nearest long cluster {g.dL.median():.2f}%, short cluster {g.dS.median():.2f}% | "
          f"either hit within 8h {100 * g['first'].notna().mean():.0f}%")
    print(f"   MAGNET: nearer cluster hit first {100 * dec.near_first.mean():.1f}% vs random walk {100 * dec.p_rw.mean():.1f}%  (n {len(dec)})")
    for nm, c in (("toward NEARER cluster", "r_near"), ("toward FARTHER cluster", "r_far"), ("toward HEAVIER side (3%)", "r_heavy")):
        r = g[c]; tt = r.mean() / r.std() * np.sqrt(len(r)); h = lambda a, b: r[g.t.dt.year.between(a, b)].mean()
        print(f"   {nm:25s} avg {r.mean():+.3f}% (t {tt:+.2f}, win {100 * (r > 0).mean():.0f}%) | 2020-22 {h(2020, 2022):+.3f}%  2023-26 {h(2023, 2026):+.3f}%")
