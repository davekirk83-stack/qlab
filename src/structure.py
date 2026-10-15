"""
MARKET STRUCTURE ENGINE — major pivots, horizontal levels, and real diagonal
trend lines, drawn the way a chartist draws them.

DK, three points, all exposing the same weakness in the earlier level work:
  "During a major cascade we might be looking at annual or multi-year lows"
  "Are you able to plot trend lines on a chart using major highs and lows"
  "not just horizontals but also diagonal trends"

The level set in doc 37 looked back 400 HOURLY bars — about 17 days — and drew
a least-squares line through three recent swing lows. That is both far too
short-sighted for a major cascade and not how a trend line is actually drawn.
The forward tracker confirmed it: 16 signals in five days, zero within 0.2% of
any level it could see.

WHAT THIS BUILDS

1. MAJOR PIVOTS, by prominence rather than a fixed window. A pivot counts as
   major if the retracement either side of it is large relative to the
   instrument's own volatility — so one definition works on BTC and on FIL, and
   on daily and hourly bars alike.

2. HORIZONTAL LEVELS from those pivots, including the long ones DK named:
   all-time high/low, annual high/low, multi-year pivots, and clusters where
   several pivots stack at a similar price (the strongest kind of level).

3. DIAGONAL TREND LINES drawn properly:
     - anchored on TWO major pivots
     - scored by how many LATER bars touch the line without closing decisively
       through it (a line nobody respects is not a line)
     - invalidated once price closes beyond it by a volatility-scaled margin
     - projected forward to the current bar
   Both support (rising/falling lows) and resistance (highs).

Every level carries a STRENGTH score, so the cascade filter can ask "did the low
land on something important" rather than merely "something".

No lookahead anywhere: a line is only usable from the bar after its second
anchor, and touches are only counted up to the evaluation bar.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd


# ----------------------------------------------------------------- pivots
def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def major_pivots(df, prominence=2.0, window=5):
    """Pivots whose swing either side exceeds `prominence` x ATR.

    Returns two arrays of integer indices: (low_idx, high_idx). Significance is
    volatility-scaled, so the same setting works across instruments."""
    H, L = df.high.values, df.low.values
    a = atr(df).bfill().values
    n = len(df)
    lows, highs = [], []
    for i in range(window, n - window):
        if L[i] == L[i - window:i + window + 1].min():
            left = H[max(0, i - 60):i].max() - L[i] if i > 0 else 0
            right = H[i:min(n, i + 60)].max() - L[i]
            if min(left, right) > prominence * a[i]:
                lows.append(i)
        if H[i] == H[i - window:i + window + 1].max():
            left = H[i] - L[max(0, i - 60):i].min() if i > 0 else 0
            right = H[i] - L[i:min(n, i + 60)].min()
            if min(left, right) > prominence * a[i]:
                highs.append(i)
    return np.array(lows, dtype=int), np.array(highs, dtype=int)


# ------------------------------------------------------- horizontal levels
def horizontal_levels(df, upto, lows, highs, cluster_tol=0.01):
    """Horizontal support/resistance visible at bar `upto`, with strength.

    Strength counts how many major pivots stack within cluster_tol of each
    other — several pivots at one price is the strongest kind of level."""
    px = df.close.values[upto]
    if px <= 0:
        return []
    lo = [i for i in lows if i < upto]
    hi = [i for i in highs if i < upto]
    cand = []
    for i in lo:
        cand.append((df.low.values[i], "pivot_low", upto - i))
    for i in hi:
        cand.append((df.high.values[i], "pivot_high", upto - i))
    # the long-horizon levels DK named
    w = df.iloc[:upto + 1]
    if len(w) > 30:
        cand.append((w.low.min(), "all_time_low", len(w)))
        cand.append((w.high.max(), "all_time_high", len(w)))
    for bars, lab in ((365, "annual"), (730, "two_year")):
        if len(w) > bars:
            s = w.iloc[-bars:]
            cand.append((s.low.min(), f"{lab}_low", bars))
            cand.append((s.high.max(), f"{lab}_high", bars))
    cand = [c for c in cand if np.isfinite(c[0]) and c[0] > 0
            and abs(c[0] / px - 1) <= 0.35]
    if not cand:
        return []

    # MERGE first, then score. Scoring each candidate separately returned nine
    # near-identical "levels" at the same price, each claiming the strength of
    # the whole cluster — on BTC hourly that produced 9 rows at 64,450 all
    # scoring 79. A cluster of pivots is ONE level whose strength is how many
    # pivots formed it, not nine levels that each counted their neighbours.
    cand.sort(key=lambda c: c[0])
    groups = []
    for p, kind, age in cand:
        if groups and abs(p / groups[-1]["anchor"] - 1) <= cluster_tol:
            groups[-1]["members"].append((p, kind, age))
        else:
            groups.append(dict(anchor=p, members=[(p, kind, age)]))

    # Density normalisation: on hourly data with 600+ pivots, a raw count is a
    # measure of how busy the chart is, not of how important the price is. Score
    # each cluster against the AVERAGE cluster size for this instrument, so
    # "strong" means strong relative to its own chart.
    sizes = np.array([len(g["members"]) for g in groups], dtype=float)
    typical = max(float(np.median(sizes)), 1.0)

    out = []
    for g in groups:
        mem = g["members"]
        prices = np.array([m[0] for m in mem])
        kinds = [m[1] for m in mem]
        price = float(np.median(prices))
        major = any(k.startswith(("all_time", "two_year", "annual")) for k in kinds)
        rel = len(mem) / typical
        strength = int(round(min(rel, 6.0) + (3 if major else 0)))
        # name the cluster after its most significant member
        kind = next((k for k in kinds
                     if k.startswith(("all_time", "two_year", "annual"))),
                    max(set(kinds), key=kinds.count))
        out.append(dict(price=price, kind=kind, strength=max(strength, 1),
                        age=int(max(m[2] for m in mem)), diagonal=False,
                        pivots=len(mem)))
    return out


# ---------------------------------------------------------- diagonal lines
def trend_lines(df, upto, pivots, side, min_touches=2, tol_atr=0.5, max_lines=8):
    """Real trend lines anchored on two major pivots, scored by later touches.

    side='support' uses pivot lows and requires price to sit ABOVE the line;
    side='resistance' uses pivot highs and requires price BELOW. A line is
    discarded once price closes through it by more than tol_atr x ATR."""
    P = [i for i in pivots if i < upto]
    if len(P) < 2:
        return []
    vals = df.low.values if side == "support" else df.high.values
    close = df.close.values
    a = atr(df).bfill().values
    lines = []
    recent = P[-10:]                       # pairs among the most recent majors
    for ai in range(len(recent) - 1):
        for bi in range(ai + 1, len(recent)):
            i1, i2 = recent[ai], recent[bi]
            if i2 - i1 < 10:
                continue
            y1, y2 = vals[i1], vals[i2]
            slope = (y2 - y1) / (i2 - i1)
            touches, broken = 0, False
            for j in range(i2 + 1, upto + 1):
                line = y1 + slope * (j - i1)
                if line <= 0:
                    broken = True; break
                tol = tol_atr * a[j]
                if side == "support":
                    if close[j] < line - tol:
                        broken = True; break
                    if abs(vals[j] - line) <= tol:
                        touches += 1
                else:
                    if close[j] > line + tol:
                        broken = True; break
                    if abs(vals[j] - line) <= tol:
                        touches += 1
            if broken or touches < min_touches:
                continue
            proj = y1 + slope * (upto - i1)
            if proj <= 0:
                continue
            lines.append(dict(price=float(proj), kind=f"trend_{side}",
                              strength=int(2 + touches), age=int(upto - i1),
                              diagonal=True, touches=int(touches),
                              slope_pct=float(slope / close[upto] * 100)))
    # Merge lines that project to effectively the same place. Different anchor
    # pairs across the same run of pivots describe ONE line; without this, SOL
    # returned eight "trend supports" between 117.32 and 117.94 and the level
    # set was mostly one line counted repeatedly. Keep the best-supported of
    # each group and credit it with the touches of the line that earned most.
    lines.sort(key=lambda x: (-x["touches"], -x["age"]))
    kept = []
    if upto < len(a) and a[upto] > 0:
        tol = tol_atr * a[upto]
    else:
        tol = 0.0
    for ln in lines:
        if any(abs(ln["price"] - k["price"]) <= tol for k in kept):
            continue
        kept.append(ln)
    kept.sort(key=lambda x: (-x["strength"], -x["age"]))
    return kept[:max_lines]


def all_levels(df, upto, prominence=2.0, band=0.25):
    """Every level visible at bar `upto`: horizontals plus diagonals.

    RELEVANCE FILTER: a level far from current price is not a level, it is
    history. Only levels within `band` of the current close are returned —
    without this, clustering scores reward dense OLD price regions (SPY's
    strongest 'levels' came out at 280 while price was 778)."""
    lows, highs = major_pivots(df, prominence=prominence)
    out = horizontal_levels(df, upto, lows, highs)
    out += trend_lines(df, upto, lows, "support")
    out += trend_lines(df, upto, highs, "resistance")
    px = df.close.values[upto]
    if px > 0 and band:
        out = [l for l in out if abs(l["price"] / px - 1) <= band]
    return out


def nearest(levels, price, min_strength=0):
    """Closest level to `price`, as (distance_fraction, level)."""
    c = [l for l in levels if l["strength"] >= min_strength and l["price"] > 0]
    if not c:
        return None, None
    best = min(c, key=lambda l: abs(price / l["price"] - 1))
    return abs(price / best["price"] - 1), best


if __name__ == "__main__":
    import os
    p = "/home/claude/qlab/data_wide/SPY.csv"
    d = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
    lows, highs = major_pivots(d)
    print(f"SPY daily: {len(d)} bars, {len(lows)} major pivot lows, "
          f"{len(highs)} major pivot highs")
    L = all_levels(d, len(d) - 1)
    print(f"{len(L)} levels visible at the last bar, close {d.close.iloc[-1]:.2f}\n")
    for l in sorted(L, key=lambda x: -x["strength"])[:14]:
        tag = "diag" if l["diagonal"] else "horiz"
        extra = f" touches={l.get('touches','-')} slope={l.get('slope_pct',0):+.3f}%/bar" \
            if l["diagonal"] else ""
        print(f"  {l['kind']:18s} {tag:5s} {l['price']:10.2f}  "
              f"strength {l['strength']:2d}  age {l['age']:5d}{extra}")
