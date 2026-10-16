"""
DOES ANY OF IT SURVIVE A DIFFERENT MARKET? — the book across five years.

Everything registered so far rests on thirteen months, September 2025 to
September 2026. That is one regime. A mean-reversion book is exactly the kind
of thing that works beautifully in a chop and dies in a trend, so a single
regime is the weakest possible evidence for it.

The new 15-minute panel reaches back to October 2021 and therefore covers:

  2021 Q4   the top of the last cycle - violent, trending, euphoric
  2022      the collapse - LUNA in May, FTX in November, sustained downtrend
  2023      the grind - low volatility, range-bound, the book's ideal
  2024-25   recovery and the new cycle
  2025-26   the period everything was fitted on

If the book earns its return only in 2023 and loses through 2022, it is a
chop strategy with a flattering sample, and the honest description changes
from "24.8% a year" to "works in a third of market conditions". If it holds
up through the collapse, that is the strongest evidence yet obtained.

NO DEPTH DATA exists before the collection period, so the queue and chase
models cannot run here. This uses the optimistic fill throughout - which doc
120 showed is only about three points of CAGR above a chased book, and doc
122 showed the premium barely matters. The LEVEL is therefore slightly
flattered; the COMPARISON ACROSS YEARS, which is the whole point, is not
affected at all because every year is treated identically.

Reported per calendar year, and per market regime defined causally from the
equal-weight index's own 200-bar trend, so a reader can see whether the book
depends on the market going up - which doc 117 suggested it does.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD


def load5():
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_15m/*USD.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if len(d) > 60_000: out[s] = d
    return out


if __name__ == "__main__":
    data = load5()
    print(f"{len(data)} symbols with long histories.")
    if not data:
        raise SystemExit("no five-year files yet")
    span = min(d.index[0] for d in data.values())
    print(f"earliest bar {str(span)[:10]}, latest "
          f"{str(max(d.index[-1] for d in data.values()))[:10]}\n")
    for s, d in sorted(data.items()):
        print(f"  {s:<12}{len(d):>8,} bars  from {str(d.index[0])[:10]}")

    rows = []
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        al = (v > v.expanding(500).median()).values
        rows += CP.episodes(d, al, ema, lo_b, hi_b, a, None, "optimistic", "L", s)
        rows += CP.episodes(d, al, ema, lo_b, hi_b, a, None, "optimistic", "S", s)
    S = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"])
    S = S[np.isfinite(S.ret)]
    print(f"\n{len(S):,} episodes.\n")

    print("="*92)
    print("BY CALENDAR YEAR — optimistic fills, both sides, 40 slots, 1x")
    print("="*92)
    print(f"  {'year':<8}{'episodes':>10}{'per ep':>10}{'win':>7}{'worst ep':>11}"
          f"{'CAGR':>10}{'maxDD':>9}{'Sharpe':>8}")
    S["yr"] = pd.to_datetime(S.entry).dt.year
    for y in sorted(S.yr.unique()):
        g = S[S.yr == y].copy()
        if len(g) < 200: continue
        r, _, _ = CP.simulate(g, 40, 1)
        if r is None:
            print(f"  {y:<8}{len(g):>10,}  WIPED OUT"); continue
        print(f"  {y:<8}{len(g):>10,}{g.ret.mean()*100:>+9.4f}%"
              f"{(g.ret>0).mean()*100:>6.0f}%{g.ret.min()*100:>+10.1f}%"
              f"{r['cagr']*100:>9.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}")

    print("\n" + "="*92)
    print("BY MARKET REGIME — equal-weight index vs its own 200-bar trend")
    print("="*92)
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
    trend = idx.pct_change(200)
    reg = pd.Series(np.where(trend > 0.05, "rising",
                    np.where(trend < -0.05, "falling", "flat")), index=idx.index)
    reg = reg.shift(1)                       # causal: yesterday's reading
    S["reg"] = reg.reindex(pd.to_datetime(S.entry), method="ffill").values
    print(f"  {'regime':<12}{'episodes':>10}{'per ep':>10}{'win':>7}"
          f"{'worst ep':>11}{'total':>11}")
    for k in ("rising", "flat", "falling"):
        g = S[S.reg == k]
        if len(g) < 100: continue
        print(f"  {k:<12}{len(g):>10,}{g.ret.mean()*100:>+9.4f}%"
              f"{(g.ret>0).mean()*100:>6.0f}%{g.ret.min()*100:>+10.1f}%"
              f"{g.ret.sum()*100:>+10.0f}%")
    print("\n  Doc 117 found the book's best days come when the market has been")
    print("  rising. If 'falling' is negative here across five years, the market")
    print("  gate is not an optimisation — it is a requirement.")

    print("\n" + "="*92)
    print("THE WHOLE PERIOD")
    print("="*92)
    for lev in (1, 3):
        r, tk, sk = CP.simulate(S, 40, lev)
        if r is None:
            print(f"  {lev}x: WIPED OUT"); continue
        print(f"  {lev}x — CAGR {r['cagr']*100:>6.1f}%   maxDD {r['dd']*100:>6.1f}%"
              f"   Sharpe {r['sharpe']:>5.2f}   over {r['yrs']:.1f} years   "
              f"$2,000 -> ${r['final']:,.0f}")
    print(f"\n  13-month fitted sample gave 27.6% CAGR at 1x on optimistic fills.")
    print("  The number above is the same book on data it was never tuned on.")
