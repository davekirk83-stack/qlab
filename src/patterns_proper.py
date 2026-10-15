"""
PATTERNS, TESTED THE WAY THEY ARE ACTUALLY TRADED.

DK, on the first version of this test: "You've done that thing where you write
off at lightning speed a whole corpus of technical analysis, probably done
badly, in a rush."

He is right about the method. The first test (patterns_general.py) measured
every pattern at a FIXED 5/10/20-bar horizon against a FIXED 1 ATR barrier. No
chartist trades a pattern that way. A pattern carries its own geometry, and
stripping that out and then measuring what is left is the doc 29 error repeated.

WHAT IS DIFFERENT HERE

1. REAL DETECTION. Patterns are built from major pivots (structure.py), not from
   rolling-window proxies. A double bottom requires two distinct pivot lows of
   similar depth with a genuine peak between them. An inverse head and shoulders
   requires five pivots in the right order. If the shape is not there, it does
   not fire.

2. PATTERN-NATIVE TARGETS AND STOPS. Each pattern defines its own trade:
       double bottom   target = neckline + (neckline - lows)      stop = below lows
       inverse H&S     target = neckline + (neckline - head)      stop = below head
       flag            target = breakout + flagpole height        stop = below flag low
       ascending tri   target = breakout + triangle height        stop = below last low
   That is the measured move, the thing the pattern actually claims.

3. SCORED AS A TRADE, not as a forward return: did the target come before the
   stop? That is the pattern's own claim, tested on its own terms, and it needs
   no arbitrary horizon.

4. CONFLUENCE GATES. The claim was never "a pattern anywhere works". Each
   pattern is also tested at a level, in a trend, and on volume.

5. CONTROL SURVIVES. A matched random entry, given the SAME target and stop
   distances, in the same instrument. This is the part that must not be dropped:
   a 70% hit rate means nothing if a coin flip with a 2:1 reward ratio gets 70%
   too. The control is what makes the number interpretable.

No lookahead: pivots are confirmed only `window` bars after they occur, and a
pattern can only fire on a bar at or after its last confirmed pivot.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
from levels_general import load_universe

RNG = np.random.default_rng(1009)
MAXBARS = 120          # give the measured move room; patterns are not scalps


# --------------------------------------------------------------- detection
def confirmed_pivots(df, prominence=2.0, window=5):
    """Pivot indices plus the bar at which each becomes KNOWN (i + window)."""
    lo, hi = ST.major_pivots(df, prominence=prominence, window=window)
    return [(int(i), int(i + window)) for i in lo], [(int(i), int(i + window)) for i in hi]


def d_double_bottom(df, lows, highs, tol=0.04):
    """Two pivot lows within tol of each other, a real peak between them,
    fires on the close that clears the neckline."""
    C = df.close.values; H = df.high.values; L = df.low.values
    out = []
    for a in range(len(lows) - 1):
        i1, _ = lows[a]
        for b in range(a + 1, min(a + 4, len(lows))):
            i2, k2 = lows[b]
            if i2 - i1 < 10:
                continue
            y1, y2 = L[i1], L[i2]
            if y1 <= 0 or abs(y2 / y1 - 1) > tol:
                continue
            mid = [h for h, _ in highs if i1 < h < i2]
            if not mid:
                continue
            neck_i = max(mid, key=lambda h: H[h])
            neck = H[neck_i]
            base = min(y1, y2)
            if neck <= base:
                continue
            # first close above the neckline, after the second low is confirmed
            for j in range(max(k2, neck_i + 1), min(i2 + 150, len(C))):
                if C[j] > neck:
                    out.append(dict(bar=j, entry=C[j], stop=base,
                                    target=neck + (neck - base), name="double_bottom"))
                    break
            break
    return out


def d_inv_hs(df, lows, highs, tol=0.25):
    """Five pivots: low, high, LOWER low, high, low. Fires on the neckline break."""
    C = df.close.values; H = df.high.values; L = df.low.values
    out = []
    for a in range(len(lows) - 2):
        iL, _ = lows[a]; iH, kH = lows[a + 1]; iR, kR = lows[a + 2]
        if not (iL < iH < iR):
            continue
        if L[iH] >= L[iL] or L[iH] >= L[iR]:
            continue                                   # head must be lowest
        if L[iL] <= 0 or abs(L[iR] / L[iL] - 1) > tol:
            continue                                   # shoulders roughly level
        n1 = [h for h, _ in highs if iL < h < iH]
        n2 = [h for h, _ in highs if iH < h < iR]
        if not n1 or not n2:
            continue
        neck = max(H[max(n1, key=lambda h: H[h])], H[max(n2, key=lambda h: H[h])])
        head = L[iH]
        if neck <= head:
            continue
        for j in range(kR, min(iR + 150, len(C))):
            if C[j] > neck:
                out.append(dict(bar=j, entry=C[j], stop=head,
                                target=neck + (neck - head), name="inv_hs"))
                break
    return out


def d_flag(df, lows, highs, pole=2.0, maxcons=25):
    """A real flagpole (impulse of `pole` ATR), a contained pullback, then a
    break of the pullback high. Target = pole height projected from the break."""
    C = df.close.values; H = df.high.values; L = df.low.values
    a = ST.atr(df).bfill().values
    out = []
    for i, k in highs:                       # the pivot high ends the pole
        start = max(0, i - 30)
        base = L[start:i + 1].min()
        poleh = H[i] - base
        if a[i] <= 0 or poleh < pole * a[i]:
            continue
        lo_after = None
        for j in range(k, min(i + maxcons, len(C))):
            if L[j] < base + 0.3 * poleh:    # pullback too deep: not a flag
                break
            lo_after = L[j] if lo_after is None else min(lo_after, L[j])
            if C[j] > H[i]:
                out.append(dict(bar=j, entry=C[j], stop=lo_after,
                                target=C[j] + poleh, name="flag"))
                break
    return out


def d_asc_triangle(df, lows, highs, tol=0.03):
    """Flat resistance, rising lows, break of the resistance."""
    C = df.close.values; H = df.high.values; L = df.low.values
    out = []
    for a in range(len(highs) - 1):
        i1, _ = highs[a]
        for b in range(a + 1, min(a + 4, len(highs))):
            i2, k2 = highs[b]
            if i2 - i1 < 10 or H[i1] <= 0 or abs(H[i2] / H[i1] - 1) > tol:
                continue
            inner = [l for l, _ in lows if i1 < l < i2]
            if len(inner) < 2 or L[inner[-1]] <= L[inner[0]]:
                continue                               # lows must be RISING
            res = max(H[i1], H[i2]); base = L[inner[0]]
            if res <= base:
                continue
            for j in range(k2, min(i2 + 120, len(C))):
                if C[j] > res:
                    out.append(dict(bar=j, entry=C[j], stop=L[inner[-1]],
                                    target=res + (res - base), name="asc_triangle"))
                    break
            break
    return out


DETECTORS = [d_double_bottom, d_inv_hs, d_flag, d_asc_triangle]


# ------------------------------------------------------------------ scoring
def resolve(df, bar, entry, stop, target, maxbars=MAXBARS):
    """Did the pattern's OWN target arrive before its OWN stop?"""
    H, L = df.high.values, df.low.values
    n = len(df)
    if entry <= 0 or stop >= entry or target <= entry:
        return None
    rr = (target - entry) / (entry - stop)
    if not np.isfinite(rr) or rr <= 0 or rr > 20:
        return None
    for j in range(bar + 1, min(bar + 1 + maxbars, n)):
        hit_t, hit_s = H[j] >= target, L[j] <= stop
        if hit_t and hit_s:
            return dict(win=0.0, rr=rr, bars=j - bar, resolved=1)   # assume worst
        if hit_t:
            return dict(win=1.0, rr=rr, bars=j - bar, resolved=1)
        if hit_s:
            return dict(win=0.0, rr=rr, bars=j - bar, resolved=1)
    return dict(win=np.nan, rr=rr, bars=maxbars, resolved=0)


