"""
THE SYSTEM, RUN ON ELEVEN YEARS INSTEAD OF THIRTEEN MONTHS.

DK: "tell me about our trading system and how well or badly it works on all
     that data."

Everything this programme has produced was measured on a 13-month panel
containing exactly ONE regime change. Four separate constructions all flipped
sign across that one transition (findings 89, 93, 94). The daily history just
ingested - 300 products, 78 with four years or more, BTC to 2015 - is the
first sample with enough transitions to tell a signal from a regime.

WHAT IS TESTED. The one mechanism that has survived everything: the Keltner
lower-band touch in a range regime, small target, wide stop (finding 88 found
the geometry inverted from what we had assumed - 0.5 ATR target against a
3 ATR stop, not the mid). Run on daily bars across the whole universe.

HOW IT IS JUDGED, and this is the part that matters. Not one number. The book
is run SEPARATELY IN EVERY CALENDAR YEAR, so the question becomes "in how many
distinct markets did this work" rather than "what did it average". A book that
makes money in eight years out of eleven is a book. A book whose whole result
comes from 2020-21 is a bull market with extra steps.

Each year also carries its same-regime time-matched control, so a year that
merely rode the market is visible as one.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

MAKER, TAKER, SLIP = 2/10000, 5/10000, 10/10000
RNG = np.random.default_rng(2015)
T_ATR, S_ATR, KBAND, EFF, HOLD = 0.5, 3.0, 2.0, 0.30, 16
MINBARS = 500


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net / np.where(gross > 0, gross, np.nan)


def play(C, H, L, i, stop, tgt, maxh):
    n = len(C); e = C[i]*(1+MAKER)
    for q in range(i+1, min(i+1+maxh, n)):
        if L[q] <= stop: return (stop*(1-SLIP-TAKER))/e-1
        if H[q] >= tgt:  return (tgt*(1-MAKER))/e-1
    q = min(i+maxh, n-1)
    return (C[q]*(1-MAKER))/e-1


def load():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        d = pd.read_csv(p)
        if len(d) < MINBARS: continue
        d.index = pd.to_datetime(d.t, unit="ms")
        out[os.path.basename(p)[:-4]] = d[["open", "high", "low", "close", "volume"]]
    return out


def trades(data):
    rows = []
    for s, d in data.items():
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); a = atr_np(H, L, C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - KBAND*a
        ok = efficiency(C) < EFF
        trig = (C <= lower) & (np.roll(C, 1) > np.roll(lower, 1)) & ok
        elig = np.flatnonzero(ok & np.isfinite(a) & (np.arange(n) > 120))
        elig = elig[(elig > 120) & (elig < n-HOLD-2)]
        last = -10**9
        for i in np.flatnonzero(trig):
            if i < 120 or i > n-HOLD-2 or i-last < HOLD: continue
            last = i
            r = play(C, H, L, i, C[i]-S_ATR*a[i], C[i]+T_ATR*a[i], HOLD)
            c = np.nan
            if len(elig):
                q = int(RNG.choice(elig))
                c = play(C, H, L, q, C[q]-S_ATR*a[q], C[q]+T_ATR*a[q], HOLD)
            rows.append((s, d.index[i], r, c))
    return pd.DataFrame(rows, columns=["sym", "ts", "ret", "ctrl"])


if __name__ == "__main__":
    data = load()
    span = pd.Series({s: (d.index[-1]-d.index[0]).days/365.25 for s, d in data.items()})
    print(f"universe: {len(data)} products with >={MINBARS} daily bars, "
          f"median history {span.median():.1f}y, longest {span.max():.1f}y")
    print(f"book: Keltner lower-band touch, range regime (eff<{EFF}), "
          f"target {T_ATR} ATR, stop {S_ATR} ATR, hold {HOLD} days\n")
    T = trades(data)
    T["yr"] = T.ts.dt.year
    print(f"{len(T):,} trades, {T.sym.nunique()} products, "
          f"{T.yr.min()}-{T.yr.max()}\n")

    print("=" * 92)
    print("YEAR BY YEAR — the only question that matters is how many markets it worked in")
    print(f"  {'year':>6}{'trades':>8}{'net/trade':>12}{'t':>8}{'control':>10}"
          f"{'edge':>9}{'win%':>7}{'total%':>9}")
    good = 0; yrs = 0
    for y, g in T.groupby("yr"):
        if len(g) < 40: continue
        yrs += 1
        m = g.ret.mean(); t = m/(g.ret.std(ddof=1)/np.sqrt(len(g)))
        c = g.ctrl.dropna()
        edge = m - (c.mean() if len(c) else 0)
        if m > 0: good += 1
        print(f"  {y:>6}{len(g):>8}{m*100:>+11.3f}%{t:>+8.2f}"
              f"{(c.mean() if len(c) else np.nan)*100:>+9.3f}%{edge*100:>+8.3f}%"
              f"{(g.ret>0).mean()*100:>6.0f}%{g.ret.sum()*100:>+8.1f}%")
    print(f"\n  profitable in {good} of {yrs} years with >=40 trades")

    print("\n" + "=" * 92)
    print("POOLED, AND SPLIT AT THE MIDPOINT")
    mid = T.ts.quantile(0.5)
    for tag, G in (("all history", T), (f"first half (to {mid.date()})", T[T.ts < mid]),
                   (f"second half (from {mid.date()})", T[T.ts >= mid])):
        if len(G) < 100: continue
        m = G.ret.mean(); t = m/(G.ret.std(ddof=1)/np.sqrt(len(G)))
        c = G.ctrl.dropna()
        print(f"  {tag:<34}n={len(G):>6}  {m*100:>+7.3f}%  t={t:>+6.2f}  "
              f"control {c.mean()*100:>+7.3f}%  edge {(m-c.mean())*100:>+7.3f}%  "
              f"win {(G.ret>0).mean()*100:.0f}%")

    print("\n" + "=" * 92)
    print("WHAT IT WOULD HAVE PAID ON $2,000 AT 3x, PER YEAR")
    print("  (one position at a time is assumed; overlapping signals are NOT all taken)")
    for y, g in T.groupby("yr"):
        if len(g) < 40: continue
        per_yr = len(g)
        print(f"  {y}: {per_yr:>4} signals  ${g.ret.mean()*2000*3:>+7.2f}/trade  "
              f"${g.ret.sum()*2000*3:>+9.0f} if every one were taken at full size")
    T.to_csv("/home/claude/qlab/runs/system_history.csv", index=False)
    print("\n  -> runs/system_history.csv")
