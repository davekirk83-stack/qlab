"""
READING THE CROSS-TIMEFRAME LIBRARY SWEEP WITHOUT FOOLING OURSELVES.

The raw ICs rise sharply with bar size - at 1D the best element reads -0.21
against -0.05 at 1h. That is NOT four times the predictive power. Two things
inflate IC as the timeframe lengthens and neither is edge:

  1. OVERLAPPING WINDOWS. A 20-bar forward return at consecutive bars shares
     19/20 of its path. The observations are not independent, and the longer
     the bar the fewer genuinely independent windows exist in a fixed calendar
     span. At 1D over one year there are ~18 independent 20-day windows per
     symbol; at 1h there are ~430.
  2. NOISE RATIO. Coarser bars average away microstructure noise, which lifts
     rank correlation without the signal changing.

So IC is reported but is NOT the ranking statistic. The ranking statistic is
the per-symbol t, which already accounts for how many symbols independently
agree, alongside:
    agree/total   how many symbols carry the same sign
    stable        same sign in the first and second half of the sample
    n_eff         calendar span / horizon length: the number of genuinely
                  independent forward windows available per symbol

An element is only called "better at timeframe X" if t and symbol agreement
rise together, not if IC alone does.
"""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd

ORDER = ["15min", "30min", "1h", "2h", "4h", "8h", "1D"]
MINS = dict(zip(ORDER, [15, 30, 60, 120, 240, 480, 1440]))
HORIZON = 20
SPAN_DAYS = 394   # data_1m span, 2025-09-01 -> 2026-09-30


def load():
    fr = []
    for tf in ORDER:
        p = f"/home/claude/qlab/runs/libtf_{tf}.csv"
        if os.path.exists(p):
            fr.append(pd.read_csv(p))
    if not fr: return None
    T = pd.concat(fr, ignore_index=True)
    T["n_eff"] = SPAN_DAYS * 1440 / (MINS.get("1h", 60) * 0)  if False else \
                 SPAN_DAYS * 1440 / (T.tf.map(MINS) * HORIZON)
    return T


if __name__ == "__main__":
    T = load()
    if T is None: raise SystemExit("no results yet")
    done = [tf for tf in ORDER if tf in set(T.tf)]
    print(f"CROSS-TIMEFRAME LIBRARY SWEEP — {len(done)} timeframes complete: "
          f"{', '.join(done)}")
    print(f"{T.name.nunique()} distinct elements\n")

    print("HOW MANY INDEPENDENT FORWARD WINDOWS EACH TIMEFRAME ACTUALLY HAS")
    print("(calendar span / 20-bar horizon, per symbol — this is why raw IC rises)")
    print(f"  {'tf':>7}{'horizon':>12}{'n_eff/sym':>11}{'symbols':>9}"
          f"{'median |IC|':>13}{'median |t|':>12}")
    for tf in done:
        g = T[T.tf == tf]
        hrs = MINS[tf] * HORIZON / 60
        hz = f"{hrs:.0f}h" if hrs < 48 else f"{hrs/24:.0f}d"
        print(f"  {tf:>7}{hz:>12}{g.n_eff.iloc[0]:>11.0f}{g.nsym.iloc[0]:>9}"
              f"{g.ic.abs().median():>13.4f}{g.t.abs().median():>12.2f}")

    print(f"\n{'='*104}")
    print("BEST TIMEFRAME FOR EACH ELEMENT, ranked by |t| — the honest ranking")
    print("Only elements whose best cell has |t|>=4 and >=70% of symbols agreeing.")
    print(f"  {'element':<22}{'family':<14}{'best tf':>8}{'IC':>9}{'t':>8}"
          f"{'agree':>8}{'stable':>7}{'1h IC':>9}{'1h t':>8}{'moved':>7}")
    rows = []
    for name, g in T.groupby("name"):
        g = g.dropna(subset=["t"])
        if g.empty: continue
        b = g.loc[g.t.abs().idxmax()]
        if abs(b.t) < 4 or b.agree / b.total < 0.70: continue
        h = g[g.tf == "1h"]
        h_ic = float(h.ic.iloc[0]) if len(h) else np.nan
        h_t = float(h.t.iloc[0]) if len(h) else np.nan
        moved = b.tf != "1h"
        rows.append(dict(name=name, family=b.family, tf=b.tf, ic=b.ic, t=b.t,
                         agree=f"{int(b.agree)}/{int(b.total)}", stable=int(b.stable),
                         h_ic=h_ic, h_t=h_t, moved=moved,
                         gain=abs(b.t) - (abs(h_t) if np.isfinite(h_t) else 0)))
    R = pd.DataFrame(rows).sort_values("t", key=abs, ascending=False)
    for _, r in R.head(30).iterrows():
        print(f"  {r['name']:<22}{r['family']:<14}{r['tf']:>8}{r['ic']:>+9.4f}"
              f"{r['t']:>+8.2f}{r['agree']:>8}{r['stable']:>7}"
              f"{r['h_ic']:>+9.4f}{r['h_t']:>+8.2f}{'YES' if r['moved'] else '-':>7}")

    print(f"\n{'='*104}\nTHE HEADLINE NUMBERS")
    print(f"  elements clearing |t|>=4 with >=70% symbol agreement at SOME timeframe: {len(R)}")
    print(f"  of those, best at a timeframe OTHER than the hourly we always used: "
          f"{int(R.moved.sum())}  ({R.moved.mean()*100:.0f}%)")
    print("\n  where each element's best timeframe actually is:")
    for tf in done:
        k = (R.tf == tf).sum()
        if k: print(f"    {tf:>7}  {k:>3} elements  {'#'*k}")

    big = R[R.gain > 2].sort_values("gain", ascending=False)
    print(f"\n  ELEMENTS WE MATERIALLY UNDERRATED AT 1h (|t| gain > 2):  {len(big)}")
    if len(big):
        print(f"    {'element':<22}{'best tf':>8}{'t there':>9}{'t at 1h':>9}{'gain':>7}")
        for _, r in big.head(18).iterrows():
            print(f"    {r['name']:<22}{r['tf']:>8}{r['t']:>+9.2f}{r['h_t']:>+9.2f}"
                  f"{r['gain']:>+7.2f}")

    print(f"\n{'='*104}\nBY FAMILY — does a whole family prefer a timeframe?")
    print(f"  {'family':<16}{'n':>4}  best-timeframe distribution")
    for fam, g in R.groupby("family"):
        d = g.tf.value_counts()
        s = "  ".join(f"{k}:{v}" for k, v in d.items())
        print(f"  {fam:<16}{len(g):>4}  {s}")
    R.to_csv("/home/claude/qlab/runs/libtf_best.csv", index=False)
    print("\n  -> runs/libtf_best.csv")
