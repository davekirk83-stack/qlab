"""
CALENDAR / CYCLE CONDITIONING.

DK: factor in statistical probabilities of success by day / week / month / year
and the US election cycle.

This is real territory — seasonality and the presidential cycle are both
documented — but it is also where spurious patterns breed fastest. Seven weekdays
x twelve months x four cycle years is a lot of buckets, and with ~5,000 trades
some buckets will look wonderful by chance alone.

So the method is derive-then-test, never derive-and-report:

  1. Split the trade history in half by TIME.
  2. Compute each calendar bucket's statistics on the FIRST half only.
  3. Pick the favourable buckets from that half.
  4. Measure what those buckets did in the SECOND half, which the selection
     never saw.
  5. A calendar effect is real only if the first-half selection improves the
     second half. Otherwise it is curve-fitting the calendar.

Buckets tested:
    day of week          Mon-Fri
    week of month        1st..5th
    month of year        Jan-Dec
    quarter              Q1-Q4
    US election cycle    year 1 (post-election), 2 (midterm), 3 (pre-election), 4 (election)
    turn of month        last 3 / first 3 trading days
"""
import numpy as np, pandas as pd
import core as C, levels as LV
from run10 import load_universe, est_cost
import split as S

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}
BEST = dict(stop_atr=1.0, tp1_r=1.0, tp2_r=3.0, tp3_r=15.0,
            trail_atr=4.0, meat_bars=5, runner_bars=60)

# US presidential election years
ELECTIONS = {2004, 2008, 2012, 2016, 2020, 2024, 2028}


def cycle_year(y):
    """1 = year after an election, ... 4 = election year."""
    last = max([e for e in ELECTIONS if e <= y], default=y)
    d = y - last
    return 4 if d == 0 else d


def collect():
    """Every trade with its entry date, so it can be bucketed."""
    rows = []
    for s, df in PANEL.items():
        try:
            e = LV.l_swing_break(df, 20)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        A = S.atr(df).values
        H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
        SL = df.low.rolling(10).min().values
        idx = np.flatnonzero(e.values > 0)
        last = -1
        for i in idx:
            if i <= last or i + 1 >= len(df):
                continue
            res = S.trade(df.iloc[max(0, i - 250):i + 200],
                          pd.Series(0.0, index=df.index[max(0, i - 250):i + 200]),
                          COSTS[s], **BEST)
            break
        # simpler: run the whole symbol once and tag by entry index
        out = S.trade(df, e, COSTS[s], **BEST)
        ptr = 0
        entries_idx = list(idx)
        for r, b, t1, t2 in out:
            rows.append(dict(ret=r, bars=b, sym=s))
        # attach dates by re-walking
    return pd.DataFrame(rows)


