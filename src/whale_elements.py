"""
WHAT WAS THE CHART SAYING AT THE MOMENT THEY ENTERED?

DK: "And / or what indicators are telling them to target that moment / chart
     position."

We cannot read their minds, but we can read their clock. For every entry fill
of every profitable account, compute our 66-element library on the bar BEFORE
the fill, and compare the distribution against the same elements at random
bars in the same instrument over the same window.

An element whose value at their entries differs sharply from random is an
element that describes the condition they were waiting for — whether or not
they personally look at that indicator. It is the chart state they chose.

Scored as a standardised difference (Cohen's d) so elements on different
scales are comparable, with longs and shorts kept separate because a condition
that is bullish must appear with opposite sign on the two sides. An element
that looks "strong" on both sides with the SAME sign is measuring when they
trade, not which way.
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import elements as EL

RNG = np.random.default_rng(4242)


def candles(path):
    d = pd.DataFrame(json.load(open(path)))
    for c in ("o", "c", "h", "l", "v"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.t, unit="ms")
    d = (d.sort_values("ts").reset_index(drop=True)
          .rename(columns={"o": "open", "c": "close", "h": "high",
                           "l": "low", "v": "volume"}))
    return d.set_index("ts")[["open", "high", "low", "close", "volume"]]


def run():
    rows = []
    for fp in sorted(glob.glob("/tmp/fills/win_*.json")):
        try:
            f = pd.DataFrame(json.load(open(fp)))
        except Exception:
            continue
        if not len(f) or "dir" not in f:
            continue
        f["px"] = pd.to_numeric(f.px, errors="coerce")
        f["ts"] = pd.to_datetime(f.time, unit="ms")
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
            if len(g) < 5:
                continue
            idx = np.clip(d.index.searchsorted(g.ts) - 1, 250, len(d) - 2)
            for (_, r), i in zip(g.iterrows(), idx):
                if "Open" not in str(r.dir):
                    continue
                side = "short" if "Short" in str(r.dir) else "long"
                rec = {"side": side, "grp": "REAL"}
                for k, arr in F.items():
                    v = arr[int(i)]
                    rec[k] = v if np.isfinite(v) else np.nan
                rows.append(rec)
                j = int(RNG.integers(250, len(d) - 2))
                rec2 = {"side": side, "grp": "CTRL"}
                for k, arr in F.items():
                    v = arr[j]
                    rec2[k] = v if np.isfinite(v) else np.nan
                rows.append(rec2)
    return pd.DataFrame(rows)


def cohen(a, b):
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 100 or len(b) < 100:
        return np.nan
    s = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (a.mean() - b.mean()) / s if s > 0 else np.nan


if __name__ == "__main__":
    T = run()
    feats = [c for c in T.columns if c not in ("side", "grp")]
    print(f"ELEMENT STATE AT WINNERS' ENTRY BARS vs RANDOM BARS")
    print(f"{int((T.grp=='REAL').sum()):,} entry fills, "
          f"{len(feats)} elements\n")
    out = []
    for k in feats:
        dl = cohen(T[(T.side == "long") & (T.grp == "REAL")][k].values,
                   T[(T.side == "long") & (T.grp == "CTRL")][k].values)
        ds = cohen(T[(T.side == "short") & (T.grp == "REAL")][k].values,
                   T[(T.side == "short") & (T.grp == "CTRL")][k].values)
        if not (np.isfinite(dl) and np.isfinite(ds)):
            continue
        out.append(dict(el=k, d_long=dl, d_short=ds,
                        opposed=(np.sign(dl) != np.sign(ds)),
                        power=min(abs(dl), abs(ds)) if np.sign(dl) != np.sign(ds)
                              else 0.0, same=abs((dl + ds) / 2)))
    R = pd.DataFrame(out)
    print("  DIRECTIONAL — the element points the OPPOSITE way for longs and")
    print("  shorts, so it describes WHICH WAY they chose to trade.\n")
    print(f"  {'element':<20}{'d(long)':>10}{'d(short)':>10}{'reading':>34}")
    for _, r in R[R.opposed].nlargest(12, "power").iterrows():
        rd = ("long when HIGH, short when LOW" if r.d_long > 0
              else "long when LOW, short when HIGH")
        print(f"  {r.el:<20}{r.d_long:>+10.2f}{r.d_short:>+10.2f}{rd:>34}")
    print("\n  TIMING — same sign on both sides, so it describes WHEN they")
    print("  trade at all, regardless of direction.\n")
    print(f"  {'element':<20}{'d(long)':>10}{'d(short)':>10}{'reading':>34}")
    for _, r in R[~R.opposed].nlargest(10, "same").iterrows():
        rd = "they act when this is HIGH" if r.d_long > 0 else "they act when this is LOW"
        print(f"  {r.el:<20}{r.d_long:>+10.2f}{r.d_short:>+10.2f}{rd:>34}")
