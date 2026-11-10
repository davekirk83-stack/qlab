"""Doc 224 addendum 5 — DK 16:11: "if it doesn't tell us direction, it does indicate extent".
At each session open: band = [nearest live long cluster below, nearest live short cluster above]. Over the 8h session:
 1. CONTAINMENT: how often price stays inside the band, vs PLACEBO bands of the same widths shuffled across other opens (same session type).
 2. Does band width predict the session's actual range (high-low) beyond what the previous 24h range already says? (regression)
 3. When an edge breaks, how far does price overshoot it (for stop placement) — and does a break of the band reach the NEXT cluster out?"""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import liq_session_test as S
H, L, C, O, N, W = S.H, S.L, S.C, S.O, S.N, S.W
rng = np.random.default_rng(5); rows = []
for sess, ts in S.opens.items():
    for t in ts:
        j = S.pos[t]
        if j < 2000 or j + W >= N: continue
        p = O[j]; mL = (S.SL <= j - 1) & (S.TL > j - 1) & (S.LL < p) & (S.LL > p * 0.90); mS = (S.SS <= j - 1) & (S.TS > j - 1) & (S.LS > p) & (S.LS < p * 1.10)
        if not mL.any() or not mS.any(): continue
        lvL = np.sort(S.LL[mL])[::-1]; lvS = np.sort(S.LS[mS])
        hi_s, lo_s = H[j:j + W].max(), L[j:j + W].min()
        rows.append(dict(t=t, sess=sess, dn=(1 - lvL[0] / p) * 100, up=(lvS[0] / p - 1) * 100,
                         dn2=(1 - lvL[1] / p) * 100 if len(lvL) > 1 else np.nan, up2=(lvS[1] / p - 1) * 100 if len(lvS) > 1 else np.nan,
                         sup=(hi_s / p - 1) * 100, sdn=(1 - lo_s / p) * 100, prev=(H[j - 96:j].max() / L[j - 96:j].min() - 1) * 100))
t = pd.DataFrame(rows); t["inside"] = (t.sup < t.up) & (t.sdn < t.dn); t["rng"] = t.sup + t.sdn; t["band"] = t.up + t.dn
print(f"Session opens with a cluster on both sides within 10%: n {len(t)}; median band: {t.dn.median():.2f}% below, {t.up.median():.2f}% above\n")
print("1. CONTAINMENT — session stays inside the cluster band:")
for sess in ("Asia", "London", "New York", "all"):
    g = t if sess == "all" else t[t.sess == sess]; pl = []
    for _ in range(200):
        k = rng.permutation(len(g)); pl.append(((g.sup.values < g.up.values[k]) & (g.sdn.values < g.dn.values[k])).mean())
    pl = np.array(pl); real = g.inside.mean()
    print(f"   {sess:9s} real {100 * real:.1f}% vs placebo (same widths, shuffled) {100 * pl.mean():.1f}% [95% {100 * np.percentile(pl, 2.5):.1f}-{100 * np.percentile(pl, 97.5):.1f}]  n {len(g)}")
    # per edge
    for nm, real_e, d, s_ in (("  top edge holds", (g.sup < g.up).mean(), g.up.values, g.sup.values), ("  bottom edge holds", (g.sdn < g.dn).mean(), g.dn.values, g.sdn.values)):
        pe = np.mean([(s_ < d[rng.permutation(len(g))]).mean() for _ in range(200)])
        print(f"      {nm:18s} real {100 * real_e:.1f}% vs placebo {100 * pe:.1f}%")
print("\n2. Does band width predict the session's range? (log-log regression)")
x1 = np.log(t.band); x0 = np.log(t.prev); y = np.log(t.rng.clip(lower=0.01))
for nm, X in (("previous 24h range only", np.c_[np.ones(len(t)), x0]), ("band width only", np.c_[np.ones(len(t)), x1]), ("both", np.c_[np.ones(len(t)), x0, x1])):
    b, *_ = np.linalg.lstsq(X, y, rcond=None); r2 = 1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    print(f"   {nm:25s} R2 {r2:.3f}  coefficients {np.round(b[1:], 3)}")
q = pd.qcut(t.band, 5, labels=False)
print("   session range by band-width quintile:", "  ".join(f"Q{i + 1} band {t.band[q == i].median():.2f}% -> range {t.rng[q == i].median():.2f}%" for i in range(5)))
print("\n3. When an edge BREAKS — overshoot beyond it, and does it reach the next cluster out?")
for nm, brk, s_, d, d2 in (("top edge", t.sup >= t.up, t.sup, t.up, t.up2), ("bottom edge", t.sdn >= t.dn, t.sdn, t.dn, t.dn2)):
    g = t[brk]; ov = s_[brk] - d[brk]; nx = (s_[brk] >= d2[brk]).mean()
    pl = np.mean([(s_[brk].values >= (d[brk].values + (d2 - d)[brk].values[rng.permutation(brk.sum())])).mean() for _ in range(200)])
    print(f"   {nm:11s} broken {100 * brk.mean():.0f}% of sessions | overshoot past it: median {ov.median():.2f}%, 75th {ov.quantile(.75):.2f}%, 90th {ov.quantile(.9):.2f}% "
          f"| reached the next cluster out {100 * nx:.0f}% (placebo gap {100 * pl:.0f}%)")
t.to_csv("runs/gate/liq_extent_test.csv", index=False)