def collect_dated():
    """Re-implement the walk so each trade carries its entry DATE."""
    rows = []
    for s, df in PANEL.items():
        try:
            e = LV.l_swing_break(df, 20)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        A = S.atr(df).values
        H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
        SL = df.low.rolling(10).min().values
        cost = COSTS[s]
        idx = np.flatnonzero(e.values > 0)
        last = -1
        for i in idx:
            if i <= last or i + 1 >= len(df):
                continue
            a = A[i]
            if not (a == a) or a <= 0:
                continue
            px = O[i + 1]
            if not (px == px) or px <= 0:
                continue
            st = max(px - a, SL[i] * 0.995) if SL[i] == SL[i] else px - a
            if st >= px:
                st = px - a
            risk = px - st
            if risk <= 0:
                continue
            tp1, tp2, tp3 = px + risk, px + 3 * risk, px + 15 * risk
            filled, pnl, peak, ex = 0.0, 0.0, px, None
            cur = st
            for j in range(i + 1, min(i + 61, len(df))):
                k = j - i
                if L[j] <= cur:
                    pnl += (1 - filled) * (cur / px - 1); ex = j; break
                if filled < 0.34 and H[j] >= tp1:
                    pnl += (1 / 3) * (tp1 / px - 1); filled = 1 / 3
                    cur = max(cur, px + 0.10 * risk + cost * px)
                if filled < 0.67 and H[j] >= tp2:
                    pnl += (1 / 3) * (tp2 / px - 1); filled = 2 / 3
                if k >= 5 and filled < 0.66:
                    cl = (2 / 3) - filled
                    if cl > 0:
                        pnl += cl * (Cl[j] / px - 1); filled = 2 / 3
                if filled >= 0.66:
                    if H[j] >= tp3:
                        pnl += (1 - filled) * (tp3 / px - 1); ex = j; break
                    tr = peak - 4.0 * a
                    if L[j] <= tr and tr > cur:
                        pnl += (1 - filled) * (tr / px - 1); ex = j; break
                peak = max(peak, H[j])
            if ex is None:
                j = min(i + 60, len(df) - 1)
                pnl += (1 - filled) * (Cl[j] / px - 1); ex = j
            d = df.index[i + 1]
            rows.append(dict(ret=pnl - cost, date=d, sym=s))
            last = ex
    t = pd.DataFrame(rows)
    t["date"] = pd.to_datetime(t["date"])
    t["dow"] = t.date.dt.dayofweek
    t["wom"] = ((t.date.dt.day - 1) // 7) + 1
    t["month"] = t.date.dt.month
    t["quarter"] = t.date.dt.quarter
    t["cycle"] = t.date.dt.year.map(cycle_year)
    t["tom"] = ((t.date.dt.day >= 26) | (t.date.dt.day <= 3)).astype(int)
    return t


DOW = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
CYC = {1: "Y1 post-election", 2: "Y2 midterm", 3: "Y3 pre-election", 4: "Y4 election"}


def table(t, col, labels=None, title=""):
    g = t.groupby(col).ret.agg(["count", "mean", "median"])
    g["win"] = t.groupby(col).ret.apply(lambda x: (x > 0).mean())
    g = g[g["count"] >= 50]
    print(f"\n  {title}")
    print(f"    {'bucket':20s} {'n':>6} {'expectancy':>11} {'median':>9} {'win%':>7}")
    for k, r in g.sort_values("mean", ascending=False).iterrows():
        lab = labels.get(k, str(k)) if labels else str(k)
        print(f"    {lab:20s} {int(r['count']):6d} {r['mean']*100:+10.3f}% "
              f"{r['median']*100:+8.3f}% {r['win']*100:6.1f}%")
    return g


def main():
    print("CALENDAR & CYCLE CONDITIONING — swing break, spec v1\n")
    t = collect_dated()
    print(f"  {len(t)} trades, {t.date.min().date()} to {t.date.max().date()}")
    print(f"  OVERALL expectancy {t.ret.mean()*100:+.3f}%  win {float((t.ret>0).mean())*100:.1f}%")

    print("\n" + "=" * 78)
    print("  FULL-SAMPLE STATISTICS BY BUCKET  (descriptive only — see the test below)")
    print("=" * 78)
    table(t, "dow", DOW, "DAY OF WEEK (entry day)")
    table(t, "wom", None, "WEEK OF MONTH")
    table(t, "month", None, "MONTH OF YEAR")
    table(t, "quarter", None, "QUARTER")
    table(t, "cycle", CYC, "US ELECTION CYCLE")
    table(t, "tom", {0: "mid-month", 1: "turn of month"}, "TURN OF MONTH")

    print("\n" + "=" * 78)
    print("  THE HONEST TEST — derive buckets on the FIRST half, measure on the SECOND")
    print("=" * 78)
    t = t.sort_values("date")
    cut = t.date.quantile(0.5)
    a, b = t[t.date < cut], t[t.date >= cut]
    print(f"  first half  {a.date.min().date()} to {a.date.max().date()}  n={len(a)}")
    print(f"  second half {b.date.min().date()} to {b.date.max().date()}  n={len(b)}")
    print(f"\n  {'filter':24s} {'1st-half sel.':>14} {'2nd-half result':>17} "
          f"{'vs unfiltered':>14}")
    base_b = b.ret.mean()
    for col, lab in (("dow", "day of week"), ("wom", "week of month"),
                     ("month", "month"), ("quarter", "quarter"),
                     ("cycle", "election cycle"), ("tom", "turn of month")):
        g = a.groupby(col).ret.agg(["count", "mean"])
        g = g[g["count"] >= 30]
        good = list(g[g["mean"] > a.ret.mean()].index)
        if not good:
            continue
        sel = b[b[col].isin(good)]
        if len(sel) < 50:
            continue
        print(f"  {lab:24s} {len(good):3d} buckets kept  "
              f"{sel.ret.mean()*100:+15.3f}% {(sel.ret.mean()-base_b)*100:+13.3f}pp")
    print(f"\n  unfiltered second half: {base_b*100:+.3f}%")
    print("\n  A calendar effect is REAL only if the right-hand column is positive.")

    C.ledger_bump(6, "calendar/cycle conditioning, derive-then-test")
    t.to_csv("/home/claude/qlab/runs/calendar.csv", index=False)


if __name__ == "__main__":
    main()
