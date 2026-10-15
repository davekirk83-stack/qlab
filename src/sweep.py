"""
THE SWEEP TEST — the right measurement for DK's contention.

DK: "Most market moves in bitcoin aim to target liquidity (resting orders /
liquidations of high leverage positions or stop losses)."

WHY THE DRIFT TEST WAS THE WRONG ONE
magnet.py asked whether a lopsided book predicts the DIRECTION of the next
24 hours. Over 15 symbols and a year the answer is no: IC -0.025, CI
straddling zero, first half flat. The 45-day version in doc 59 was a
small-sample artefact and is hereby withdrawn.

But that is not what the contention says. It does not say price ENDS UP where
the liquidity is. It says price GOES AND GETS IT -- touches it, takes it, and
is often somewhere else by the time the window closes. A drift correlation
cannot see that; it nets the visit against the return trip and reads zero.

The measurement that can see it is FIRST PASSAGE between EQUIDISTANT barriers.

    from price P, does the market touch P*(1-b) before P*(1+b)?

Both barriers are the same distance away, so the null is exactly 50% -- no
random-walk geometry to model, no distance correction, no null to argue
about. This is the cleanest null in the whole programme.

Then: does the book predict which one gets hit?

    skew > 0   more resting notional BELOW
    MAGNET     predicts the DOWN barrier is touched first
    SUPPORT    predicts that size absorbs, so the UP barrier goes first

The two hypotheses are opposite signs on one number against a 50% null.

ALSO MEASURED
  by horizon       how long the market is given to make the trip
  by band          0.2% (near book) through 5% (the far clusters)
  conditioned      skew extremes only -- the contention is about LOPSIDED
                   books, and a balanced book should predict nothing, which
                   doubles as a placebo
  per symbol       sign consistency across 15 instruments
  bootstrap        whole days resampled, 2000 draws
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DEPTH = "/home/claude/qlab/data_depth_full"
M1 = "/home/claude/qlab/data_1m"
RNG = np.random.default_rng(777)
STEP = 72          # a fresh observation every 6 hours
MAXB = 576         # 48 hours to complete the trip


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


def skew_at(j, lim):
    lo = sum(j[c].values for c in j.columns
             if c.startswith("d-") and float(c[2:]) <= lim + 1e-9)
    hi = sum(j[c].values for c in j.columns
             if c.startswith("d+") and float(c[2:]) <= lim + 1e-9)
    t = lo + hi
    return np.where(t > 0, (lo - hi) / t, np.nan)


def race(H, L, i, up, dn, maxb):
    """Which equidistant barrier is touched first? +1 up, -1 down, 0 neither."""
    n = len(H)
    for j in range(i + 1, min(i + 1 + maxb, n)):
        hu, hd = H[j] >= up, L[j] <= dn
        if hu and hd:
            return 0            # same bar, unresolvable -- discard
        if hu:
            return 1
        if hd:
            return -1
    return 0


def run(band, maxb=MAXB):
    rows = []
    for f in sorted(glob.glob(f"{DEPTH}/*.csv")):
        s = os.path.basename(f)[:-4]
        j = load(s)
        if j is None:
            continue
        C, H, L = j.close.values, j.high.values, j.low.values
        sk = skew_at(j, band)
        n = len(C)
        for i in range(288, n - maxb - 1, STEP):
            if not np.isfinite(sk[i]) or C[i] <= 0:
                continue
            b = band / 100.0
            r = race(H, L, i, C[i] * (1 + b), C[i] * (1 - b), maxb)
            if r == 0:
                continue
            rows.append(dict(sym=s, ts=j.index[i], skew=sk[i], down=int(r < 0)))
    return pd.DataFrame(rows)


def boot(T, draws=2000):
    days = T.ts.dt.floor("1D").values
    uniq = np.unique(days)
    idx = {d: np.flatnonzero(days == d) for d in uniq}
    y = T.down.values
    out = []
    for _ in range(draws):
        pick = RNG.choice(uniq, len(uniq), replace=True)
        m = np.concatenate([idx[d] for d in pick])
        out.append(y[m].mean())
    return np.percentile(out, [2.5, 97.5])


if __name__ == "__main__":
    print("THE SWEEP TEST — does price go and TAKE the resting liquidity?")
    print("Equidistant barriers, so the null is exactly 50%. 48h to complete.\n")
    for band in (0.2, 1.0, 2.0):
        T = run(band)
        if len(T) < 500:
            print(f"  {band}%: too few\n"); continue
        print("=" * 88)
        print(f"  BARRIERS AT +/-{band}%     n={len(T)} races, "
              f"{T.sym.nunique()} symbols, {T.ts.dt.floor('1D').nunique()} days")
        print("=" * 88)
        base = T.down.mean()
        print(f"  unconditional: down-barrier first {base*100:5.2f}%  "
              f"(null 50.00%)\n")
        # split by how lopsided the book is, within each symbol's own history
        T["q"] = T.groupby("sym")["skew"].transform(
            lambda v: pd.qcut(v.rank(method="first"), 5, labels=False))
        print(f"  {'book skew quintile':<34}{'n':>7}{'down first':>12}"
              f"{'95% CI':>20}")
        for q, lab in enumerate(["1  heaviest ABOVE", "2", "3  balanced", "4",
                                 "5  heaviest BELOW"]):
            S = T[T.q == q]
            if len(S) < 200:
                continue
            lo, hi = boot(S)
            star = "  <--" if (lo > 0.5 or hi < 0.5) else ""
            print(f"    {lab:<32}{len(S):>7}{S.down.mean()*100:>11.2f}%"
                  f"   [{lo*100:5.2f},{hi*100:5.2f}]{star}")
        top = T[T.q == 4].down.mean(); bot = T[T.q == 0].down.mean()
        print(f"\n  SPREAD (heaviest below - heaviest above): "
              f"{(top-bot)*100:+.2f}pp")
        print("  MAGNET predicts positive, SUPPORT predicts negative.")
        v = []
        for s, g in T.groupby("sym"):
            a, b = g[g.q == 4], g[g.q == 0]
            if len(a) > 50 and len(b) > 50:
                v.append(a.down.mean() - b.down.mean())
        if v:
            print(f"  per-symbol: {sum(1 for x in v if x>0)}/{len(v)} positive"
                  f"   median {np.median(v)*100:+.2f}pp")
        print()
