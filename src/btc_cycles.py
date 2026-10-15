"""
ELEVEN YEARS OF BITCOIN, BY CYCLE — WHERE DOES TODAY SIT?

DK: "Many people think we are just kicking off into the next BTC bull market
     cycle."

Worth testing rather than agreeing or disagreeing with, because the claim is
checkable against the only four cycles that exist. The halving is the usual
anchor, so each cycle is measured from its halving date and today is placed on
the same axis as its predecessors.

Halvings: 2012-11-28, 2016-07-09, 2020-05-11, 2024-04-19. Next ~2028-04.

What is measured, all from the data rather than from the folklore:
  - the top and bottom of each cycle, and how many days after the halving
  - drawdown from the all-time high, then and now
  - today's position on the halving clock against the same day in each prior
    cycle
  - what price did over the following 90 and 180 days from a comparable point

CAVEAT STATED UP FRONT AND NOT BURIED. Four cycles is four observations. Two
of those (2012, 2016) happened at a market capitalisation small enough that
the asset was a different thing. Anything resembling an average of four
numbers is not a forecast, and none of this is a recommendation - it is where
today sits on a chart of what has happened before.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

HALVINGS = ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-19"]
NEXT = "2028-04-20"


def load():
    d = pd.read_csv("/home/claude/qlab/data_daily/BTCUSD.csv")
    d.index = pd.to_datetime(d.t, unit="ms")
    return d[["open", "high", "low", "close", "volume"]].sort_index()


if __name__ == "__main__":
    d = load()
    print(f"BTC daily: {len(d):,} bars, {d.index[0].date()} -> {d.index[-1].date()}")
    px = float(d.close.iloc[-1])
    ath = float(d.close.cummax().iloc[-1])
    ath_date = d.close.idxmax().date()
    print(f"last close {px:,.0f}   all-time closing high {ath:,.0f} on {ath_date}"
          f"   drawdown {(px/ath-1)*100:+.1f}%\n")

    H = [pd.Timestamp(h) for h in HALVINGS]
    today = d.index[-1]
    cur_cycle = max(i for i, h in enumerate(H) if h <= today)
    days_in = (today - H[cur_cycle]).days
    print(f"today is day {days_in} of cycle {cur_cycle+1} "
          f"(halving {H[cur_cycle].date()}, next {NEXT})\n")

    print("=" * 94)
    print("EACH CYCLE MEASURED FROM ITS HALVING")
    print(f"  {'cycle':<8}{'halving':<12}{'low':>12}{'d_low':>7}"
          f"{'high':>12}{'d_high':>8}{'gain x':>9}{'then fell':>11}")
    rows = []
    for i, h in enumerate(H):
        end = H[i+1] if i + 1 < len(H) else today
        seg = d.loc[h:end]
        if len(seg) < 50: continue
        lo, hi = seg.close.min(), seg.close.max()
        d_lo = (seg.close.idxmin() - h).days
        d_hi = (seg.close.idxmax() - h).days
        after = seg.loc[seg.close.idxmax():]
        fell = (after.close.min() / hi - 1) * 100 if len(after) > 1 else np.nan
        rows.append((i+1, h, lo, d_lo, hi, d_hi, hi/lo, fell))
        print(f"  {i+1:<8}{str(h.date()):<12}{lo:>12,.0f}{d_lo:>7}"
              f"{hi:>12,.0f}{d_hi:>8}{hi/lo:>8.1f}x{fell:>10.1f}%")

    print(f"\n  peak came {', '.join(str(r[5]) for r in rows[:-1])} days after "
          f"the halving in completed cycles "
          f"(median {int(np.median([r[5] for r in rows[:-1]]))})")

    print("\n" + "=" * 94)
    print(f"TODAY (day {days_in}) AGAINST THE SAME DAY IN EVERY PRIOR CYCLE")
    print(f"  {'cycle':<8}{'px at day':>12}{'vs cycle low':>14}{'drawdn от high':>16}"
          .replace("от", "from") + f"{'next 90d':>10}{'next 180d':>11}")
    for i, h in enumerate(H[:-1]):
        tgt = h + pd.Timedelta(days=days_in)
        seg = d.loc[h:H[i+1]] if i + 1 < len(H) else d.loc[h:]
        if tgt not in d.index:
            nearest = d.index[d.index.get_indexer([tgt], method="nearest")][0]
        else:
            nearest = tgt
        if nearest > d.index[-1]: continue
        p = float(d.close.loc[nearest])
        lo = float(seg.close.min())
        runmax = float(d.close.loc[:nearest].max())
        f90 = d.close.loc[:nearest + pd.Timedelta(days=90)].iloc[-1] / p - 1
        f180 = d.close.loc[:nearest + pd.Timedelta(days=180)].iloc[-1] / p - 1
        print(f"  {i+1:<8}{p:>12,.0f}{p/lo:>13.1f}x{(p/runmax-1)*100:>15.1f}%"
              f"{f90*100:>+9.1f}%{f180*100:>+10.1f}%")
    cl = float(d.loc[H[cur_cycle]:].close.min())
    print(f"  {cur_cycle+1:<8}{px:>12,.0f}{px/cl:>13.1f}x{(px/ath-1)*100:>15.1f}%"
          f"{'  — now —':>19}")

    print("\n" + "=" * 94)
    print("IS THIS A BOTTOM OR A TOP? the measures that distinguished them before")
    cyc = d.loc[H[cur_cycle]:]
    for lbl, w in (("200d", 200), ("50d", 50)):
        ma = d.close.rolling(w).mean().iloc[-1]
        print(f"  price vs {lbl} MA              {(px/ma-1)*100:+7.1f}%")
    dd = (d.close / d.close.cummax() - 1)
    print(f"  current drawdown from ATH      {dd.iloc[-1]*100:+7.1f}%")
    print(f"  deepest drawdown this cycle    {dd.loc[H[cur_cycle]:].min()*100:+7.1f}%")
    for i, h in enumerate(H[:-1]):
        end = H[i+1]
        print(f"  deepest drawdown cycle {i+1}       "
              f"{dd.loc[h:end].min()*100:+7.1f}%")
    r365 = px / float(d.close.iloc[-366]) - 1 if len(d) > 366 else np.nan
    print(f"\n  trailing 1-year return         {r365*100:+7.1f}%")
    print(f"  days since the ATH close       {(today - pd.Timestamp(ath_date)).days}")

    print("\n" + "=" * 94)
    print("CAVEAT: four cycles is four observations, and two of them happened at")
    print("a market cap where BTC was a different asset. This is where today sits")
    print("on a chart of what has happened before, not a forecast.")
