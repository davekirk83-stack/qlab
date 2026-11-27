"""DK 27 Nov 17:27: "Why would auclair's thing fail on the real order flow data? we know he uses it, and that it works".
Audit of the 23 Nov true-delta divergence test (doc 256) found four method flaws:
  1. divergence trades were run through the BREAKOUT exit stack (breakeven +15, 1-ATR trail). His divergence trades (his /CL algo, the
     one he describes) SCALE IN against the entry (-12 / -17 pips) before a hard stop (-26) with ONE target (+32) for all lots.
  2. his threshold is literal: "divergence min net delta 420" contracts on 5-min bid/ask bars. We replaced it with a percentile of a
     6-bar sum. On true CME data the literal number can be used as he uses it.
  3. CME futures delta was laid on IG/Dukascopy CFD price bars. Here prices AND delta come from the same Databento futures bars.
  4. the breakout path also turned negative on true delta (-2.7 vs +6.5 on tick-rule delta), a sign the whole true-delta run was
     mis-calibrated rather than a verdict on divergence.
Redo: NQ futures 5-min, Databento trades Apr-Nov 2026 (true aggressor delta). Divergence short: bar makes a new N-bar high, its net
delta over the push (last k bars) is >= 420 contracts weaker than at the previous N-bar high, and that previous push had |net delta|
>= 420; mirror for longs. Entry at the next bar open, scale-in his way (1/3 now, 1/3 at +1.2 x unit, 1/3 at +1.7 x unit against us),
hard stop at 2.6 x unit, one target 3.2 x unit for all lots (his /CL numbers in units of 10 pips -> unit = 1 ATR of 5-min NQ).
Costs 0.5 pt per lot round trip (his futures). Variants: lookback N, push length k, regime (none / only when no 15-min trend)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
t = pd.read_csv("data_nq_cache/nq_true_delta_5m.csv.gz", index_col=0, parse_dates=True)
t["delta"] = t.buy.astype("int64") - t.sell.astype("int64"); t = t[~t.index.duplicated()].sort_index()
O, H, L, C, D = t.open.values, t.high.values, t.low.values, t.close.values, t.delta.values.astype(float); n = len(C)
tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)), np.abs(L - np.roll(C, 1)))); ATR = pd.Series(tr).rolling(20).mean().shift(1).values
# 15-min regression trend (his regime idea, simple version): |t-stat| of 16 x 15-min closes > 2
c15 = t.close.resample("15min").last().dropna(); x = np.arange(16); xm = x - x.mean()
def tst(v):
    y = v - v.mean(); b = (xm * y).sum() / (xm ** 2).sum(); r = y - b * xm; s = np.sqrt((r ** 2).sum() / 14 / (xm ** 2).sum()); return b / s if s > 0 else 0
tt = c15.rolling(16).apply(tst, raw=True).shift(1); TREND = (tt.abs() > 2).reindex(t.index, method="ffill").fillna(False).values
def sim(N=20, k=3, thr=420, regime="any", scale=(1.2, 1.7), stop=2.6, tgt=3.2, cost=0.5, single=False):
    nd = pd.Series(D).rolling(k).sum().values
    hh = pd.Series(H).rolling(N).max().shift(1).values; ll = pd.Series(L).rolling(N).min().shift(1).values
    ih = pd.Series(H).rolling(N).apply(np.argmax, raw=True).shift(1).values; il = pd.Series(L).rolling(N).apply(np.argmin, raw=True).shift(1).values
    out = []; i = N + k + 25
    while i < n - 2:
        s = 0
        if H[i] > hh[i] and np.isfinite(ih[i]):
            jprev = int(i - N + ih[i]);
            if abs(nd[jprev]) >= thr and nd[i] <= nd[jprev] - thr: s = -1
        if s == 0 and L[i] < ll[i] and np.isfinite(il[i]):
            jprev = int(i - N + il[i])
            if abs(nd[jprev]) >= thr and nd[i] >= nd[jprev] + thr: s = 1
        if s == 0 or not np.isfinite(ATR[i]) or (regime == "no trend" and TREND[i]): i += 1; continue
        u = ATR[i]; e0 = O[i + 1]; fills = [e0] if not single else [e0]
        adds = [] if single else [e0 - s * scale[0] * u, e0 - s * scale[1] * u]
        lots = 1 if single else 1
        st = e0 - s * stop * u; x = None; q = i + 1
        for q in range(i + 1, min(n, i + 1 + 72)):
            for a in list(adds):
                if (s == 1 and L[q] <= a) or (s == -1 and H[q] >= a): fills.append(a); adds.remove(a)
            avg = np.mean(fills); tp = (e0 if not single else e0) + s * tgt * u
            if (s == 1 and L[q] <= st) or (s == -1 and H[q] >= st): x = st; break
            if (s == 1 and H[q] >= tp) or (s == -1 and L[q] <= tp): x = tp; break
        if x is None: x = C[q]
        pts = sum(s * (x - f) - cost for f in fills) / (1 if single else 3)       # per full position of 3 lots, in points per lot
        out.append((t.index[i], pts, len(fills), s)); i = q + 1
    r = pd.DataFrame(out, columns=["t", "pts", "fills", "s"])
    if len(r) < 10: return None
    h = len(r) // 2; mo = r.groupby(r.t.dt.to_period("M")).pts.sum()
    return dict(n=len(r), win=round((r.pts > 0).mean(), 2), pts=round(r.pts.mean(), 2), h1=round(r.pts[:h].mean(), 2), h2=round(r.pts[h:].mean(), 2),
                months_pos=f"{(mo > 0).sum()}/{len(mo)}", longs=round(r[r.s == 1].pts.mean(), 2), shorts=round(r[r.s == -1].pts.mean(), 2))
if __name__ == "__main__":
    print("bars", n, t.index[0], t.index[-1], "| median |bar delta|", np.median(np.abs(D)), "| 90th pct |3-bar net delta|", np.nanpercentile(np.abs(pd.Series(D).rolling(3).sum()), 90))
    rows = []
    for N in (20, 40):
        for k in (1, 3, 6):
            for regime in ("any", "no trend"):
                for lab, kw in (("his scale-in exits", {}), ("single entry, same stop/target", {"single": True})):
                    r = sim(N=N, k=k, regime=regime, **kw)
                    if r: rows.append(dict(N=N, k=k, regime=regime, exits=lab, **r)); print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/ad_div_redo.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
    print("\nvariants with both halves > 0:", int(((R.h1 > 0) & (R.h2 > 0)).sum()), "of", len(R))
