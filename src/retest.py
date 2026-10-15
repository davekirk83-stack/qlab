"""
BREAK AND RETEST — is the retest the execution point?

DK: "When a price level breaks, and is then retested for confirmation, is that
where we would aim to execute?"

This is the one idea that survived the general pattern sweep best: `sretest` was
the only pattern positive on BOTH forward return and the exit-free barrier race
in two universes. But it was never tested with a native target and stop, which
is the test that matters (doc 39).

THE THREE WAYS TO TRADE THE SAME BREAK — the actual question

    BREAK       buy the close that clears the level
    RETEST      wait; buy only if price comes back to the level and holds it
    FAILED      price comes back and closes decisively through -> no trade
                (measured anyway, to see what is being avoided)

All three use the SAME stop (below the level, volatility-scaled) and the SAME
target (the measured move: level + the height of the base that preceded it), so
the comparison is purely about WHEN you execute, not about a different trade.

That is the only way to answer DK's question. Comparing a retest entry with some
other strategy's numbers would answer nothing.

WHAT COUNTS AS A RETEST
After a decisive close above a level, price must return to within `tol x ATR`
of it within `window` bars, and then close back above it. Buying that close is
the retest entry. If price instead closes below the level by more than the
tolerance, the break has failed and the setup is void.

CONTROL: a random entry in the same instrument given the same stop and target
distances, so a high hit rate cannot flatter a low reward:risk.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
from levels_general import load_universe

RNG = np.random.default_rng(8123)
MAXBARS = 120


def levels_from_pivots(df, highs, upto, band=0.25):
    """Resistance levels (pivot highs) known before `upto`."""
    H = df.high.values
    px = df.close.values[upto]
    out = [(int(i), float(H[i])) for i, k in highs if k < upto]
    return [(i, p) for i, p in out
            if np.isfinite(p) and p > 0 and abs(p / px - 1) <= band]


def diagonal_setups(df, highs, lows, tol_atr=0.4, retest_window=20,
                    min_touches=3, tail=None):
    """DK: "Similar breaks and reclaims also happen on established diagonal
    trendlines."

    Harder than the horizontal case, because the level MOVES: the line's price
    at the break bar is not its price at the retest bar, so both the retest
    test and the stop have to track the projection rather than a fixed price.

    A line must be ESTABLISHED before it can be broken — at least `min_touches`
    later bars touching it without closing through. An untouched line through
    two pivots is a drawing, not a level.
    """
    H, L, C = df.high.values, df.low.values, df.close.values
    a = ST.atr(df).bfill().values
    n = len(df)
    lim = n - 2 if tail == 0 else n - MAXBARS - 2
    out = []
    P = [i for i, k in highs]                      # descending resistance lines
    for ai in range(max(0, len(P) - 40), len(P) - 1):
        for bi in range(ai + 1, min(ai + 6, len(P))):
            i1, i2 = P[ai], P[bi]
            if i2 - i1 < 10:
                continue
            y1, y2 = H[i1], H[i2]
            slope = (y2 - y1) / (i2 - i1)
            if slope >= 0:
                continue                           # want a falling resistance
            def line_at(j):
                return y1 + slope * (j - i1)
            # establish: count touches, stop at the first decisive break
            touches, brk = 0, None
            for j in range(i2 + 1, min(lim, i2 + 400)):
                lv = line_at(j)
                if lv <= 0 or a[j] <= 0:
                    break
                if C[j] > lv + tol_atr * a[j]:
                    brk = j; break
                if abs(H[j] - lv) <= tol_atr * a[j]:
                    touches += 1
            if brk is None or touches < min_touches:
                continue
            lvl_at_break = line_at(brk)
            base = L[max(0, brk - 120):brk + 1].min()
            height = lvl_at_break - base
            if height <= 0:
                continue
            rec = dict(break_bar=brk, level=lvl_at_break,
                       stop=lvl_at_break - tol_atr * a[brk],
                       target=lvl_at_break + height,
                       entry_break=C[brk], touches=touches,
                       retest_bar=None, retest_stop=None, failed=False)
            for j in range(brk + 1, min(brk + 1 + retest_window, lim)):
                lv = line_at(j)
                if C[j] < lv - tol_atr * a[j]:
                    rec["failed"] = True; break
                if L[j] <= lv + tol_atr * a[j] and C[j] > lv:
                    rec["retest_bar"] = j
                    rec["retest_stop"] = lv - tol_atr * a[j]
                    break
            out.append(rec)
            break                                  # one line per anchor
    return out


def find_setups(df, highs, lows, tol_atr=0.4, retest_window=20, tail=None):
    """`tail` is how many bars at the end are reserved for scoring.

    Backtesting needs MAXBARS of future to resolve a trade, so the search stops
    there. A FORWARD tracker must see setups right up to the last bar and
    resolve them later as bars arrive — it passes tail=0.
    """
    """Every break of a pivot-high level, with its break entry and, if it
    happens, its retest entry. Same stop and target for both."""
    H, L, C = df.high.values, df.low.values, df.close.values
    a = ST.atr(df).bfill().values
    n = len(df)
    lim = n - 2 if tail == 0 else n - MAXBARS - 2
    lo_idx = sorted(i for i, _ in lows)
    out = []
    for i, k in highs:
        lvl = H[i]
        if not np.isfinite(lvl) or lvl <= 0:
            continue
        # base height: the drop from this high to the lowest low before it
        prior_lows = [j for j in lo_idx if j < i]
        if not prior_lows:
            continue
        base = L[max(0, i - 120):i + 1].min()
        height = lvl - base
        if height <= 0:
            continue
        # first decisive close above the level, after the pivot is confirmed
        br = None
        for j in range(k, min(i + 300, lim)):
            if a[j] <= 0:
                continue
            if C[j] > lvl + tol_atr * a[j]:
                br = j; break
            if C[j] < base:
                break                       # structure gone; stop looking
        if br is None:
            continue
        stop = lvl - tol_atr * a[br]
        target = lvl + height
        rec = dict(sym=None, break_bar=br, level=lvl, stop=stop, target=target,
                   entry_break=C[br])
        # does it come back?
        rt, failed = None, False
        for j in range(br + 1, min(br + 1 + retest_window, lim)):
            if C[j] < lvl - tol_atr * a[j]:
                failed = True; break
            if L[j] <= lvl + tol_atr * a[j] and C[j] > lvl:
                rt = j; break
        rec["retest_bar"] = rt
        rec["failed"] = failed
        out.append(rec)
    return out


def score(df, bar, entry, stop, target):
    r = PP.resolve(df, bar, entry, stop, target, maxbars=MAXBARS)
    if not r:
        return None
    return dict(R=(0.0 if r["resolved"] == 0
                   else (r["rr"] if r["win"] == 1 else -1.0)),
                rr=r["rr"], win=r["win"], resolved=r["resolved"],
                bars=r["bars"])


def run_diagonal(which):
    """Same three-way comparison, on established diagonal trend lines."""
    panel = load_universe(which)
    brk, ret, nort = [], [], []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        C = df.close.values
        for sid, u in enumerate(diagonal_setups(df, highs, lows)):
            key = f"{s}|{sid}"
            b = score(df, u["break_bar"], u["entry_break"], u["stop"], u["target"])
            if b:
                b["sym"] = s; b["sid"] = key
                b["retested"] = u["retest_bar"] is not None
                b["touches"] = u["touches"]
                brk.append(b)
            if u["retest_bar"] is not None:
                rb = u["retest_bar"]
                r = score(df, rb, C[rb], u["retest_stop"], u["target"])
                if r:
                    r["sym"] = s; r["sid"] = key; r["touches"] = u["touches"]
                    ret.append(r)
            elif not u["failed"] and b:
                nort.append(b)
    return pd.DataFrame(brk), pd.DataFrame(ret), pd.DataFrame(nort)


def run(which):
    panel = load_universe(which)
    brk, ret, ctrl, nort = [], [], [], []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        setups = find_setups(df, highs, lows)
        C = df.close.values
        for sid, u in enumerate(setups):
            key = f"{s}|{sid}"
            b = score(df, u["break_bar"], u["entry_break"], u["stop"], u["target"])
            if b:
                b["sym"] = s; b["sid"] = key
                b["retested"] = u["retest_bar"] is not None
                brk.append(b)
            if u["retest_bar"] is not None:
                rb = u["retest_bar"]
                r = score(df, rb, C[rb], u["stop"], u["target"])
                if r:
                    r["sym"] = s; r["sid"] = key; ret.append(r)
            elif not u["failed"] and b:
                nort.append(b)          # broke and never looked back
            # control with the same geometry
            if b and u["entry_break"] > 0:
                sd = 1 - u["stop"] / u["entry_break"]
                td = u["target"] / u["entry_break"] - 1
                j = int(RNG.integers(200, max(201, len(df) - MAXBARS - 2)))
                e = C[j]
                c = score(df, j, e, e * (1 - sd), e * (1 + td))
                if c:
                    ctrl.append(c)
    return (pd.DataFrame(brk), pd.DataFrame(ret),
            pd.DataFrame(nort), pd.DataFrame(ctrl))


def line(lab, T, base=None, pad=38):
    if len(T) < 40:
        print(f"  {lab:{pad}s} n={len(T):5d}  too few"); return None
    r = T.R.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    res = T[T.resolved == 1]
    hit = res.win.mean() * 100 if len(res) else float("nan")
    d = f"  vs break {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  hit {hit:5.1f}%  R:R {T.rr.mean():4.2f}  "
          f"{r.mean():+6.3f}R  t={r.mean()/se:+5.2f}{d}")
    return r.mean()


def compare(B, R, N, C, label):
    print("=" * 104)
    print(f"  {label}")
    print("=" * 104)
    b = line("BUY THE BREAK (every break)", B)
    if C is not None and len(C):
        line("  control, same R:R", C)
    print()
    if len(R) and len(B):
        # PAIRED: only the setups that actually retested, both ways.
        # Comparing the retest subset against ALL breaks is not a comparison —
        # the subsets are different trades.
        pair = set(R.sid) & set(B.sid)
        Bp = B[B.sid.isin(pair)]; Rp = R[R.sid.isin(pair)]
        bp = line("PAIRED — same setups, bought at break", Bp)
        line("PAIRED — same setups, bought at retest", Rp, bp)
    print()
    line("NO RETEST (broke and ran) *see caveat", N, b)
    print()


if __name__ == "__main__":
    print("BREAK vs RETEST — same level, same stop, same target, different timing")
    print("* the 'broke and ran' group is selected on price action AFTER entry")
    print("  and is therefore circular. Reported to show what it is, not to trade.\n")
    print("#" * 104)
    print("  PART 1 — HORIZONTAL LEVELS")
    print("#" * 104)
    for u in ("crypto_hourly", "crypto_daily", "etf"):
        B, R, N, C = run(u)
        compare(B, R, N, C, u.upper())
    print("#" * 104)
    print("  PART 2 — ESTABLISHED DIAGONAL TREND LINES (DK: breaks and reclaims)")
    print("#" * 104)
    for u in ("crypto_hourly", "crypto_daily", "etf"):
        B, R, N = run_diagonal(u)
        compare(B, R, N, None, f"{u.upper()}  (diagonal)")
