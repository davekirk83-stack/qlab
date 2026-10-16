"""
DAYS TO STAY OUT OF — FOMC and the rest, tested rather than assumed.

DK: "We could also establish a rule about which days are best to avoid
     altogether for trading (FOMC +/-2?)"

A reasonable instinct, and this is the first question in the calendar family
that CAN be answered with the data we have. Doc 123 refused to read anything
into the monthly table because thirteen months gives one observation per
month and five years gives five. FOMC is different: eight meetings a year
over five years is about forty events, which is enough to detect a large
effect even though it would miss a subtle one.

WHY IT MIGHT MATTER FOR THIS BOOK SPECIFICALLY. The range book sells
volatility - it buys the lower band expecting price to come back, and its
losses come from breaks that keep going. A scheduled event that reliably
produces a directional break is therefore its worst possible environment,
and unlike most risks it is known about in advance. If the effect is real,
sitting out is free.

WHY IT MIGHT NOT. Crypto trades through the night and the weekend and is not
obviously tied to the Fed; and doc 123 found the book made money through
2022, the most relentless hiking cycle in forty years. If FOMC days really
hurt, 2022 should have been its worst year, and it was not.

TESTED
  the decision day itself, and windows of +/-1 and +/-2 days around it
  weekends against weekdays, since crypto is the only asset that trades both
  month end and quarter end, where futures and options roll
  the US cash open and close hours, already partly covered by doc 106

DATES. The decision day (the SECOND day of each two-day meeting) for 2021-2025
is taken from the published schedule and is reliable. The 2026 dates are from
the schedule as published in advance and are less certain; since the test uses
a +/-2 day window, a one-day error blurs the result rather than inventing one,
but the 2026 rows should be verified before anything is registered on them.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD
import fiveyear as FY

FOMC = [
 "2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22",
 "2021-11-03","2021-12-15",
 "2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21",
 "2022-11-02","2022-12-14",
 "2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20",
 "2023-11-01","2023-12-13",
 "2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18",
 "2024-11-07","2024-12-18",
 "2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17",
 "2025-10-29","2025-12-10",
 # 2026 — published in advance, less certain
 "2026-01-28","2026-03-18","2026-04-29","2026-06-17","2026-07-29","2026-09-16",
]
STABLE = {"USDTUSD","USDCUSD","DAIUSD","PYUSDUSD","USDSUSD","RLUSDUSD"}


if __name__ == "__main__":
    data = {s: d for s, d in FY.load5().items() if s not in STABLE}
    print(f"{len(data)} symbols, five years.\n")
    rows = []
    for s, d in data.items():
        D, ema, lo, hi, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        al = (v > v.expanding(500).median()).values
        rows += CP.episodes(d, al, ema, lo, hi, a, None, "optimistic", "L", s)
        rows += CP.episodes(d, al, ema, lo, hi, a, None, "optimistic", "S", s)
    S = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"])
    S = S[np.isfinite(S.ret)].copy()
    S["ts"] = pd.to_datetime(S.entry)
    S["day"] = S.ts.dt.tz_convert("UTC").dt.normalize()
    print(f"{len(S):,} episodes.\n")

    fom = pd.to_datetime(FOMC).tz_localize("UTC")
    print("="*86)
    print("FOMC — is the book worse around a decision?")
    print("="*86)
    print(f"  {'window':<26}{'episodes':>10}{'per ep':>11}{'win':>7}"
          f"{'worst':>10}{'total':>11}")
    for w, lbl in ((0, "decision day only"), (1, "+/- 1 day"), (2, "+/- 2 days")):
        near = pd.Series(False, index=S.index)
        for f in fom:
            near |= (S.day >= f - pd.Timedelta(days=w)) & \
                    (S.day <= f + pd.Timedelta(days=w))
        g, o = S[near], S[~near]
        if len(g) < 100: continue
        print(f"  {'FOMC '+lbl:<26}{len(g):>10,}{g.ret.mean()*100:>+10.4f}%"
              f"{(g.ret>0).mean()*100:>6.0f}%{g.ret.min()*100:>+9.1f}%"
              f"{g.ret.sum()*100:>+10.0f}%")
        print(f"  {'  all other days':<26}{len(o):>10,}{o.ret.mean()*100:>+10.4f}%"
              f"{(o.ret>0).mean()*100:>6.0f}%{o.ret.min()*100:>+9.1f}%"
              f"{o.ret.sum()*100:>+10.0f}%")
        diff = g.ret.mean()-o.ret.mean()
        se = np.sqrt(g.ret.var(ddof=1)/len(g) + o.ret.var(ddof=1)/len(o))
        print(f"  {'  difference':<26}{'':>10}{diff*100:>+10.4f}%"
              f"{'':>6}{'':>9}   t = {diff/se:+.2f}\n")

    print("="*86)
    print("OTHER CANDIDATE DAYS TO AVOID")
    print("="*86)
    S["dow"] = S.ts.dt.tz_convert("Europe/London").dt.dayofweek
    S["dom"] = S.ts.dt.tz_convert("Europe/London").dt.day
    S["mon"] = S.ts.dt.tz_convert("Europe/London").dt.month
    tests = [
        ("weekend (Sat/Sun)", S.dow >= 5),
        ("Monday", S.dow == 0),
        ("Friday", S.dow == 4),
        ("month end (last 2 days)", S.dom >= 29),
        ("month start (first 2)", S.dom <= 2),
        ("quarter end month", S.mon.isin([3, 6, 9, 12]) & (S.dom >= 28)),
    ]
    print(f"  {'candidate':<28}{'episodes':>10}{'per ep':>11}{'vs rest':>11}{'t':>8}")
    for lbl, mask in tests:
        g, o = S[mask], S[~mask]
        if len(g) < 200: continue
        diff = g.ret.mean()-o.ret.mean()
        se = np.sqrt(g.ret.var(ddof=1)/len(g) + o.ret.var(ddof=1)/len(o))
        print(f"  {lbl:<28}{len(g):>10,}{g.ret.mean()*100:>+10.4f}%"
              f"{diff*100:>+10.4f}%{diff/se:>+8.2f}")

    print("\n  A day is worth avoiding only if the difference is both NEGATIVE and")
    print("  large enough to survive the cost of the trades it forgoes. With ~46")
    print("  FOMC meetings in the sample, a t below about 2 is not a finding —")
    print("  and sitting out days on a weak signal is how breadth gets destroyed.")
