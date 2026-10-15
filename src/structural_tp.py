"""
STRUCTURAL TAKE-PROFITS vs ARBITRARY R-MULTIPLES.

DK's original instruction, which I drifted away from: targets should sit on
fib and structural levels, not at arbitrary R-multiples. Spec v1 honoured it
(TP2 = 1.618 fib extension). Run 15 swapped it for a flat 3R because
R-multiples are easy to sweep, and every run since inherited that silently.

It matters more now than it did. The barrier-race test showed the entry edge
lives at ~3 ATR and is NEGATIVE at 1 ATR, so target placement is the live
question — and answering it with numbers I chose is precisely the wrong method.

A structural target is a price other people are watching: a prior high, a fib
extension of the move, a round number. There is a real mechanism for why price
reacts there (resting orders), which an R-multiple has no claim to.

Candidate target schemes, all applied to the SAME entries and the SAME stop,
so only the target differs:

  R-MULTIPLE (control)   TP at k x risk
  FIB EXTENSION          retrace leg measured, target at 1.272 / 1.618 / 2.618
  PRIOR SWING HIGH       the next untouched swing high above entry
  PRIOR PERIOD HIGH      prior week / month / quarter high above entry
  MEASURED MOVE          height of the consolidation projected from the break
  ROUND NUMBER           next psychological level (whole/half units by price scale)
  ATR MULTIPLE           target at k x ATR (the barrier-race geometry)

Judged on expectancy per trade AND on how often the target is actually reached,
because a target that never fills is just a time stop wearing a hat.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
import levels as LV
import patterns as P
from run10 import atr
import wide_test as W

PANEL = W.PANEL
ETF = set(W.CLASS.keys())
MAXBARS = 15
SLIP = 0.0005


# ------------------------------------------------------------ target finders
def swing_highs(df, n=5):
    """Pivot highs: a high with n lower highs each side."""
    h = df.high
    piv = (h == h.rolling(2 * n + 1, center=True).max())
    return piv.fillna(False).values


def next_swing_high(H, piv, i, px, lookback=120):
    """Nearest pivot high ABOVE the entry, searching back from the signal."""
    best = None
    for j in range(max(0, i - lookback), i + 1):
        if piv[j] and H[j] > px:
            if best is None or H[j] < best:
                best = H[j]
    return best


def round_level(px):
    """Next round number above, scaled to the price magnitude."""
    if px <= 0:
        return None
    mag = 10 ** np.floor(np.log10(px))
    step = mag / 2
    return float(np.ceil(px / step) * step)


def fib_ext(df, i, px, k):
    """Fib extension of the most recent measurable swing below the entry."""
    lo = df.low.iloc[max(0, i - 50):i + 1].min()
    hi = df.high.iloc[max(0, i - 50):i + 1].max()
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return None
    return float(lo + (hi - lo) * k)


def measured_move(df, i, px):
    """Height of the 20-bar consolidation projected up from the break."""
    w = df.iloc[max(0, i - 20):i + 1]
    h = w.high.max() - w.low.min()
    if not np.isfinite(h) or h <= 0:
        return None
    return float(px + h)


def period_high(df, i, px, bars):
    w = df.high.iloc[max(0, i - bars):i + 1]
    v = w.max()
    return float(v) if np.isfinite(v) and v > px else None


# ------------------------------------------------------------------ the test
def run(df, entries, cost, target_fn, stop_atr=1.5, maxbars=MAXBARS):
    """One target, one stop, no scale-out — so the TARGET is the only variable."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    piv = swing_highs(df)
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
    for i in idx:
        if i <= last or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        px = O[i + 1] * (1 + SLIP)
        if not (px == px) or px <= 0:
            continue
        stop = px - stop_atr * a
        risk = px - stop
        if risk <= 0 or risk / px < 2 * cost:
            continue
        tgt = target_fn(df, H, piv, i, px, a, risk)
        if tgt is None or not np.isfinite(tgt) or tgt <= px:
            continue
        ex, pnl, how = None, 0.0, None
        for j in range(i + 1, min(i + 1 + maxbars, len(df))):
            if L[j] <= stop:
                fill = min(stop, O[j]) * (1 - SLIP)
                pnl = fill / px - 1; ex = j; how = "stop"; break
            if H[j] >= tgt:
                pnl = tgt * (1 - SLIP) / px - 1; ex = j; how = "target"; break
        if ex is None:
            j = min(i + maxbars, len(df) - 1)
            pnl = Cl[j] * (1 - SLIP) / px - 1; ex = j; how = "time"
        out.append(dict(R=(pnl - cost) * px / risk, how=how, bars=ex - i,
                        dist=(tgt - px) / a))
        last = ex
    return out


