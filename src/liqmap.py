"""
LIQUIDATION CLUSTERS — measuring the liquidity DK actually named.

DK: "most market moves in bitcoin aim to target liquidity (resting orders /
LIQUIDATIONS OF HIGH LEVERAGE POSITIONS or STOP LOSSES)."

WHY THE FIRST THREE TESTS MISSED THE POINT
magnet.py, sweep.py and down_first.py all measured ORDER BOOK DEPTH, and all
three came back empty at full sample. But book depth is the wrong object.
It is the liquidity that is VISIBLE and VOLUNTARY -- someone chose to rest it
there and can pull it in a millisecond, and in practice does, exactly when it
would have mattered. DK's contention names two things that are neither:

    LIQUIDATIONS  not resting orders at all. They are FORCED market orders
                  that do not exist until price arrives, cannot be cancelled,
                  and whose location is DETERMINISTIC given entry price and
                  leverage. They are invisible in the book and visible in
                  open interest.
    STOP LOSSES   also not in the book -- held at the venue or in someone's
                  head, triggered into market orders at structure.

The thing that makes these a magnet is precisely what book depth lacks: they
cannot be withdrawn, and taking them pays, because each one is a forced
market order in your favour. A resting limit is an obstacle. A liquidation
cluster is a prize.

RECONSTRUCTING THE LIQUIDATION BOOK
We cannot see positions, but we can derive them. For each 5-minute bar:

  dOI > 0            new contracts opened, at roughly this bar's price
  direction          split by whether price rose or fell as OI grew --
                     OI up with price up is long-dominated accumulation,
                     OI up with price down is short-dominated. This is the
                     quadrant decomposition already used in the programme.
  liquidation price  a long opened at P with leverage L is force-closed near
                     P*(1 - 1/L); a short near P*(1 + 1/L). Tiers 10/25/50/100x
                     are accumulated with the weights retail actually uses.
  removal            when price trades through a level, those positions are
                     gone. The book is depleted on contact -- without this the
                     map is a cumulative fiction.

That yields, at every bar, an estimate of forced-order notional sitting at
each price. Then the same clean test as before:

    LIQ SKEW = (long-liq notional within b% BELOW) - (short-liq within b% ABOVE)
               ------------------------------------------------------------
                                    total within b%

and the equidistant-barrier race, null exactly 50%. Identical machinery to
sweep.py, so the two results are directly comparable and the only thing that
changed is WHICH liquidity is measured. If the contention is right, this is
where it shows up and the book-depth null was measuring the wrong object.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
M1 = "/home/claude/qlab/data_1m"
RNG = np.random.default_rng(424242)
TIERS = [(10, 0.20), (25, 0.35), (50, 0.30), (100, 0.15)]   # leverage, weight
STEP, MAXB = 72, 576
DECAY = 1 - 1 / (288 * 7)      # positions age out over about a week


def load(sym):
    p, m = f"{OI}/{sym}.csv", f"{M1}/{sym}.csv"
    if not (os.path.exists(p) and os.path.exists(m)):
        return None
    d = pd.read_csv(p, parse_dates=["create_time"]).set_index("create_time").sort_index()
    d = d[~d.index.duplicated()]
    k = pd.read_csv(m); k["dt"] = pd.to_datetime(k.t, unit="ms")
    k = k.set_index("dt").sort_index(); k = k[~k.index.duplicated()]
    px = k.resample("5min").agg(close=("close", "last"), high=("high", "max"),
                                low=("low", "min")).dropna()
    j = px.join(d[["sum_open_interest", "sum_taker_long_short_vol_ratio"]], how="inner")
    return j.dropna() if len(j) > 5000 else None


def liq_book(j, nbins=400):
    """Returns (grid, longs, shorts) where longs[i] is the array of forced
    long-liquidation notional by price bucket, as it stood at bar i."""
    C, H, L = j.close.values, j.high.values, j.low.values
    oi = j.sum_open_interest.values
    tk = j.sum_taker_long_short_vol_ratio.values
    n = len(C)
    lo, hi = np.nanmin(L) * 0.98, np.nanmax(H) * 1.02
    grid = np.exp(np.linspace(np.log(lo), np.log(hi), nbins))
    gl = np.zeros(nbins); gs = np.zeros(nbins)
    out_l = np.zeros((n, nbins), dtype=np.float32)
    out_s = np.zeros((n, nbins), dtype=np.float32)
    doi = np.diff(oi, prepend=oi[0])
    dpx = np.diff(C, prepend=C[0])
    for i in range(1, n):
        gl *= DECAY; gs *= DECAY
        add = doi[i]
        if add > 0 and C[i] > 0:
            # long share of the new OI: price direction, tilted by taker flow
            t = tk[i] if np.isfinite(tk[i]) else 1.0
            flow = t / (1 + t)
            dirn = 0.5 + 0.5 * np.sign(dpx[i])
            lshare = np.clip(0.5 * flow + 0.5 * dirn, 0.05, 0.95)
            notional = add * C[i]
            for lev, w in TIERS:
                pl = C[i] * (1 - 1 / lev)
                ps = C[i] * (1 + 1 / lev)
                bl = np.searchsorted(grid, pl)
                bs = np.searchsorted(grid, ps)
                if 0 <= bl < nbins:
                    gl[bl] += notional * w * lshare
                if 0 <= bs < nbins:
                    gs[bs] += notional * w * (1 - lshare)
        # DEPLETION: anything the bar traded through is liquidated and gone
        a = np.searchsorted(grid, L[i]); b = np.searchsorted(grid, H[i])
        if b > a:
            gl[a:b] = 0.0; gs[a:b] = 0.0
        out_l[i] = gl; out_s[i] = gs
    return grid, out_l, out_s


def run(band):
    b = band / 100.0
    rows = []
    for f in sorted(glob.glob(f"{OI}/*.csv")):
        s = os.path.basename(f)[:-4]
        j = load(s)
        if j is None:
            continue
        grid, GL, GS = liq_book(j)
        C, H, L = j.close.values, j.high.values, j.low.values
        n = len(C)
        for i in range(2016, n - MAXB - 1, STEP):
            if C[i] <= 0:
                continue
            dn_lo = np.searchsorted(grid, C[i] * (1 - b))
            up_hi = np.searchsorted(grid, C[i] * (1 + b))
            cur = np.searchsorted(grid, C[i])
            below = GL[i, dn_lo:cur].sum()       # longs liquidate below
            above = GS[i, cur:up_hi].sum()       # shorts liquidate above
            tot = below + above
            if tot <= 0:
                continue
            up, dn = C[i] * (1 + b), C[i] * (1 - b)
            out = 0
            for k in range(i + 1, i + 1 + MAXB):
                hu, hd = H[k] >= up, L[k] <= dn
                if hu and hd:
                    out = 0; break
                if hu:
                    out = 1; break
                if hd:
                    out = -1; break
            if out == 0:
                continue
            rows.append(dict(sym=s, ts=j.index[i], lskew=(below - above) / tot,
                             down=int(out < 0)))
    return pd.DataFrame(rows)


def boot(y, days, draws=2000):
    uniq = np.unique(days); idx = {d: np.flatnonzero(days == d) for d in uniq}
    out = []
    for _ in range(draws):
        pick = RNG.choice(uniq, len(uniq), replace=True)
        out.append(y[np.concatenate([idx[d] for d in pick])].mean())
    return np.percentile(out, [2.5, 97.5])


if __name__ == "__main__":
    print("LIQUIDATION CLUSTERS AS A MAGNET")
    print("Forced orders, not resting ones. Equidistant barriers, null = 50%.\n")
    for band in (1.0, 2.0, 3.0):
        T = run(band)
        if len(T) < 500:
            print(f"  {band}%: too few\n"); continue
        print("=" * 86)
        print(f"  BARRIERS +/-{band}%   n={len(T)}  {T.sym.nunique()} symbols  "
              f"{T.ts.dt.floor('1D').nunique()} days")
        print("=" * 86)
        T["q"] = T.groupby("sym")["lskew"].transform(
            lambda v: pd.qcut(v.rank(method="first"), 5, labels=False))
        print(f"  {'liquidation skew quintile':<36}{'n':>7}{'down first':>12}{'95% CI':>20}")
        for q, lab in enumerate(["1  shorts stacked ABOVE", "2", "3  balanced", "4",
                                 "5  longs stacked BELOW"]):
            S = T[T.q == q]
            if len(S) < 200:
                continue
            lo, hi = boot(S.down.values, S.ts.dt.floor("1D").values)
            star = "  <--" if (lo > 0.5 or hi < 0.5) else ""
            print(f"    {lab:<34}{len(S):>7}{S.down.mean()*100:>11.2f}%"
                  f"   [{lo*100:5.2f},{hi*100:5.2f}]{star}")
        top, bot = T[T.q == 4].down.mean(), T[T.q == 0].down.mean()
        v = []
        for s, g in T.groupby("sym"):
            a, c = g[g.q == 4], g[g.q == 0]
            if len(a) > 40 and len(c) > 40:
                v.append(a.down.mean() - c.down.mean())
        print(f"\n  SPREAD (longs-below minus shorts-above): {(top-bot)*100:+.2f}pp"
              f"   MAGNET predicts positive")
        if v:
            print(f"  per-symbol: {sum(1 for x in v if x>0)}/{len(v)} positive"
                  f"   median {np.median(v)*100:+.2f}pp")
        print()
