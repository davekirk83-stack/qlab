"""
THE DOWNSIDE IS REACHED FIRST — and the obvious explanation has to go first.

Fell out of sweep.py. Against an exactly-50% null (equidistant barriers), the
down barrier is touched first more often than the up barrier, and the margin
WIDENS with distance:

    +/-0.2%   51.97%      +/-1%   52.54%      +/-2%   53.23%

DK, on TWAP: "you get the stairs up and then elevator down after a while."
This is that, measured.

THE OBVIOUS EXPLANATION, WHICH MUST BE KILLED FIRST
If these fifteen coins simply fell over the sample year, the down barrier gets
touched first for a trivial reason and there is nothing here. So the drift
control is not optional, and it is done three ways:

 1. DRIFT-MATCHED NULL   for each race, the actual realised drift of that
                         symbol over that window is used to compute the
                         random-walk probability of down-first, and the
                         observed rate is scored against THAT, not 50%.
 2. DEMEANED BARRIERS    barriers placed around a drift-adjusted path, so a
                         trending instrument has symmetric targets.
 3. SPLIT BY REGIME      up-trending windows and down-trending windows
                         separately. If the asymmetry survives in UP markets
                         it is not drift.

If it survives all three it is a real path asymmetry: price reaches down
before up even when it ends up higher. That is a statement about HOW markets
travel, and it has a direct use -- it is the quantitative case for the
registered cascade book, and it says a long entry should expect to be dipped
on before it works.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DEPTH = "/home/claude/qlab/data_depth_full"
M1 = "/home/claude/qlab/data_1m"
RNG = np.random.default_rng(31337)
STEP, MAXB = 72, 576


def load(sym):
    m = f"{M1}/{sym}.csv"
    if not os.path.exists(m):
        return None
    k = pd.read_csv(m); k["dt"] = pd.to_datetime(k.t, unit="ms")
    k = k.set_index("dt").sort_index(); k = k[~k.index.duplicated()]
    px = k.resample("5min").agg(close=("close", "last"), high=("high", "max"),
                                low=("low", "min")).dropna()
    return px if len(px) > 5000 else None


def races(band, maxb=MAXB):
    b = band / 100.0
    rows = []
    for f in sorted(glob.glob(f"{DEPTH}/*.csv")):
        s = os.path.basename(f)[:-4]
        px = load(s)
        if px is None:
            continue
        C, H, L = px.close.values, px.high.values, px.low.values
        n = len(C)
        for i in range(288, n - maxb - 1, STEP):
            if C[i] <= 0:
                continue
            up, dn = C[i] * (1 + b), C[i] * (1 - b)
            out = 0
            for j in range(i + 1, i + 1 + maxb):
                hu, hd = H[j] >= up, L[j] <= dn
                if hu and hd:
                    out = 0; break
                if hu:
                    out = 1; break
                if hd:
                    out = -1; break
            if out == 0:
                continue
            # realised drift over the window actually used
            end = min(i + maxb, n - 1)
            mu = (C[end] / C[i] - 1)
            rows.append(dict(sym=s, ts=px.index[i], down=int(out < 0), drift=mu))
    return pd.DataFrame(rows)


def drift_null(mu, b, sigma):
    """P(down first) for a drifting Brownian motion with symmetric barriers.
    Exact for the symmetric case: p_up = (1-exp(-2*mu*b/s^2))/(1-exp(-4*mu*b/s^2))
    taken in the log-barrier limit; guarded for mu -> 0."""
    if sigma <= 0:
        return 0.5
    a = 2 * mu * b / sigma ** 2
    if abs(a) < 1e-8:
        return 0.5
    with np.errstate(over="ignore"):
        p_up = (1 - np.exp(-a)) / (1 - np.exp(-2 * a))
    if not np.isfinite(p_up):
        p_up = 1.0 if a > 0 else 0.0
    return float(1 - min(max(p_up, 0.0), 1.0))


def boot(y, days, draws=2000):
    uniq = np.unique(days)
    idx = {d: np.flatnonzero(days == d) for d in uniq}
    out = []
    for _ in range(draws):
        pick = RNG.choice(uniq, len(uniq), replace=True)
        m = np.concatenate([idx[d] for d in pick])
        out.append(y[m].mean())
    return np.percentile(out, [2.5, 97.5])


if __name__ == "__main__":
    print("DOWN-FIRST ASYMMETRY — is it real, or is it just that crypto fell?\n")
    print(f"  {'band':>7}{'n':>8}{'down 1st':>10}{'drift null':>12}"
          f"{'EXCESS':>9}{'95% CI (obs)':>20}{'syms':>7}")
    store = {}
    for band in (0.2, 0.5, 1.0, 2.0, 3.0):
        T = races(band)
        if len(T) < 500:
            continue
        store[band] = T
        sig = T.groupby("sym").drift.transform("std").values
        nulls = np.array([drift_null(m, band / 100.0, s)
                          for m, s in zip(T.drift.values, sig)])
        lo, hi = boot(T.down.values, T.ts.dt.floor("1D").values)
        obs, nl = T.down.mean(), np.nanmean(nulls)
        pos = sum(1 for _, g in T.groupby("sym") if g.down.mean() > 0.5)
        print(f"  {str(band)+'%':>7}{len(T):>8}{obs*100:>9.2f}%{nl*100:>11.2f}%"
              f"{(obs-nl)*100:>+8.2f}pp   [{lo*100:5.2f},{hi*100:5.2f}]"
              f"{pos:>5}/{T.sym.nunique()}")

    print("\n" + "=" * 84)
    print("  CONTROL 3 — split by what the window actually did")
    print("=" * 84)
    for band in (1.0, 2.0):
        T = store.get(band)
        if T is None:
            continue
        print(f"\n  barriers +/-{band}%")
        for lab, S in (("window ended UP   ", T[T.drift > 0]),
                       ("window ended DOWN ", T[T.drift <= 0])):
            if len(S) < 200:
                continue
            lo, hi = boot(S.down.values, S.ts.dt.floor("1D").values)
            v = "asymmetry survives" if lo > 0.5 else ""
            print(f"    {lab} n={len(S):6d}  down first {S.down.mean()*100:5.2f}%"
                  f"   [{lo*100:5.2f},{hi*100:5.2f}]   {v}")
