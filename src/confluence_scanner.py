"""
CONFLUENCE SCANNER — the working tool, not another verdict.

DK: "Of course the context matters."

Taken as a premise. This stops asking whether context helps and instead scores
every setup by how much of it is present, then calibrates what each component is
worth so the score means something in R rather than in enthusiasm.

WHAT IT SCORES
    pattern     double bottom / inverse H&S / ascending triangle, detected from
                major pivots, each carrying its own target and stop
                (flags excluded: measured at -0.23R, t=-12.46 — the flagpole
                 projection overshoots and the trade dies at the stop)
    level       the pattern's structural low sits on a horizontal level visible
                beforehand
    trend       breakout above the 200-bar average
    volume      breakout bar above 1.5x its 20-bar average
    rr          the pattern's own reward:risk

CALIBRATION, not adjudication
Each component's weight is its measured contribution in R, fitted on the FIRST
HALF of history and reported on the second. A component that contributes nothing
gets a weight near zero on its own, without needing a verdict attached to it.

OUTPUT
A ranked list of live setups with the score, the components present, and the
pattern's own entry, stop and target. Research only — no order path exists.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, glob
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
from levels_general import load_universe

PATTERNS = [PP.d_double_bottom, PP.d_inv_hs, PP.d_asc_triangle]   # flags excluded
OUT = "/home/claude/qlab/runs/confluence"


def level_grid(df, lows, highs, step=50, band=0.25):
    """Horizontal levels every `step` bars.

    Pivots are passed in and computed ONCE — calling all_levels per grid point
    re-ran major_pivots over the whole history each time, which made this
    quadratic and unusable on 20k-bar hourly series."""
    Lv, Hv = df.low.values, df.high.values
    C = df.close.values
    piv = sorted([(int(i), float(Lv[i])) for i in lows] +
                 [(int(i), float(Hv[i])) for i in highs])
    idx = np.array([p[0] for p in piv]); prc = np.array([p[1] for p in piv])
    grid = {}
    for b in range(200, len(df), step):
        px = C[b]
        if px <= 0:
            grid[b] = np.array([]); continue
        m = idx < b
        p = prc[m]
        w = df.iloc[:b + 1]
        extra = [w.low.min(), w.high.max()]
        for bars in (365, 730):
            if b > bars:
                s = w.iloc[-bars:]
                extra += [s.low.min(), s.high.max()]
        p = np.concatenate([p, np.array(extra, dtype=float)]) if len(p) else \
            np.array(extra, dtype=float)
        p = p[np.isfinite(p) & (p > 0)]
        grid[b] = p[np.abs(p / px - 1) <= band]
    return grid


def nearest_fast(grid, bar, price, step=50):
    k = max(200, (bar // step) * step)
    while k not in grid and k > 200:
        k -= step
    lv = grid.get(k)
    if lv is None or len(lv) == 0 or price <= 0:
        return np.inf
    return float(np.min(np.abs(lv - price)))


def nearest_grid(grid, bar, price, step=25):
    k = max(200, (bar // step) * step)
    while k not in grid and k > 200:
        k -= step
    lv = grid.get(k, [])
    if not lv or price <= 0:
        return np.inf
    return min(abs(p - price) for p in lv)


def features(df, name_filter=None):
    """Every detected setup in one instrument, with its components."""
    try:
        lows, highs = PP.confirmed_pivots(df)
    except Exception:
        return []
    if len(lows) < 4 or len(highs) < 4:
        return []
    lows_i = [i for i, _ in lows]; highs_i = [i for i, _ in highs]
    a = ST.atr(df).bfill().values
    ma = df.close.rolling(200).mean().values
    v = df.volume.replace(0, np.nan) if "volume" in df.columns else None
    vr = (v / v.rolling(20).mean()).fillna(1.0).values if v is not None \
        else np.ones(len(df))
    grid = level_grid(df, lows_i, highs_i)
    C = df.close.values
    out = []
    for det in PATTERNS:
        try:
            sigs = det(df, lows, highs)
        except Exception:
            continue
        for g in sigs:
            r = PP.resolve(df, g["bar"], g["entry"], g["stop"], g["target"])
            if not r:
                continue
            b = g["bar"]
            d = nearest_fast(grid, b, g["stop"])
            out.append(dict(
                bar=b, name=g["name"], rr=r["rr"], win=r["win"],
                resolved=r["resolved"],
                R=(0.0 if r["resolved"] == 0 else (r["rr"] if r["win"] == 1 else -1.0)),
                f_level=float(d <= 0.5 * a[b]) if a[b] > 0 else 0.0,
                f_trend=float(np.isfinite(ma[b]) and C[b] > ma[b]),
                f_volume=float(vr[b] > 1.5),
                f_rr=float(r["rr"] >= 1.5),
            ))
    return out


def build(which, cap=None):
    panel = load_universe(which)
    if cap:
        panel = dict(list(panel.items())[:cap])
    rows = []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        for r in features(df):
            r["sym"] = s; r["n"] = len(df); rows.append(r)
    return pd.DataFrame(rows)


FEATS = ["f_level", "f_trend", "f_volume", "f_rr"]


def calibrate(T):
    """Weight = contribution in R, fitted in-sample (first half by bar order)."""
    T = T.sort_values("bar")
    cut = len(T) // 2
    tr, te = T.iloc[:cut], T.iloc[cut:]
    base = tr.R.mean()
    w = {}
    for f in FEATS:
        on, off = tr[tr[f] == 1].R, tr[tr[f] == 0].R
        w[f] = float(on.mean() - off.mean()) if len(on) > 40 and len(off) > 40 else 0.0
    # pattern identity as a weight too
    pw = {}
    for nm in tr.name.unique():
        s = tr[tr.name == nm].R
        pw[nm] = float(s.mean() - base) if len(s) > 40 else 0.0
    return w, pw, base, tr, te


def score(row, w, pw, base):
    return base + pw.get(row["name"], 0.0) + sum(w[f] * row[f] for f in FEATS)


def evaluate(te, w, pw, base):
    s = te.apply(lambda r: score(r, w, pw, base), axis=1)
    te = te.assign(score=s)
    print(f"  OUT-OF-SAMPLE, n={len(te)}  (weights fitted on the first half only)")
    q = te.score.quantile([0.25, 0.5, 0.75]).values
    for lab, sub in (("bottom quartile", te[te.score <= q[0]]),
                     ("2nd quartile", te[(te.score > q[0]) & (te.score <= q[1])]),
                     ("3rd quartile", te[(te.score > q[1]) & (te.score <= q[2])]),
                     ("TOP quartile", te[te.score > q[2]])):
        if len(sub) < 30:
            continue
        r = sub.R.values
        se = r.std(ddof=1) / np.sqrt(len(r))
        hit = sub[sub.resolved == 1].win.mean()
        print(f"    {lab:18s} n={len(r):5d}  hit {hit*100:5.1f}%  "
              f"R:R {sub.rr.mean():4.2f}  realised {r.mean():+6.3f}R  t={r.mean()/se:+5.2f}")
    return te


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for u in ("crypto_hourly", "crypto_daily", "etf"):
        print("=" * 96)
        print(f"  {u.upper()}")
        print("=" * 96)
        T = build(u)
        if len(T) < 400:
            print(f"  only {len(T)} setups — skipping\n"); continue
        w, pw, base, tr, te = calibrate(T)
        print(f"  base expectancy {base:+.3f}R over {len(tr)} in-sample setups")
        print("  component contributions (R, in-sample):")
        for f in FEATS:
            print(f"    {f:12s} {w[f]:+6.3f}R")
        for nm, x in sorted(pw.items(), key=lambda kv: -kv[1]):
            print(f"    {nm:14s} {x:+6.3f}R")
        print()
        te = evaluate(te, w, pw, base)
        T.to_csv(f"{OUT}/{u}_setups.csv", index=False)
        json.dump(dict(weights=w, pattern=pw, base=base),
                  open(f"{OUT}/{u}_weights.json", "w"), indent=1)
        print()
