"""
IS "FADE THE EXTREME" UNIVERSAL, OR ONE CLUSTER DOMINATING THE MEDIAN?

DK: "Is this worth doing for another 5-10 more top traders?"

The honest answer was no: doc 77 already covered 45 accounts and 13,182
entries. Account count is not the constraint. Two other things are, and both
are answerable with the data in hand:

  1. SELECTION. All 45 were ranked the same way — profit per dollar traded —
     which may have selected one style and measured it 45 times.
  2. AGGREGATION. Doc 77 reported MEDIANS. If there are three distinct
     archetypes, the median describes none of them.

So instead of more traders: cluster the ones we have, by behaviour, and see
whether the headline finding survives being broken apart.

PER-ACCOUNT BEHAVIOURAL FINGERPRINT
  reversion       mean standardised entry level across the mean-reversion
                  elements, SIGNED so that positive always means "fades the
                  extreme" and negative means "follows the move"
  vol_timing      how elevated range and volume are at their entries
  passive         share of entries resting rather than crossing
  breadth         instruments traded
  clip            median notional per fill
  tempo           fills per hour

Then k-means on the standardised fingerprint, and the doc 77 headline is
recomputed WITHIN each cluster. If every cluster fades, it is universal. If
one cluster follows the move and simply trades less, the median was hiding it.
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import elements as EL

RNG = np.random.default_rng(99)
REV = ["wavetrend", "rci_26", "bb_pctb_50", "range_pos_50", "rsi_50",
       "dist_ema_200", "tsi", "macd", "range_pos_200", "pi_ratio"]
TIM = ["range_pctile_50", "vol_rel", "atr_pct", "bb_width_20"]


def candles(path):
    d = pd.DataFrame(json.load(open(path)))
    for c in ("o", "c", "h", "l", "v"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.t, unit="ms")
    d = (d.sort_values("ts").reset_index(drop=True)
          .rename(columns={"o": "open", "c": "close", "h": "high",
                           "l": "low", "v": "volume"}))
    return d.set_index("ts")[["open", "high", "low", "close", "volume"]]


def fingerprint():
    out = []
    for fp in sorted(glob.glob("/tmp/fills/win_*.json")):
        addr = os.path.basename(fp)[4:-5]
        try:
            f = pd.DataFrame(json.load(open(fp)))
        except Exception:
            continue
        if not len(f) or "dir" not in f:
            continue
        for c in ("px", "sz"):
            f[c] = pd.to_numeric(f[c], errors="coerce")
        f["ts"] = pd.to_datetime(f.time, unit="ms")
        f["notional"] = f.px * f.sz
        rev, tim, n_ent, psv = [], [], 0, []
        for coin, g in f.groupby("coin"):
            cp = f"/tmp/cdl/{str(coin).replace(':','_')}.json"
            if not os.path.exists(cp):
                continue
            d = candles(cp)
            if len(d) < 400:
                continue
            try:
                F = EL.build(d)
            except Exception:
                continue
            g = g[(g.ts >= d.index.min()) & (g.ts <= d.index.max())]
            g = g[g.dir.astype(str).str.contains("Open")]
            if len(g) < 5:
                continue
            idx = np.clip(d.index.searchsorted(g.ts) - 1, 250, len(d) - 2)
            for k in REV + TIM:
                if k not in F:
                    continue
                a = F[k]
                base = a[np.isfinite(a)]
                if len(base) < 200:
                    continue
                mu, sd = base.mean(), base.std()
                if sd <= 0:
                    continue
                for (_, r), i in zip(g.iterrows(), idx):
                    v = a[int(i)]
                    if not np.isfinite(v):
                        continue
                    z = (v - mu) / sd
                    short = "Short" in str(r.dir)
                    if k in REV:
                        # sign so that POSITIVE = fading the extreme
                        rev.append(z if short else -z)
                    else:
                        tim.append(z)
            n_ent += len(g)
            psv += list((~g.crossed).astype(float))
        if n_ent < 20 or not rev:
            continue
        span = max((f.ts.max() - f.ts.min()).total_seconds() / 3600, 1e-6)
        out.append(dict(addr=addr, entries=n_ent,
                        reversion=float(np.mean(rev)),
                        vol_timing=float(np.mean(tim)) if tim else np.nan,
                        passive=float(np.mean(psv)) * 100 if psv else np.nan,
                        breadth=f.coin.nunique(),
                        clip=float(f.notional.median()),
                        tempo=len(f) / span))
    return pd.DataFrame(out).dropna()


def kmeans(X, k=3, iters=120):
    Z = (X - X.mean(0)) / X.std(0).replace(0, 1)
    V = Z.values
    C = V[RNG.choice(len(V), k, replace=False)]
    for _ in range(iters):
        lab = np.argmin(((V[:, None, :] - C[None]) ** 2).sum(2), 1)
        for j in range(k):
            if (lab == j).any():
                C[j] = V[lab == j].mean(0)
    return lab


if __name__ == "__main__":
    P = fingerprint()
    print(f"BEHAVIOURAL FINGERPRINTS — {len(P)} profitable accounts, "
          f"{int(P.entries.sum()):,} entries\n")
    cols = ["reversion", "vol_timing", "passive", "breadth", "clip", "tempo"]
    P["cl"] = kmeans(P[cols], 3)
    print("  'reversion' is signed so POSITIVE = fades the extreme, "
          "NEGATIVE = follows the move\n")
    print(f"  {'cluster':<10}{'n':>4}{'entries':>9}{'reversion':>11}"
          f"{'volTiming':>11}{'passive':>9}{'breadth':>9}{'clip':>10}{'tempo':>8}")
    for c, g in P.groupby("cl"):
        print(f"  {'#'+str(c):<10}{len(g):>4}{int(g.entries.sum()):>9}"
              f"{g.reversion.median():>+11.2f}{g.vol_timing.median():>+11.2f}"
              f"{g.passive.median():>8.0f}%{g.breadth.median():>9.0f}"
              f"{g.clip.median():>10,.0f}{g.tempo.median():>8.1f}")
    print(f"\n  ACCOUNTS THAT FADE (reversion > 0):   "
          f"{(P.reversion > 0).sum()}/{len(P)}  "
          f"({(P.reversion>0).mean()*100:.0f}%)")
    print(f"  ACCOUNTS THAT FOLLOW (reversion < 0): "
          f"{(P.reversion < 0).sum()}/{len(P)}")
    print(f"\n  So the doc 77 headline is "
          f"{'UNIVERSAL' if (P.reversion>0).mean()>0.8 else 'A MAJORITY, NOT A LAW'}.")
    print(f"\n  spread of 'reversion' across accounts: "
          f"10th {P.reversion.quantile(.1):+.2f}   median "
          f"{P.reversion.median():+.2f}   90th {P.reversion.quantile(.9):+.2f}")
    print(f"  spread of 'volatility timing':          "
          f"10th {P.vol_timing.quantile(.1):+.2f}   median "
          f"{P.vol_timing.median():+.2f}   90th {P.vol_timing.quantile(.9):+.2f}")
    fad = P[P.reversion > 0]; fol = P[P.reversion < 0]
    if len(fol) >= 3:
        print(f"\n  FADERS vs FOLLOWERS")
        for k, lab, f in (("vol_timing", "volatility timing", "{:+.2f}"),
                          ("passive", "passive share", "{:.0f}%"),
                          ("breadth", "instruments", "{:.0f}"),
                          ("clip", "median clip", "${:,.0f}"),
                          ("tempo", "fills per hour", "{:.1f}")):
            print(f"    {lab:<22}{f.format(fad[k].median()):>12}"
                  f"{f.format(fol[k].median()):>12}")
