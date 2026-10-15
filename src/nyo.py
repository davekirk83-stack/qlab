"""
NEW YORK OPEN — time-to-reversal of the opening move, at 15-minute resolution.

DK: "the first move directionally usually reverses after the first 60-90 mins."
My earlier hourly test asked a cruder question ("does the rest of the session go
the other way") and found a coin flip. That is not the same claim. The claim is
that the OPENING MOVE gets retraced. So measure that directly.

Correct NY cash open: 09:30 ET.
    EDT (Mar-Nov) = UTC-4  -> 13:30 UTC
    EST (Nov-Mar) = UTC-5  -> 14:30 UTC
Handled per date rather than assumed.

Measured, per day:
  - the "first move": the extreme reached in the first 15/30/45/60 min after the open
  - P(price trades back THROUGH the opening price) within N minutes
  - the time distribution of that retrace
  - and, because a retrace is not automatically a trade, what happens AFTER it:
    does the reversal continue, or was the first move right all along?
"""
import os, numpy as np, pandas as pd

D15 = "/home/claude/qlab/data_15m"
SYMS = sorted(f[:-4] for f in os.listdir(D15) if f.endswith(".csv"))


def ny_open_hour(ts):
    """13:30 UTC during US daylight time, 14:30 UTC otherwise.
    DST: 2nd Sunday March -> 1st Sunday November."""
    y = ts.year
    mar = pd.Timestamp(f"{y}-03-01")
    start = mar + pd.Timedelta(days=(6 - mar.dayofweek) % 7 + 7)
    nov = pd.Timestamp(f"{y}-11-01")
    end = nov + pd.Timedelta(days=(6 - nov.dayofweek) % 7)
    return (13, 30) if start <= ts.normalize() < end else (14, 30)


def main():
    print("NEW YORK OPEN — opening-move reversal at 15-minute resolution\n")
    print(f"  {len(SYMS)} symbols, {', '.join(SYMS)}")
    print("  NY cash open 09:30 ET, DST handled per date\n")

    FIRST = [1, 2, 3, 4]        # 15, 30, 45, 60 min defining the 'first move'
    HORIZ = [2, 4, 6, 8, 12]    # 30min, 1h, 1.5h, 2h, 3h to retrace

    res = {(f, h): [] for f in FIRST for h in HORIZ}
    times = {f: [] for f in FIRST}
    after = {f: [] for f in FIRST}
    ndays = 0

    for sym in SYMS:
        df = pd.read_csv(f"{D15}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
        for day, sub in df.groupby(df.index.date):
            ts = pd.Timestamp(day)
            oh, om = ny_open_hour(ts)
            op = sub[(sub.index.hour == oh) & (sub.index.minute == om)]
            if op.empty:
                continue
            start = op.index[0]
            win = sub[sub.index >= start].head(40)      # 10 hours
            if len(win) < 20:
                continue
            ndays += 1
            o = win.open.iloc[0]
            for f in FIRST:
                seg = win.iloc[:f]
                move = seg.close.iloc[-1] - o
                if move == 0:
                    continue
                up = move > 0
                rest = win.iloc[f:]
                # did price trade back THROUGH the opening price?
                if up:
                    hit = np.flatnonzero(rest.low.values <= o)
                else:
                    hit = np.flatnonzero(rest.high.values >= o)
                for h in HORIZ:
                    res[(f, h)].append(bool(len(hit) and hit[0] < h))
                if len(hit):
                    times[f].append((hit[0] + 1) * 15)   # minutes after the first move
                    # what happens AFTER the retrace: continue reversing or snap back?
                    k = hit[0]
                    if k + 8 < len(rest):
                        post = rest.close.iloc[k + 8] - o
                        after[f].append(bool((post < 0) if up else (post > 0)))

    print("=" * 84)
    print("  P(the opening move retraces back through the open) ")
    print("=" * 84)
    print(f"  {'first move':14s}" + "".join(f"{h*15:>10}min" for h in HORIZ))
    for f in FIRST:
        row = f"  first {f*15:3d} min   "
        for h in HORIZ:
            v = res[(f, h)]
            row += f"{np.mean(v)*100:12.1f}%" if v else f"{'n/a':>13}"
        print(row)
    print(f"\n  n = {ndays:,} session-days")

    print()
    print("=" * 84)
    print("  HOW LONG DOES THE RETRACE TAKE?  (of those that do retrace)")
    print("=" * 84)
    for f in FIRST:
        t = np.array(times[f])
        if len(t) < 50:
            continue
        print(f"  first {f*15:3d} min move: median {np.median(t):5.0f} min, "
              f"25th {np.percentile(t,25):4.0f}, 75th {np.percentile(t,75):5.0f}  "
              f"(n={len(t)})")
        within = {m: float((t <= m).mean()) for m in (30, 60, 90, 120, 180)}
        print("     cumulative: " + "  ".join(f"{m}min {v*100:.0f}%"
                                              for m, v in within.items()))

    print()
    print("=" * 84)
    print("  IS THE REVERSAL TRADEABLE? — 2h after the retrace, has it kept going?")
    print("=" * 84)
    for f in FIRST:
        a = after[f]
        if len(a) < 50:
            continue
        print(f"  first {f*15:3d} min move: reversal continued {np.mean(a)*100:5.1f}%  "
              f"(n={len(a)})  {'-> edge' if np.mean(a) > 0.55 else '-> coin flip'}")


if __name__ == "__main__":
    main()
