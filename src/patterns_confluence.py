"""
CONFLUENCE — the claim I never actually tested.

The chartist claim was never "a double bottom anywhere works". It is "a double
bottom AT A LEVEL, IN A TREND, ON VOLUME works". The first test measured the
strawman. patterns_proper.py fixed the detection and the targets; this fixes the
context.

Built on patterns_proper's detectors and its own-target scoring, so the only
thing changing is the GATE.

GATES
  level     the pattern's stop (the structural low it is built on) sits within
            0.5 ATR of a horizontal level visible beforehand  -> structure.py
  trend     price above its 200-bar average at the breakout
  volume    breakout bar volume > 1.5x its 20-bar average
  wide_rr   the pattern's own reward:risk is at least 1.5

Every gate is also applied to the CONTROL, so a gate that merely selects
favourable market conditions shows up as a control that improves too. That is
the trap: "trades at a level in an uptrend did well" is usually a statement
about uptrends.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
from levels_general import load_universe

RNG = np.random.default_rng(555)


def context(df):
    """Per-bar context arrays, all trailing-only."""
    a = ST.atr(df).bfill().values
    ma = df.close.rolling(200).mean().values
    if "volume" in df.columns:
        v = df.volume.replace(0, np.nan)
        vr = (v / v.rolling(20).mean()).fillna(1.0).values
    else:
        vr = np.ones(len(df))
    return a, ma, vr


def level_near(df, bar, price, a_bar, tol=0.5):
    """Is `price` within tol x ATR of a horizontal level visible at `bar`?"""
    try:
        lv = ST.all_levels(df, bar)
    except Exception:
        return False
    if not lv or a_bar <= 0:
        return False
    for l in lv:
        if l["diagonal"]:
            continue
        if abs(l["price"] - price) <= tol * a_bar:
            return True
    return False


def enrich(df, recs, sigs, a, ma, vr, do_level):
    """Attach gate flags to each scored record."""
    C = df.close.values
    out = []
    for r, g in zip(recs, sigs):
        b = g["bar"]
        r = dict(r)
        r["trend"] = bool(np.isfinite(ma[b]) and C[b] > ma[b])
        r["volume"] = bool(vr[b] > 1.5)
        r["wide_rr"] = bool(r["rr"] >= 1.5)
        r["level"] = level_near(df, b, g["stop"], a[b]) if do_level else False
        out.append(r)
    return out


def run(which, do_level=True, cap=None):
    panel = load_universe(which)
    if cap:
        panel = dict(list(panel.items())[:cap])
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 500:
            continue
        try:
            lows, highs = PP.confirmed_pivots(df)
        except Exception:
            continue
        if len(lows) < 4 or len(highs) < 4:
            continue
        a, ma, vr = context(df)
        sigs = []
        for det in PP.DETECTORS:
            try:
                sigs += det(df, lows, highs)
            except Exception:
                continue
        recs, keep = [], []
        for g in sigs:
            r = PP.resolve(df, g["bar"], g["entry"], g["stop"], g["target"])
            if r:
                r["name"] = g["name"]; recs.append(r); keep.append(g)
        if not keep:
            continue
        real += enrich(df, recs, keep, a, ma, vr, do_level)
        # control: random entries, same R:R, same gates evaluated at THEIR bar
        cs = PP.control_for(df, keep, len(keep))
        cb = RNG.choice(np.arange(150, max(151, len(df) - PP.MAXBARS - 2)),
                        size=len(cs), replace=True)
        fake_sigs = [dict(bar=int(b), stop=df.close.values[int(b)] * 0.98,
                          name=c["name"]) for b, c in zip(cb, cs)]
        ctrl += enrich(df, cs, fake_sigs, a, ma, vr, do_level)
    return pd.DataFrame(real), pd.DataFrame(ctrl)


def show(lab, A, B, pad=30):
    if len(A) < 60:
        print(f"  {lab:{pad}s} n={len(A):5d}  too few"); return
    ra, rb = PP.expectancy(A), PP.expectancy(B) if len(B) else np.array([np.nan])
    sa = ra.std(ddof=1) / np.sqrt(len(ra))
    hit = A[A.resolved == 1].win.mean()
    edge = ra.mean() - rb.mean() if len(B) >= 60 else np.nan
    print(f"  {lab:{pad}s} n={len(ra):5d}  hit {hit*100:5.1f}%  "
          f"R:R {A.rr.mean():4.2f}  exp {ra.mean():+6.3f}R  t={ra.mean()/sa:+5.2f}  "
          f"ctrl {rb.mean():+6.3f}R  EDGE {edge:+6.3f}R")


if __name__ == "__main__":
    print("CONFLUENCE — do the gates actually add anything?")
    print("Gates applied to the CONTROL too, so a gate that merely picks good")
    print("market conditions shows up as a control that improves as well.\n")
    for u in ("crypto_hourly", "crypto_daily", "etf"):
        A, B = run(u)
        print("=" * 108)
        print(f"  {u.upper()}   (real n={len(A)})")
        print("=" * 108)
        show("ungated", A, B)
        print()
        for g in ("level", "trend", "volume", "wide_rr"):
            if g in A.columns:
                show(f"  {g}", A[A[g]], B[B[g]] if g in B.columns else B)
        print()
        if {"level", "trend"} <= set(A.columns):
            show("  level + trend", A[A.level & A.trend], B[B.level & B.trend])
            show("  level + trend + volume",
                 A[A.level & A.trend & A.volume], B[B.level & B.trend & B.volume])
        print()
        print("  best pattern x gate:")
        for nm in sorted(A.name.unique()):
            sa = A[A.name == nm]; sb = B[B.name == nm] if len(B) else B
            show(f"    {nm} @level", sa[sa.level], sb[sb.level] if len(sb) else sb)
        print()
