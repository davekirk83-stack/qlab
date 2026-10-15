"""
NW ENVELOPE, PART 2 — the band-to-band oscillation.

DK: "Even if it's no good as a predictor in itself, it does show an uncanny
bouncing pattern between the lower and higher envelopes."

A fair challenge, and part 1 did not answer it. Part 1 tested ONE entry (close
crossing back up through the lower band) with ONE exit (hold 40 bars). That is
not the trade DK is describing. The trade he is describing is LOWER BAND TO
MEAN, or LOWER BAND TO UPPER BAND — and it was never measured.

TWO SEPARATE QUESTIONS, deliberately kept apart

Q1  HOW MUCH OF THE CONTAINMENT IS AN ARTEFACT?
    If the repainting bands hold price inside them far more often than the
    causal bands do, the "uncanny" fit is the lookahead drawing itself. This is
    measured directly: the share of bars inside the channel, both versions,
    and how often a touch of the lower band is followed by a trip to the mean.
    A repainting band is fitted to residuals that already include the future,
    so it SHOULD contain price almost perfectly. Quantifying that is the point.

Q2  DOES THE OSCILLATION SURVIVE ON CAUSAL BANDS ANYWAY?
    Separate question, and DK's real one. Price genuinely does oscillate around
    a smoothed mean inside a volatility-scaled channel — that is close to a
    definition of mean reversion, not a claim about this indicator. So the
    band-to-band trade is tested on CAUSAL bands only:
        entry    close at or below the lower band
        targets  the MEAN, and the UPPER band (the full traverse)
        stop     below the entry by a volatility-scaled amount
        control  random entries, same targets and stop distances
    Also split by regime, because mean reversion inside a channel should work
    when the channel is FLAT and fail when it is sloping — if that split does
    not appear, the effect is not what it claims to be.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import nadaraya as NW
from levels_general import load_universe

RNG = np.random.default_rng(606)
MAXBARS = 120


def containment(which, h=8.0, mult=3.0):
    """Q1: share of bars inside the channel, repaint vs causal."""
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 800:
            continue
        c = df.close.values
        for variant in ("repaint", "causal"):
            fit = NW.nw_repaint(c, h=h) if variant == "repaint" else NW.nw_causal(c, h=h)
            lo, hi = NW.bands(c, fit, mult=mult)
            ok = ~(np.isnan(lo) | np.isnan(hi))
            if ok.sum() < 200:
                continue
            inside = ((c >= lo) & (c <= hi))[ok]
            # and: after a touch of the lower band, does price reach the mean?
            touch = np.flatnonzero(ok & (c <= lo))
            reach = []
            for i in touch:
                if i + 40 >= len(c):
                    continue
                reach.append(bool(np.nanmax(c[i + 1:i + 41]) >= fit[i]))
            rows.append(dict(sym=s, variant=variant,
                             inside=float(inside.mean()),
                             n=int(ok.sum()),
                             touches=len(reach),
                             reach_mean=float(np.mean(reach)) if reach else np.nan))
    return pd.DataFrame(rows)


def traverse(which, h=8.0, mult=3.0, stop_atr=1.5):
    """Q2: the band-to-band trade on CAUSAL bands, with a random control."""
    panel = load_universe(which)
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 800:
            continue
        c = df.close.values
        H, L = df.high.values, df.low.values
        a = ST.atr(df).bfill().values
        fit = NW.nw_causal(c, h=h)
        lo, hi = NW.bands(c, fit, mult=mult)
        ok = ~(np.isnan(lo) | np.isnan(hi) | np.isnan(fit))
        # channel slope over the last 40 bars, in ATR — flat vs sloping
        slope = np.full(len(c), np.nan)
        slope[40:] = (fit[40:] - fit[:-40]) / np.where(a[40:] > 0, a[40:], np.nan)

        sig, last = [], -10**9
        for i in np.flatnonzero(ok):
            if i < 250 or i >= len(c) - MAXBARS - 2 or a[i] <= 0:
                continue
            if c[i] <= lo[i] and i - last >= 40:
                sig.append(i); last = i

        def race(bar, entry, stop, target):
            for j in range(bar + 1, min(bar + 1 + MAXBARS, len(c))):
                if L[j] <= stop:
                    return -1.0
                if H[j] >= target:
                    return (target - entry) / (entry - stop)
            return (c[min(bar + MAXBARS, len(c) - 1)] - entry) / (entry - stop)

        for i in sig:
            entry = c[i]; stop = entry - stop_atr * a[i]
            if stop <= 0 or entry <= stop:
                continue
            real.append(dict(sym=s, to_mean=race(i, entry, stop, fit[i]),
                             to_upper=race(i, entry, stop, hi[i]),
                             width_atr=float((hi[i] - lo[i]) / a[i]),
                             slope=float(slope[i]) if slope[i] == slope[i] else np.nan))
        for _ in range(len(sig)):
            j = int(RNG.integers(250, max(251, len(c) - MAXBARS - 2)))
            if a[j] <= 0:
                continue
            entry = c[j]; stop = entry - stop_atr * a[j]
            if not (np.isfinite(fit[j]) and np.isfinite(hi[j])) or entry <= stop:
                continue
            # same target DISTANCES as a real signal would have
            dm = abs(fit[j] - lo[j]) if np.isfinite(lo[j]) else a[j]
            du = abs(hi[j] - lo[j]) if np.isfinite(lo[j]) else 2 * a[j]
            ctrl.append(dict(sym=s, to_mean=race(j, entry, stop, entry + dm),
                             to_upper=race(j, entry, stop, entry + du),
                             width_atr=np.nan, slope=np.nan))
    return pd.DataFrame(real), pd.DataFrame(ctrl)


def line(lab, r, base=None, pad=32):
    r = np.asarray(r, dtype=float); r = r[np.isfinite(r)]
    if len(r) < 50:
        print(f"  {lab:{pad}s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"   vs control {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  {r.mean():+6.3f}R  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("NW ENVELOPE PART 2 — is the band-to-band bounce real?\n")
    for which in ("crypto_hourly", "etf"):
        print("=" * 94)
        print(f"  {which.upper()}")
        print("=" * 94)
        C = containment(which)
        print("  Q1 — HOW MUCH OF THE 'UNCANNY FIT' IS THE LOOKAHEAD?")
        for v in ("repaint", "causal"):
            s = C[C.variant == v]
            if not len(s):
                continue
            print(f"    {v:8s} bars inside the channel {s.inside.mean()*100:5.1f}%   "
                  f"after a lower-band touch, reaches the mean within 40 bars "
                  f"{s.reach_mean.mean()*100:5.1f}%")
        print()
        R, K = traverse(which)
        print("  Q2 — THE BAND-TO-BAND TRADE, CAUSAL BANDS ONLY")
        if len(R) and len(K):
            for tgt in ("to_mean", "to_upper"):
                b = line(f"    control  {tgt}", K[tgt].values)
                line(f"  NW causal  {tgt}", R[tgt].values, b)
            print()
            print("  by channel slope (flat should work, sloping should not):")
            for lo_, hi_, lab in ((-99, -1.0, "falling"), (-1.0, 1.0, "FLAT"),
                                  (1.0, 99, "rising")):
                sub = R[(R.slope >= lo_) & (R.slope < hi_)]
                line(f"    {lab:8s} to_mean", sub.to_mean.values)
        print()
