"""
CANDLESTICKS AS CONTEXT-GATED TRIGGERS, not standalone signals.

Doc 38 tested candles at fixed horizons on every bar and found nothing. That
test carried the same fault as the pattern test: a candle is not a signal, it is
a TRIGGER — a bar-level confirmation that the structure you were already
watching has turned. Nobody buys a hammer; they buy a hammer at the low of a
double bottom they were already tracking.

So the question is narrow and answerable:

    GIVEN a detected pattern with its own target and stop, does the SHAPE of the
    bar that completes it change the outcome?

Two places the candle could matter:
    pivot candle    the bar at the pattern's structural low (the second low of a
                    double bottom, the head of an inverse H&S, the last rising
                    low of a triangle) — is absorption visible there?
    breakout candle the bar that triggers entry — conviction or hesitation?

Scored exactly as patterns_proper scores everything: did the pattern's own
target arrive before its own stop, in R, using its own reward:risk. The
comparison is WITHIN the pattern set, so there is no control to construct — the
ungated pattern population IS the control, and any candle gate must beat it.

A gate that merely shrinks the sample without improving expectancy is not a
filter, it is a smaller bet.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
from levels_general import load_universe

PATTERNS = [PP.d_double_bottom, PP.d_inv_hs, PP.d_asc_triangle]


def bar_shape(df, i):
    """Everything about one candle, normalised so it compares across assets."""
    o, h, l, c = (df.open.values[i], df.high.values[i],
                  df.low.values[i], df.close.values[i])
    rng = h - l
    if rng <= 0 or not np.isfinite(rng):
        return None
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return dict(
        pos=(c - l) / rng,              # where it closed in its range
        body_frac=body / rng,
        upper_frac=upper / rng,
        lower_frac=lower / rng,
        green=float(c > o),
        hammer=float(lower > 2 * body and upper < 0.3 * rng),
        shooting=float(upper > 2 * body and lower < 0.3 * rng),
        marubozu=float(body / rng > 0.9),
        doji=float(body / rng < 0.05),
    )


def pivot_bar(df, g):
    """The bar carrying the pattern's structural low — the one its stop sits on."""
    L = df.low.values
    lo = g["stop"]
    w = range(max(0, g["bar"] - 200), g["bar"] + 1)
    best, bd = None, np.inf
    for j in w:
        d = abs(L[j] - lo)
        if d < bd:
            bd, best = d, j
    return best


def collect(which):
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        for det in PATTERNS:
            try:
                sigs = det(df, lows, highs)
            except Exception:
                continue
            for g in sigs:
                r = PP.resolve(df, g["bar"], g["entry"], g["stop"], g["target"])
                if not r:
                    continue
                pb = pivot_bar(df, g)
                ps = bar_shape(df, pb) if pb is not None else None
                bs = bar_shape(df, g["bar"])
                if ps is None or bs is None:
                    continue
                row = dict(sym=s, name=g["name"], rr=r["rr"], win=r["win"],
                           resolved=r["resolved"],
                           R=(0.0 if r["resolved"] == 0
                              else (r["rr"] if r["win"] == 1 else -1.0)))
                for k, v in ps.items():
                    row[f"p_{k}"] = v
                for k, v in bs.items():
                    row[f"b_{k}"] = v
                rows.append(row)
    return pd.DataFrame(rows)


def line(lab, T, base=None, pad=34):
    if len(T) < 60:
        print(f"  {lab:{pad}s} n={len(T):5d}  too few"); return None
    r = T.R.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    hit = T[T.resolved == 1].win.mean()
    d = f"  vs all {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  hit {hit*100:5.1f}%  "
          f"R:R {T.rr.mean():4.2f}  {r.mean():+6.3f}R  t={r.mean()/se:+5.2f}{d}")
    return r.mean()


def run(which):
    T = collect(which)
    print("=" * 104)
    print(f"  {which.upper()}   n={len(T)} patterns with both candles measured")
    print("=" * 104)
    if len(T) < 300:
        print("  too few\n"); return
    base = line("ALL patterns (the control)", T)
    print("\n  THE PIVOT CANDLE — the bar at the pattern's structural low")
    for lab, m in (("hammer at the low", T.p_hammer == 1),
                   ("doji at the low", T.p_doji == 1),
                   ("marubozu at the low", T.p_marubozu == 1),
                   ("green at the low", T.p_green == 1),
                   ("closed top 1/3 of range", T.p_pos > 0.67),
                   ("closed bottom 1/3 of range", T.p_pos < 0.33),
                   ("long lower wick (>40%)", T.p_lower_frac > 0.4)):
        line(f"    {lab}", T[m], base)
    print("\n  THE BREAKOUT CANDLE — the bar that triggers entry")
    for lab, m in (("marubozu breakout", T.b_marubozu == 1),
                   ("doji breakout", T.b_doji == 1),
                   ("shooting star breakout", T.b_shooting == 1),
                   ("closed top 1/3 of range", T.b_pos > 0.67),
                   ("closed bottom 1/3 of range", T.b_pos < 0.33),
                   ("big body (>60% of range)", T.b_body_frac > 0.6),
                   ("small body (<25% of range)", T.b_body_frac < 0.25),
                   ("long upper wick (>40%)", T.b_upper_frac > 0.4)):
        line(f"    {lab}", T[m], base)
    print("\n  COMBINED — absorption at the low AND conviction on the break")
    line("    lower wick low + strong close",
         T[(T.p_lower_frac > 0.4) & (T.b_pos > 0.67)], base)
    line("    weak low + strong close",
         T[(T.p_pos < 0.33) & (T.b_pos > 0.67)], base)
    print()
    return T


if __name__ == "__main__":
    print("CANDLES AS TRIGGERS INSIDE PATTERNS — scored on the pattern's own target\n")
    print("The ungated pattern population is the control. A gate must BEAT it,")
    print("not merely shrink it.\n")
    out = {}
    for u in ("crypto_hourly", "crypto_daily"):
        out[u] = run(u)
