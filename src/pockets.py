"""
POCKETS — do moves TERMINATE at concentrations of resting liquidity?

DK, after three nulls: "you've just not found it yet for some reason."

He is right that the question was not properly put, and the flaw is nameable.

WHAT DOC 60 MEASURED, AND WHY IT COULD NOT HAVE WORKED
    skew = (size below - size above) / total
That is NET IMBALANCE. A book with a large cluster 2% below AND a large cluster
2% above nets to a skew of zero -- while containing two magnets. The contention
is about POCKETS, concentrations, lumps. Averaging the two sides against each
other destroys exactly the object under test. Three tests were run on a measure
that was incapable of detecting the thing.

THE SECOND REFRAME
Doc 60 also asked a FORECASTING question: does the book predict the direction of
the next move? That is not what "moves aim to target liquidity" claims. A move
has to happen first. The claim is about where moves STOP -- that price travels
until it reaches a pocket, takes it, and that is the end of the leg.

So this measures termination, conditional on a move occurring. No direction
forecast anywhere in it.

THE MEASURE
At each bar, the book is read as six bands per side (0.2/1/2/3/4/5%). Density
per band is size divided by the band's width, which matters: the 0.2% band is
one fifth the width of the 1% band, so raw notional flatters the wide ones.
The POCKET is the band with the highest density, found separately above and
below, and only counted when it is genuinely concentrated -- its density at
least 1.5x the mean of its own side. A flat book has no pocket and is excluded,
which is the placebo built into the design.

Then: over the next 24 hours, where does the move's EXTREME land?

    hit      the extreme falls inside the pocket band
    null     the pocket band's share of the travelled range, i.e. exactly what
             you would get if extremes landed anywhere in the range at random

The null is computed per observation from that observation's own geometry, so
there is nothing to argue about: a wide pocket band gets a correspondingly
larger null and earns no credit for being wide.

CONTROL
The same test with the pocket location SHUFFLED across time within each symbol.
Identical band widths, identical nulls, identical move distribution -- only the
pairing between book and future is broken. If the real pairing does not beat the
shuffled one, there is nothing here.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DEPTH = "/home/claude/qlab/data_depth_full"
M1 = "/home/claude/qlab/data_1m"
BANDS = [0.2, 1.0, 2.0, 3.0, 4.0, 5.0]
EDGES = [0.0] + BANDS
RNG = np.random.default_rng(606)
HOR = 288          # 24 hours of 5-minute bars
CONC = 1.5         # a pocket must be this dense relative to its own side


def load(sym):
    p, m = f"{DEPTH}/{sym}.csv", f"{M1}/{sym}.csv"
    if not (os.path.exists(p) and os.path.exists(m)):
        return None
    d = pd.read_csv(p, parse_dates=["ts"]).set_index("ts").sort_index()
    k = pd.read_csv(m); k["dt"] = pd.to_datetime(k.t, unit="ms")
    k = k.set_index("dt").sort_index(); k = k[~k.index.duplicated()]
    px = k.resample("5min").agg(close=("close", "last"), high=("high", "max"),
                                low=("low", "min")).dropna()
    j = d.join(px, how="inner")
    return j if len(j) > 5000 else None


def densities(j, side):
    """Per-band density = notional / band width, as an (n, 6) array."""
    out = np.zeros((len(j), len(BANDS)))
    for bi, b in enumerate(BANDS):
        col = f"d{'-' if side == 'down' else '+'}{b:g}"
        w = EDGES[bi + 1] - EDGES[bi]
        out[:, bi] = np.nan_to_num(j[col].values) / w if col in j.columns else 0.0
    return out


def run():
    rows = []
    for f in sorted(glob.glob(f"{DEPTH}/*.csv")):
        s = os.path.basename(f)[:-4]
        j = load(s)
        if j is None:
            continue
        C, H, L = j.close.values, j.high.values, j.low.values
        n = len(C)
        DD = densities(j, "down"); DU = densities(j, "up")
        for i in range(288, n - HOR - 1, 36):
            if C[i] <= 0:
                continue
            hi = H[i + 1:i + 1 + HOR].max(); lo = L[i + 1:i + 1 + HOR].min()
            up_pct = (hi / C[i] - 1) * 100
            dn_pct = (1 - lo / C[i]) * 100
            for side, D, ext_pct in (("down", DD, dn_pct), ("up", DU, up_pct)):
                d = D[i]
                if d.sum() <= 0:
                    continue
                k = int(np.argmax(d))
                if d[k] < CONC * d.mean():
                    continue                       # no real pocket: excluded
                a, b = EDGES[k], EDGES[k + 1]
                # the move must at least reach the pocket's near edge, and we
                # only score moves that stayed on the chart (<= 5%)
                if ext_pct < a or ext_pct > 5.0:
                    continue
                hit = int(a <= ext_pct <= b)
                null = (b - a) / 5.0               # share of the measurable range
                rows.append(dict(sym=s, ts=j.index[i], side=side, band=k,
                                 hit=hit, null=null, ext=ext_pct))
    return pd.DataFrame(rows)


def score(T, label):
    if len(T) < 200:
        print(f"  {label}: too few"); return
    obs = T.hit.mean(); nl = T.null.mean()
    days = T.ts.dt.floor("1D").values
    uniq = np.unique(days); idx = {d: np.flatnonzero(days == d) for d in uniq}
    h, nn = T.hit.values, T.null.values
    bs = []
    for _ in range(2000):
        pick = RNG.choice(uniq, len(uniq), replace=True)
        m = np.concatenate([idx[d] for d in pick])
        bs.append(h[m].mean() - nn[m].mean())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    sig = "SIGNIFICANT" if lo > 0 else ("negative" if hi < 0 else "not significant")
    print(f"  {label:<34}n={len(T):>6}  hit {obs*100:5.2f}%  null {nl*100:5.2f}%"
          f"  excess {(obs-nl)*100:+5.2f}pp  [{lo*100:+5.2f},{hi*100:+5.2f}]  {sig}")


if __name__ == "__main__":
    print("DO MOVES TERMINATE AT LIQUIDITY POCKETS?")
    print("Pockets = density concentrations, not net imbalance. Termination, not direction.\n")
    T = run()
    if not len(T):
        print("no data"); raise SystemExit
    print(f"  {T.sym.nunique()} symbols, {T.ts.dt.floor('1D').nunique()} days, "
          f"{len(T)} scored moves (flat books excluded)\n")
    print("=" * 104)
    score(T, "ALL")
    for sd in ("down", "up"):
        score(T[T.side == sd], f"  side = {sd}")
    print()
    for k in range(len(BANDS)):
        S = T[T.band == k]
        if len(S) > 200:
            score(S, f"  pocket in band {EDGES[k]:g}-{BANDS[k]:g}%")

    print("\n" + "=" * 104)
    print("  CONTROL — pocket location shuffled in time within each symbol")
    print("=" * 104)
    S = T.copy()
    S["band"] = S.groupby("sym")["band"].transform(
        lambda v: RNG.permutation(v.values))
    S["null"] = S.band.map(lambda k: (EDGES[k + 1] - EDGES[k]) / 5.0)
    S["hit"] = [int(EDGES[k] <= e <= EDGES[k + 1])
                for k, e in zip(S.band.values, S.ext.values)]
    score(S, "shuffled")