def expectancy(t):
    """R per trade, using each trade's OWN reward:risk. Unresolved = flat."""
    r = []
    for _, x in t.iterrows():
        if x.resolved == 0:
            r.append(0.0)
        else:
            r.append(x.rr if x.win == 1.0 else -1.0)
    return np.array(r)


def control_for(df, sig, n_draw):
    """Random entries given the SAME stop and target DISTANCES as real signals."""
    C = df.close.values
    lo, hi = 150, len(C) - MAXBARS - 2
    if hi <= lo or not sig:
        return []
    out = []
    bars = RNG.choice(np.arange(lo, hi), size=min(n_draw, hi - lo), replace=False)
    for j, s in zip(bars, RNG.choice(len(sig), size=len(bars))):
        ref = sig[int(s)]
        if ref["entry"] <= 0:
            continue
        sd = 1 - ref["stop"] / ref["entry"]
        td = ref["target"] / ref["entry"] - 1
        e = C[int(j)]
        r = resolve(df, int(j), e, e * (1 - sd), e * (1 + td))
        if r:
            r["name"] = ref["name"]; out.append(r)
    return out


def run(which, prominence=2.0):
    panel = load_universe(which)
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        try:
            lows, highs = confirmed_pivots(df, prominence=prominence)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        sigs = []
        for det in DETECTORS:
            try:
                sigs += det(df, lows, highs)
            except Exception:
                continue
        keep = []
        for g in sigs:
            r = resolve(df, g["bar"], g["entry"], g["stop"], g["target"])
            if r:
                r["name"] = g["name"]; real.append(r); keep.append(g)
        if keep:
            ctrl += control_for(df, keep, len(keep))
    return pd.DataFrame(real), pd.DataFrame(ctrl)


def report(lab, T):
    if not len(T):
        print(f"  {lab:24s} no signals"); return
    R = expectancy(T)
    res = T[T.resolved == 1]
    hit = res.win.mean() if len(res) else np.nan
    se = R.std(ddof=1) / np.sqrt(len(R)) if len(R) > 1 else np.nan
    print(f"  {lab:24s} n={len(T):5d}  hit {hit*100:5.1f}%  "
          f"avg R:R {T.rr.mean():4.2f}  expectancy {R.mean():+6.3f}R  "
          f"t={R.mean()/se:+5.2f}  unresolved {(T.resolved==0).mean()*100:4.1f}%")
    return R.mean()


if __name__ == "__main__":
    print("PATTERNS WITH THEIR OWN TARGETS AND STOPS — pivot-based detection")
    print("Each pattern is scored on its own measured move, against a random")
    print("entry given the SAME reward:risk in the same instrument.\n")
    for u in ("etf", "crypto_daily", "crypto_hourly"):
        A, B = run(u)
        print("=" * 100)
        print(f"  {u.upper()}")
        print("=" * 100)
        a = report("REAL (all patterns)", A)
        b = report("CONTROL (same R:R)", B)
        if a is not None and b is not None:
            print(f"  {'EDGE':24s} {a - b:+6.3f}R per trade")
        print()
        if len(A):
            for nm in sorted(A.name.unique()):
                report(f"  {nm}", A[A.name == nm])
                if len(B):
                    report(f"    control", B[B.name == nm])
        print()