TARGETS = {
    "R-mult 1.0R (control)":  lambda d, H, p, i, px, a, r: px + 1.0 * r,
    "R-mult 3.0R (control)":  lambda d, H, p, i, px, a, r: px + 3.0 * r,
    "ATR 3.0 (barrier geom)": lambda d, H, p, i, px, a, r: px + 3.0 * a,
    "fib 1.272 ext":          lambda d, H, p, i, px, a, r: fib_ext(d, i, px, 1.272),
    "fib 1.618 ext":          lambda d, H, p, i, px, a, r: fib_ext(d, i, px, 1.618),
    "fib 2.618 ext":          lambda d, H, p, i, px, a, r: fib_ext(d, i, px, 2.618),
    "next swing high":        lambda d, H, p, i, px, a, r: next_swing_high(H, p, i, px),
    "prior month high":       lambda d, H, p, i, px, a, r: period_high(d, i, px, 21),
    "prior quarter high":     lambda d, H, p, i, px, a, r: period_high(d, i, px, 63),
    "measured move":          lambda d, H, p, i, px, a, r: measured_move(d, i, px),
    "next round number":      lambda d, H, p, i, px, a, r: round_level(px),
}

ENTRIES = {
    "month-high break": lambda d: LV.l_break_prior_month_high(d),
    "flag":             lambda d: P.p_flag(d, 2.0, 10, 5, 0.5),
}


def main():
    print("STRUCTURAL TAKE-PROFITS vs ARBITRARY R-MULTIPLES\n")
    print(f"  {len(ETF & set(PANEL))} survivorship-clean ETFs · single target, no scale-out")
    print(f"  stop fixed at 1.5 ATR, {MAXBARS}-bar limit, 5bp slippage, gap-through stops")
    print("  only the TARGET varies\n")

    for ename, efn in ENTRIES.items():
        print("=" * 112)
        print(f"  ENTRY: {ename}")
        print("=" * 112)
        print(f"  {'target scheme':24s} {'n':>6} {'meanR':>8} {'hit%':>7} {'median dist':>12} "
              f"{'bars':>6} {'t':>7}")
        res = []
        for tname, tfn in TARGETS.items():
            rows = []
            for s, df in PANEL.items():
                if s not in ETF or len(df) < 300:
                    continue
                try:
                    e = efn(df)
                    e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
                except Exception:
                    continue
                if e.sum() == 0:
                    continue
                rows += run(df, e, W.COSTS[s], tfn)
            if len(rows) < 200:
                continue
            t = pd.DataFrame(rows)
            m, se = t.R.mean(), t.R.std() / np.sqrt(len(t))
            hit = float((t.how == "target").mean())
            res.append(dict(name=tname, n=len(t), m=m, hit=hit,
                            dist=t.dist.median(), bars=t.bars.mean(),
                            tstat=m / se if se > 0 else 0))
            print(f"  {tname:24s} {len(t):6d} {m:+8.3f} {hit*100:6.1f}% "
                  f"{t.dist.median():11.2f}A {t.bars.mean():6.1f} {m/se if se>0 else 0:+7.2f}")
        if res:
            best = max(res, key=lambda x: x["m"])
            ctrl = [x for x in res if "3.0R" in x["name"]]
            print(f"\n  BEST: {best['name']} at {best['m']:+.3f}R")
            if ctrl:
                print(f"  vs the arbitrary 3R control: {best['m']-ctrl[0]['m']:+.3f}R")
        print()

    C.ledger_bump(len(TARGETS) * len(ENTRIES), "structural vs R-multiple targets")


if __name__ == "__main__":
    main()
