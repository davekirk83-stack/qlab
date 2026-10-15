"""
ENVELOPE FAMILIES AND SUPERTREND — tested in the roles their users give them.

DK: "Are there any other envelope based systems that are more rugged? Is
supertrend worth using as many do?"

WHY "RUGGED" IS THE RIGHT WORD
Nadaraya-Watson failed for two reasons worth separating. One was the lookahead
(docs 44, 45). The other is that kernel regression has a BANDWIDTH parameter
that silently controls how much the line bends — change h and you change every
signal. The families below are sturdier because their construction is fixed:

    Keltner       EMA +/- k x ATR            — one smoothing, one width
    Donchian      N-bar high / low           — NO parameters beyond N; the band
                                               IS the price extremes, nothing
                                               is fitted, nothing can repaint
    Percentile    rolling q-th percentile    — distribution-free; no assumption
                                               that returns are symmetric
    Supertrend    ATR band that RATCHETS     — a band that only moves in the
                                               direction of trend, flipping on
                                               a close through it

Donchian is the most rugged thing on the list: it cannot repaint, has nothing
to fit, and is the same channel Richard Dennis's Turtles traded.

THE TWO ROLES — this is the lesson from docs 38/44/45
Testing an indicator in one role and declaring it dead is the error that has
cost most time today. Each tool here is therefore tested in BOTH roles it is
actually used for:

  ROLE 1  SIGNAL — mean reversion at the lower band, and breakout at the upper
          band, with a random-entry control at matched stop distance.

  ROLE 2  EXIT — as a trailing stop on the registered retest book, against the
          hold-40 exit adopted today (doc 44). This is where Supertrend most
          likely belongs, since trail_3 ATR already scored +0.666R there.

A tool can fail role 1 and still win role 2. That is the whole point.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
import retest as RT
from levels_general import load_universe

RNG = np.random.default_rng(4242)
MAXBARS = 120
HOLD = 40


# ------------------------------------------------------------- constructions
def keltner(df, n=20, k=2.0):
    ma = df.close.ewm(span=n, adjust=False).mean().values
    a = ST.atr(df).bfill().values
    return ma - k * a, ma, ma + k * a


def donchian(df, n=20):
    lo = df.low.rolling(n).min().shift(1).values
    hi = df.high.rolling(n).max().shift(1).values
    return lo, (lo + hi) / 2, hi


def percentile_band(df, n=100, q=0.05):
    lo = df.close.rolling(n).quantile(q).shift(1).values
    hi = df.close.rolling(n).quantile(1 - q).shift(1).values
    mid = df.close.rolling(n).median().shift(1).values
    return lo, mid, hi


def supertrend(df, n=10, k=3.0):
    """Classic Supertrend. Returns (line, direction) where direction is +1 when
    the band sits BELOW price (bullish) and -1 when above.

    The ratchet is the whole idea: in an uptrend the lower band can only rise,
    so it behaves as a trailing stop that never loosens."""
    H, L, C = df.high.values, df.low.values, df.close.values
    a = ST.atr(df, n).bfill().values
    hl2 = (H + L) / 2
    up = hl2 - k * a
    dn = hl2 + k * a
    N = len(C)
    line = np.full(N, np.nan)
    dirn = np.ones(N, dtype=int)
    fu, fd = up[0], dn[0]
    for i in range(1, N):
        fu = max(up[i], fu) if C[i - 1] > fu else up[i]
        fd = min(dn[i], fd) if C[i - 1] < fd else dn[i]
        if dirn[i - 1] == 1:
            dirn[i] = -1 if C[i] < fu else 1
        else:
            dirn[i] = 1 if C[i] > fd else -1
        line[i] = fu if dirn[i] == 1 else fd
    return line, dirn


BANDS = {
    "keltner_20_2": lambda d: keltner(d, 20, 2.0),
    "keltner_20_3": lambda d: keltner(d, 20, 3.0),
    "donchian_20": lambda d: donchian(d, 20),
    "donchian_55": lambda d: donchian(d, 55),
    "pctile_100_5": lambda d: percentile_band(d, 100, 0.05),
}


# ------------------------------------------------------------------- role 1
def hold_exit(df, bar, entry, stop, hold=HOLD):
    L, C = df.low.values, df.close.values
    risk = entry - stop
    if risk <= 0:
        return None
    last = bar + hold
    if last > len(C) - 1:
        return None
    for j in range(bar + 1, last + 1):
        if L[j] <= stop:
            return -1.0
    return float((C[last] - entry) / risk)


def role1(which, stop_atr=1.5):
    panel = load_universe(which)
    out = {}
    for s, df in panel.items():
        if len(df) < 800:
            continue
        C = df.close.values
        a = ST.atr(df).bfill().values
        n = len(C)
        sigs = {}
        for name, fn in BANDS.items():
            lo, mid, hi = fn(df)
            ok = ~(np.isnan(lo) | np.isnan(hi))
            rev = np.zeros(n, bool)
            rev[1:] = ok[1:] & (C[:-1] <= lo[:-1]) & (C[1:] > lo[1:])
            sigs[f"{name}__revert"] = np.flatnonzero(rev)
            brk = np.zeros(n, bool)
            brk[1:] = ok[1:] & (C[:-1] <= hi[:-1]) & (C[1:] > hi[1:])
            sigs[f"{name}__breakout"] = np.flatnonzero(brk)
        line, dirn = supertrend(df)
        flip = np.zeros(n, bool)
        flip[1:] = (dirn[1:] == 1) & (dirn[:-1] == -1)
        sigs["supertrend__flip_long"] = np.flatnonzero(flip)

        for name, idx in sigs.items():
            idx = [i for i in idx if 250 < i < n - HOLD - 2 and a[i] > 0]
            kept, last = [], -10**9
            for i in idx:
                if i - last >= HOLD:
                    kept.append(i); last = i
            got = [hold_exit(df, i, C[i], C[i] - stop_atr * a[i]) for i in kept]
            got = [g for g in got if g is not None]
            if got:
                out.setdefault(name, []).extend(got)
            for _ in range(len(kept)):
                j = int(RNG.integers(250, max(251, n - HOLD - 2)))
                if a[j] <= 0:
                    continue
                g = hold_exit(df, j, C[j], C[j] - stop_atr * a[j])
                if g is not None:
                    out.setdefault("CONTROL", []).append(g)
    return out


# ------------------------------------------------------------------- role 2
def role2(which):
    """Supertrend and friends as the EXIT on the registered retest book."""
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 800:
            continue
        C, H, L = df.close.values, df.high.values, df.low.values
        a = ST.atr(df).bfill().values
        n = len(C)
        st_line, st_dir = supertrend(df)
        st_line2, st_dir2 = supertrend(df, 10, 2.0)
        setups = RT.diagonal_setups(df, *PP.confirmed_pivots(df)[::-1]) \
            if False else None
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        for u in RT.diagonal_setups(df, highs, lows):
            rb = u.get("retest_bar")
            if rb is None or u.get("failed"):
                continue
            stop = u.get("retest_stop") or u["stop"]
            entry = C[rb]
            risk = entry - stop
            if risk <= 0 or rb + HOLD >= n:
                continue
            r = {}
            # the adopted exit
            r["hold_40"] = hold_exit(df, rb, entry, stop)
            # supertrend trailing exit: leave when it flips bearish
            for lab, dirn, lineq in (("supertrend_3", st_dir, st_line),
                                     ("supertrend_2", st_dir2, st_line2)):
                res = None
                for j in range(rb + 1, min(rb + 1 + MAXBARS, n)):
                    if L[j] <= stop:
                        res = -1.0; break
                    if dirn[j] == -1:
                        res = float((C[j] - entry) / risk); break
                if res is None:
                    res = float((C[min(rb + MAXBARS, n - 1)] - entry) / risk)
                r[lab] = res
            # donchian trailing exit: leave on a close below the 20-bar low
            dlo, _, _ = donchian(df, 20)
            res = None
            for j in range(rb + 1, min(rb + 1 + MAXBARS, n)):
                if L[j] <= stop:
                    res = -1.0; break
                if np.isfinite(dlo[j]) and C[j] < dlo[j]:
                    res = float((C[j] - entry) / risk); break
            r["donchian_exit"] = res if res is not None else \
                float((C[min(rb + MAXBARS, n - 1)] - entry) / risk)
            if r["hold_40"] is not None:
                rows.append(r)
    return pd.DataFrame(rows)


def line(lab, r, base=None, pad=30):
    r = np.asarray(r, dtype=float); r = r[np.isfinite(r)]
    if len(r) < 50:
        print(f"  {lab:{pad}s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"   vs {base[0]} {r.mean()-base[1]:+6.3f}R" if base else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  {r.mean():+6.3f}R  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("ENVELOPE FAMILIES AND SUPERTREND\n")
    for which in ("crypto_hourly", "etf"):
        print("=" * 96)
        print(f"  {which.upper()} — ROLE 1: as a SIGNAL (hold 40, stop 1.5 ATR)")
        print("=" * 96)
        o = role1(which)
        base = line("CONTROL (random)", o.get("CONTROL", []))
        print()
        for k in sorted(o):
            if k == "CONTROL":
                continue
            line(k.replace("__", "  "), o[k], ("control", base) if base else None)
        print()
        print("=" * 96)
        print(f"  {which.upper()} — ROLE 2: as an EXIT on the retest book (diagonals)")
        print("=" * 96)
        T = role2(which)
        if len(T) >= 50:
            b = line("hold_40 (adopted, doc 44)", T.hold_40.values)
            for c in ("supertrend_3", "supertrend_2", "donchian_exit"):
                line(c, T[c].values, ("hold_40", b) if b else None)
        else:
            print(f"  only {len(T)} setups")
        print()
