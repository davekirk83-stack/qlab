"""
CONDITIONING THE REGISTERED BOOKS ON THE ELEMENT LIBRARY.

The library (doc 57, 46 elements) measured which STATE variables predict
forward returns. Not one registered book uses any of them. Six books, all raw
price rules, with the measured state information sitting unused beside them.

Doc 66 is the argument for fixing that: conditioning the Keltner trade on
regime turned -0.094%/trade into +0.392%. The elements are state measures, and
state is exactly what should condition a trade.

THE METHOD
Take the cascade v3 entries — the one book with a positive base to condition —
and compute every element at the entry bar. Then split the trades by each
element's quantile (ranked WITHIN symbol, so a filter cannot work by selecting
instruments) and look for monotone structure.

WHAT COUNTS AS A FINDING, AND WHAT DOESN'T
A single good quintile is noise; there are 46 elements x 5 buckets here and
some will look wonderful. So the test is MONOTONICITY: the Spearman correlation
between quantile and mean return, which uses all five buckets and cannot be
rescued by one lucky cell. Reported alongside the top-minus-bottom spread and
how many symbols agree.

Nothing here is registered. A filter that survives this becomes a candidate,
and a candidate still has to clear the harness out of sample.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
from scipy import stats
import elements as EL

M1 = "/home/claude/qlab/data_1m"
DROP, WIN = 0.03, 5
LIFT, HOLD, DEPTHB, TP, MAXH = 0.008, 10, 0.004, 0.015, 60
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000


def find_base(C, L, i, n, mw=60):
    lo = L[i]; k = i
    while k < min(i + mw, n - 1):
        if L[k] < lo: lo = L[k]
        if C[k] >= lo * (1 + LIFT): break
        k += 1
    if k >= min(i + mw, n - 1) or C[k] < lo * (1 + LIFT): return None
    j = k; h = 0
    while j < min(k + mw, n - 1):
        if L[j] < lo: return None
        h += 1
        if h >= HOLD: return j, lo
        j += 1
    return None


def run():
    rows = []
    for f in sorted(glob.glob(f"{M1}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        if len(d) < 50000: continue
        d["dt"] = pd.to_datetime(d.t, unit="ms")
        d = d.set_index("dt").sort_index()
        # elements on HOURLY bars: the state the trade sits inside, not the
        # minute noise it triggers on. Doc 58: IC is timeframe-specific.
        hr = d.resample("1h").agg(open=("open", "first"), high=("high", "max"),
                                  low=("low", "min"), close=("close", "last"),
                                  volume=("volume", "sum")).dropna()
        if len(hr) < 500: continue
        FH = EL.build(hr)
        hidx = hr.index
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); i = WIN
        while i < n - 2 * MAXH:
            if C[i] / C[i - WIN] - 1 > -DROP: i += 1; continue
            b = find_base(C, L, i, n)
            if b is None: i += WIN; continue
            j, lo = b
            bid = max(C[j] * (1 - DEPTHB), lo * 1.0002)
            fill = None
            for q in range(j + 1, min(j + 1 + MAXH, n)):
                if L[q] < lo: break
                if L[q] <= bid: fill = q; break
            if fill is None: i = j + 1; continue
            px = bid * (1 + MAKER); stop = lo * (1 - 0.0005); tgt = px * (1 + TP)
            if stop >= px: i = j + 1; continue
            ret = None
            for q in range(fill + 1, min(fill + 1 + MAXH, n)):
                if L[q] <= stop: ret = (stop*(1-SLIP-TAKER))/px - 1; break
                if H[q] >= tgt: ret = (tgt*(1-MAKER))/px - 1; break
            if ret is None:
                q = min(fill + MAXH, n - 1); ret = (C[q]*(1-MAKER))/px - 1
            k = hidx.searchsorted(d.index[fill]) - 1
            if 200 <= k < len(hidx):
                rec = {"sym": s, "ret": ret}
                for key, arr in FH.items():
                    v = arr[k]
                    if np.isfinite(v): rec[key] = v
                rows.append(rec)
            i = fill + MAXH
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("CONDITIONING CASCADE v3 ON THE ELEMENT LIBRARY")
    print("Elements measured on HOURLY state at the entry bar.\n")
    T = run()
    base = T.ret.mean()
    print(f"  {len(T)} trades, {T.sym.nunique()} symbols, "
          f"unconditional {base*100:+.3f}%\n")
    feats = [c for c in T.columns if c not in ("sym", "ret")]
    out = []
    for c in feats:
        S = T[["sym", "ret", c]].dropna()
        if len(S) < 150: continue
        S = S.copy()
        # z-score WITHIN symbol (so a filter cannot work by picking instruments)
        # then quintile the pooled z-scores. Quintiling inside each symbol gave
        # 2-3 trades per bucket on 242 trades across 18 symbols, which is noise.
        try:
            z = S.groupby("sym")[c].transform(
                lambda v: (v - v.mean()) / (v.std(ddof=0) if v.std(ddof=0) > 0 else np.nan))
            S["q"] = pd.qcut(z.rank(method="first"), 5, labels=False)
        except Exception:
            continue
        S = S.dropna(subset=["q"])
        g = S.groupby("q").ret.mean()
        if len(g) < 5: continue
        mono = stats.spearmanr(g.index.values, g.values).correlation
        spread = g.iloc[-1] - g.iloc[0]
        top = S[S.q == 4]; bot = S[S.q == 0]
        if len(top) < 40 or len(bot) < 40: continue
        se = np.sqrt(top.ret.var(ddof=1)/len(top) + bot.ret.var(ddof=1)/len(bot))
        agree = 0; tot = 0
        for sy, gg in S.groupby("sym"):
            a = gg[gg.q == 4].ret; b = gg[gg.q == 0].ret
            if len(a) >= 3 and len(b) >= 3:
                tot += 1; agree += int((a.mean() - b.mean()) * np.sign(spread) > 0)
        out.append(dict(el=c, mono=mono, spread=spread, t=spread/se if se > 0 else 0,
                        top=g.iloc[-1], bot=g.iloc[0], agree=agree, tot=tot,
                        fam=EL.family(c)))
    R = pd.DataFrame(out)
    if not len(R):
        print("  no element produced usable buckets"); raise SystemExit
    R = R[(R.mono.abs() >= 0.9) & (R.t.abs() >= 2.0)]
    R = R.reindex(R.t.abs().sort_values(ascending=False).index)
    print(f"  Elements with MONOTONE structure (|rho|>=0.9) and |t|>=2.0:\n")
    if not len(R):
        print("  none — no element conditions this book")
    else:
        print(f"  {'element':<20}{'family':<12}{'bottom':>9}{'top':>9}"
              f"{'spread':>9}{'t':>7}{'mono':>7}{'syms':>8}")
        for _, r in R.iterrows():
            print(f"  {r.el:<20}{r.fam:<12}{r.bot*100:>+8.3f}%{r.top*100:>+8.3f}%"
                  f"{r.spread*100:>+8.3f}%{r.t:>+7.2f}{r.mono:>+7.2f}"
                  f"{r.agree:>5}/{r.tot}")
        print(f"\n  {len(R)} of {len(out)} elements tested. At 5% by chance "
              f"you would expect ~{len(out)*0.05:.0f} on the t-test alone,")
        print("  but monotonicity across five buckets is a much harder filter.")
