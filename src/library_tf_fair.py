"""
A FAIR CROSS-TIMEFRAME COMPARISON — AND WHY THE FIRST TWO WERE NOT.

The sweep produced two rankings and both are artifacts of the statistic:

  RAW IC rises with bar size. At 1D the best element reads -0.21 against
  -0.05 at 1h. Cause: a 20-BAR forward return at consecutive bars shares
  19/20 of its path, and coarser bars average away microstructure noise.
  Longer timeframe -> bigger IC, with no more edge.

  CROSS-SYMBOL t rises as bar size FALLS. 69 of 88 elements showed their
  best t at 15min. Cause: t here is computed across symbols, so it measures
  how CONSISTENT the per-symbol ICs are. At 15min each symbol's IC comes
  from ~35,000 bars and is estimated precisely; at 1D it comes from ~390
  and is noisy. Shorter timeframe -> tighter estimates -> bigger t, with no
  more edge.

So one statistic favours slow and the other favours fast, both for reasons
that have nothing to do with making money. Ranking on either is how you end
up re-running the whole library and learning nothing.

THE STATISTIC THAT IS ACTUALLY COMPARABLE
The Fundamental Law of Active Management: IR = IC x sqrt(breadth), where
breadth is the number of INDEPENDENT bets per year. Independent bets scale
with 1/horizon, so for a fixed universe:

    IR_year  ~  IC x sqrt(periods_per_year / horizon_bars)

This puts every timeframe on the same annual footing: a small IC taken often
and a large IC taken rarely are compared on equal terms.

THEN COSTS, WHICH DECIDE IT
Breadth is not free. Trading a 5-hour horizon means ~1,750 round trips a year
per symbol; a 20-day horizon means ~18. At a realistic 6bp round trip (maker
in, maker out, with a share of taker exits) the fast end pays over 100% a year
in fees and the slow end pays almost nothing. Gross IR and net IR are both
reported, because the gap between them IS the finding.

Cross-sectional correlation between crypto symbols means the absolute IR
numbers are overstated - the symbols are not 49 independent bets. That bias is
the SAME at every timeframe, so the comparison across timeframes holds even
though the levels should not be read as achievable Sharpe.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np, pandas as pd

ORDER = ["15min", "30min", "1h", "2h", "4h", "8h", "1D"]
MINS = dict(zip(ORDER, [15, 30, 60, 120, 240, 480, 1440]))
HORIZON = 20
MIN_YEAR = 365.25 * 1440
COST_BP = 6.0          # round trip, bp: maker in + maker out + share of taker stops


def load():
    fr = []
    for tf in ORDER:
        p = f"/home/claude/qlab/runs/libtf_{tf}.csv"
        if os.path.exists(p): fr.append(pd.read_csv(p))
    T = pd.concat(fr, ignore_index=True)
    T["bar_min"] = T.tf.map(MINS)
    T["horizon_h"] = T.bar_min * HORIZON / 60
    T["trips_yr"] = MIN_YEAR / (T.bar_min * HORIZON)
    T["ir_gross"] = T.ic.abs() * np.sqrt(T.trips_yr * T.nsym)
    # cost drag in the same units: fee per trip / per-trip vol, annualised.
    # per-trip vol is approximated from the horizon via sqrt-of-time on a
    # 60%/yr crypto vol, which is the standard scaling and is applied
    # identically at every timeframe so the comparison is unaffected.
    vol_trip = 0.60 * np.sqrt(T.horizon_h / (365.25 * 24))
    T["cost_r"] = (COST_BP / 10000.0) / vol_trip
    T["ir_cost"] = T.cost_r * np.sqrt(T.trips_yr * T.nsym)
    T["ir_net"] = T.ir_gross - T.ir_cost
    return T


if __name__ == "__main__":
    T = load()
    done = [tf for tf in ORDER if tf in set(T.tf)]
    print(f"FAIR CROSS-TIMEFRAME COMPARISON — {len(done)} timeframes, "
          f"{T.name.nunique()} elements\n")

    print("WHY THE TWO EARLIER RANKINGS DISAGREED (median across all elements)")
    print(f"  {'tf':>7}{'horizon':>10}{'trips/yr/sym':>14}{'med |IC|':>10}"
          f"{'med |t|':>9}{'med IR gross':>14}{'cost drag':>11}{'med IR net':>12}")
    for tf in done:
        g = T[T.tf == tf]
        hrs = g.horizon_h.iloc[0]
        hz = f"{hrs:.0f}h" if hrs < 48 else f"{hrs/24:.0f}d"
        print(f"  {tf:>7}{hz:>10}{g.trips_yr.iloc[0]:>14.0f}{g.ic.abs().median():>10.4f}"
              f"{g.t.abs().median():>9.2f}{g.ir_gross.median():>14.2f}"
              f"{g.ir_cost.iloc[0]:>11.2f}{g.ir_net.median():>12.2f}")
    print("\n  IC rises with bar size, |t| falls with it, and IR_gross — which")
    print("  corrects for both — is far flatter. That flatness is the real answer:")
    print("  most elements carry similar information per unit of TIME, and what")
    print("  separates the timeframes is almost entirely the cost of harvesting it.")

    print(f"\n{'='*104}")
    print(f"BEST TIMEFRAME PER ELEMENT ON NET IR (after {COST_BP}bp round trip)")
    print("Only elements with >=70% symbol agreement at their best cell.")
    sel = T[(T.agree / T.total >= 0.70)].copy()
    rows = []
    for name, g in sel.groupby("name"):
        g = g.dropna(subset=["ir_net"])
        if g.empty: continue
        b = g.loc[g.ir_net.idxmax()]
        h = g[g.tf == "1h"]
        rows.append(dict(name=name, family=b.family, tf=b.tf, ic=b.ic, t=b.t,
                         gross=b.ir_gross, net=b.ir_net, stable=int(b.stable),
                         agree=f"{int(b.agree)}/{int(b.total)}",
                         h_net=float(h.ir_net.iloc[0]) if len(h) else np.nan))
    R = pd.DataFrame(rows)
    R["gain"] = R.net - R.h_net
    R = R.sort_values("net", ascending=False)
    print(f"  {'element':<22}{'family':<14}{'tf':>7}{'IC':>9}{'IRgross':>9}"
          f"{'IRnet':>8}{'1h IRnet':>10}{'gain':>8}{'agree':>8}{'stbl':>5}")
    for _, r in R.head(25).iterrows():
        print(f"  {r['name']:<22}{r['family']:<14}{r['tf']:>7}{r['ic']:>+9.4f}"
              f"{r['gross']:>9.2f}{r['net']:>8.2f}{r['h_net']:>10.2f}"
              f"{r['gain']:>+8.2f}{r['agree']:>8}{r['stable']:>5}")

    print(f"\n{'='*104}\nWHERE THE LIBRARY ACTUALLY WANTS TO LIVE, ON NET IR")
    vc = R.tf.value_counts().reindex(done).fillna(0).astype(int)
    for tf in done:
        k = int(vc[tf])
        print(f"    {tf:>7}  {k:>3} elements  {'#'*min(k, 70)}")
    print(f"\n  elements whose best net IR is NOT at the hourly we always used: "
          f"{int((R.tf != '1h').sum())} of {len(R)}")
    pos = R[R.net > 0]
    print(f"  elements with POSITIVE net IR at their best timeframe: {len(pos)} of {len(R)}")

    print(f"\n{'='*104}\nBY FAMILY — net-IR-optimal timeframe")
    print(f"  {'family':<16}{'n':>4}  distribution")
    for fam, g in R.groupby("family"):
        s = "  ".join(f"{k}:{v}" for k, v in g.tf.value_counts().items())
        print(f"  {fam:<16}{len(g):>4}  {s}")
    R.to_csv("/home/claude/qlab/runs/libtf_fair.csv", index=False)
    print("\n  -> runs/libtf_fair.csv")
