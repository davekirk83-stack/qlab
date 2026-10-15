"""
BAND TRANSITIONS — if one side triggers, which band is hit next?

DK: "If one side of an envelope is triggered, what is the most likely
corresponding envelope band it will target next?"

A first-passage question, and answerable directly. From a touch of the lower
band, which happens FIRST: the mid, the upper, or a further excursion below?

THE NULL THAT MAKES THE ANSWER MEAN ANYTHING
From the lower band the mid is simply CLOSER than the upper, so "mid is most
likely" would be true of a coin flip and tells us nothing. For a driftless
random walk the probability of reaching an up-barrier at distance `u` before a
down-barrier at distance `d` is d / (u + d). Every observed frequency is
therefore reported against that distance-implied null.

    observed - null > 0   price is drawn toward that band beyond geometry
    observed - null ~ 0   the envelope is describing distance, nothing more

Also measured: how long each traverse takes, and the same from the upper band
(short side), since doc 44 found breakouts work and reversions do not on
crypto — so the two sides should NOT be symmetric.

Causal bands only. Keltner (EMA +/- k x ATR) and Donchian are used rather than
Nadaraya-Watson: both are repaint-proof, and Keltner's 3-ATR breakout was the
one envelope signal with a real edge (doc 47).
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import envelopes as EV
from levels_general import load_universe

MAXF = 200          # bars allowed for the traverse


def first_passage(df, i, lo, mid, hi, maxf=MAXF):
    """From bar i, which band is reached first? Returns (outcome, bars, null)."""
    H, L, C = df.high.values, df.low.values, df.close.values
    n = len(C)
    px = C[i]
    up_t, mid_t = hi[i], mid[i]
    dn_t = lo[i] - (hi[i] - lo[i]) * 0.5      # a further excursion below
    if not all(np.isfinite([up_t, mid_t, dn_t])) or px <= 0:
        return None
    hit_mid = None
    for j in range(i + 1, min(i + 1 + maxf, n)):
        if hit_mid is None and H[j] >= mid_t:
            hit_mid = j - i
        if H[j] >= up_t:
            return ("upper", j - i, hit_mid)
        if L[j] <= dn_t:
            return ("lower_again", j - i, hit_mid)
    return ("neither", maxf, hit_mid)


def null_prob(px, up_t, dn_t):
    """Driftless random-walk probability of the up barrier first."""
    u, d = up_t - px, px - dn_t
    if u <= 0 or d <= 0:
        return np.nan
    return d / (u + d)


def run(which, band="keltner_20_2"):
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 800:
            continue
        lo, mid, hi = EV.BANDS[band](df)
        C = df.close.values
        n = len(C)
        ok = ~(np.isnan(lo) | np.isnan(hi) | np.isnan(mid))
        for side in ("lower", "upper"):
            if side == "lower":
                touch = np.flatnonzero(ok & (C <= lo))
            else:
                touch = np.flatnonzero(ok & (C >= hi))
            kept, last = [], -10**9
            for i in touch:
                if 250 < i < n - MAXF - 2 and i - last >= 40:
                    kept.append(i); last = i
            for i in kept:
                if side == "lower":
                    r = first_passage(df, i, lo, mid, hi)
                    if r is None:
                        continue
                    nl = null_prob(C[i], hi[i], lo[i] - (hi[i] - lo[i]) * 0.5)
                else:
                    # mirror: from the upper band, does it reach the LOWER band
                    # before extending further up?
                    H, L = df.high.values, df.low.values
                    up_t = hi[i] + (hi[i] - lo[i]) * 0.5
                    out = ("neither", MAXF, None)
                    hit_mid = None
                    for j in range(i + 1, min(i + 1 + MAXF, n)):
                        if hit_mid is None and L[j] <= mid[i]:
                            hit_mid = j - i
                        if L[j] <= lo[i]:
                            out = ("lower", j - i, hit_mid); break
                        if H[j] >= up_t:
                            out = ("upper_again", j - i, hit_mid); break
                    r = out
                    nl = 1 - null_prob(C[i], up_t, lo[i])
                rows.append(dict(sym=s, side=side, outcome=r[0], bars=r[1],
                                 bars_to_mid=r[2], null=nl,
                                 width=float((hi[i] - lo[i]) / C[i])))
    return pd.DataFrame(rows)


def report(T, which, band):
    print("=" * 94)
    print(f"  {which.upper()}  —  {band}   n={len(T)} touches")
    print("=" * 94)
    for side in ("lower", "upper"):
        S = T[T.side == side]
        if len(S) < 60:
            print(f"  {side}: too few\n"); continue
        print(f"  FROM THE {side.upper()} BAND  (n={len(S)})")
        mid_hit = S.bars_to_mid.notna()
        print(f"    reaches the MID at all        {mid_hit.mean()*100:5.1f}%"
              f"   median {S.bars_to_mid.median():.0f} bars")
        for oc in S.outcome.value_counts().index:
            sub = S[S.outcome == oc]
            print(f"    first reaches {oc:14s} {len(sub)/len(S)*100:5.1f}%"
                  f"   median {sub.bars.median():.0f} bars")
        if side == "lower":
            got = (S.outcome == "upper").mean()
            nl = S.null.mean()
            print(f"    -> upper band first: observed {got*100:5.1f}%  "
                  f"random-walk null {nl*100:5.1f}%  "
                  f"EDGE {(got-nl)*100:+5.1f}pp")
        else:
            got = (S.outcome == "lower").mean()
            nl = S.null.mean()
            print(f"    -> lower band first: observed {got*100:5.1f}%  "
                  f"random-walk null {nl*100:5.1f}%  "
                  f"EDGE {(got-nl)*100:+5.1f}pp")
        print()


if __name__ == "__main__":
    print("BAND TRANSITIONS — which band does price target after touching one?\n")
    print("Compared against the distance-implied random-walk null, because from")
    print("the lower band the mid is simply nearer than the upper.\n")
    for which in ("crypto_hourly", "etf"):
        for band in ("keltner_20_2", "donchian_20"):
            T = run(which, band)
            if len(T):
                report(T, which, band)
