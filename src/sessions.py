"""
SESSION ANALYSIS — Asia / London / US.

DK: "the US trading session is typically very likely to clear the previous
London session's high or low."

That is a specific, falsifiable claim and we have the data to test it:
21,912 hourly bars per symbol, 2.5 years, 8 crypto symbols (24/7, so sessions
are cleanly defined by UTC hour and there are no gaps).

Session definitions (UTC), using the standard overlapping convention:
    ASIA    00:00 - 08:00
    LONDON  07:00 - 16:00
    US      13:00 - 21:00

Tested here:
  1. P(US clears the previous London high)  and  P(US clears the London low)
  2. P(US clears EITHER)  -- DK's claim
  3. The same for London vs the previous Asia session
  4. Which session actually produces the returns
  5. Does a sweep predict direction? i.e. once the US takes out London's high,
     does it keep going or reverse? That is the tradeable part.
"""
import os, numpy as np, pandas as pd

PX = "/home/claude/qlab/data_1h"
SYMS = sorted(f[:-4] for f in os.listdir(PX) if f.endswith(".csv"))

SESSIONS = {"ASIA": (0, 8), "LONDON": (7, 16), "US": (13, 21)}


def load(sym):
    d = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    return d[~d.index.duplicated()]


def session_frame(df):
    """One row per (date, session) with OHLC for that session."""
    rows = []
    h = df.index.hour
    for name, (a, b) in SESSIONS.items():
        m = (h >= a) & (h < b)
        sub = df[m]
        g = sub.groupby(sub.index.date)
        agg = g.agg(open=("open", "first"), high=("high", "max"),
                    low=("low", "min"), close=("close", "last"),
                    volume=("volume", "sum"))
        agg["session"] = name
        agg.index = pd.to_datetime(agg.index)
        rows.append(agg)
    s = pd.concat(rows).reset_index().rename(columns={"index": "day"})
    return s.sort_values(["day", "session"])


def main():
    print("SESSION ANALYSIS — Asia / London / US, hourly crypto data\n")
    print(f"  {len(SYMS)} symbols: {', '.join(SYMS)}")
    print("  ASIA 00-08 UTC · LONDON 07-16 UTC · US 13-21 UTC\n")

    sweep_hi, sweep_lo, sweep_either = [], [], []
    ldn_sweep_asia = []
    sess_ret = {k: [] for k in SESSIONS}
    cont_after_hi, rev_after_hi = [], []
    total_days = 0

    for sym in SYMS:
        df = load(sym)
        sf = session_frame(df)
        piv = sf.pivot(index="day", columns="session")
        for c in ("high", "low", "open", "close"):
            if c not in piv.columns.levels[0]:
                continue
        try:
            hi = piv["high"]; lo = piv["low"]; op = piv["open"]; cl = piv["close"]
        except KeyError:
            continue
        hi, lo, op, cl = [x.dropna(how="any") for x in (hi, lo, op, cl)]
        common = hi.index.intersection(lo.index).intersection(cl.index)
        hi, lo, op, cl = hi.loc[common], lo.loc[common], op.loc[common], cl.loc[common]
        if len(hi) < 100:
            continue
        total_days += len(hi)

        # 1-3: does the US session clear the SAME DAY's London extremes?
        us_hi, us_lo = hi["US"], lo["US"]
        ldn_hi, ldn_lo = hi["LONDON"], lo["LONDON"]
        asia_hi, asia_lo = hi["ASIA"], lo["ASIA"]

        sweep_hi.append((us_hi > ldn_hi).mean())
        sweep_lo.append((us_lo < ldn_lo).mean())
        sweep_either.append(((us_hi > ldn_hi) | (us_lo < ldn_lo)).mean())
        ldn_sweep_asia.append((((ldn_hi > asia_hi) | (ldn_lo < asia_lo))).mean())

        # 4: session returns
        for k in SESSIONS:
            sess_ret[k].append(float((cl[k] / op[k] - 1).mean()))

        # 5: once the US takes out London's high, does it close above it?
        took = us_hi > ldn_hi
        if took.sum() > 20:
            cont_after_hi.append(float((cl["US"][took] > ldn_hi[took]).mean()))
            rev_after_hi.append(float((cl["US"][took] < ldn_hi[took]).mean()))

    print("=" * 76)
    print("  1-3.  DOES THE US SESSION CLEAR THE LONDON SESSION'S EXTREMES?")
    print("=" * 76)
    print(f"  across {total_days:,} session-days")
    print(f"    US clears London HIGH      {np.mean(sweep_hi)*100:5.1f}%  "
          f"(range {min(sweep_hi)*100:.0f}-{max(sweep_hi)*100:.0f}%)")
    print(f"    US clears London LOW       {np.mean(sweep_lo)*100:5.1f}%  "
          f"(range {min(sweep_lo)*100:.0f}-{max(sweep_lo)*100:.0f}%)")
    print(f"    US clears EITHER           {np.mean(sweep_either)*100:5.1f}%  "
          f"<-- DK's claim")
    print(f"    LONDON clears Asia either  {np.mean(ldn_sweep_asia)*100:5.1f}%")

    print()
    print("=" * 76)
    print("  4.  WHICH SESSION PRODUCES THE RETURN?")
    print("=" * 76)
    for k in SESSIONS:
        v = np.mean(sess_ret[k]) * 100
        print(f"    {k:8s} mean session return {v:+.4f}%  "
              f"(annualised ~{((1+np.mean(sess_ret[k]))**365-1)*100:+.1f}%)")

    print()
    print("=" * 76)
    print("  5.  THE TRADEABLE PART — after the US takes out London's high,")
    print("      does it HOLD above it or reverse back through?")
    print("=" * 76)
    if cont_after_hi:
        print(f"    closes ABOVE the London high (continuation) {np.mean(cont_after_hi)*100:5.1f}%")
        print(f"    closes BELOW it (sweep and reverse)         {np.mean(rev_after_hi)*100:5.1f}%")
        print()
        if np.mean(cont_after_hi) > 0.55:
            print("    -> leans CONTINUATION: taking London's high is a go signal")
        elif np.mean(rev_after_hi) > 0.55:
            print("    -> leans REVERSAL: the sweep is a liquidity grab, fade it")
        else:
            print("    -> no directional edge: the sweep happens, but it does not")
            print("       predict where the session closes. The pattern is real;")
            print("       the TRADE is not.")


def us_open_reversal():
    """DK: at the US open the first directional move usually reverses after
    60-90 minutes. Testable: take the direction of the first N hours after
    13:00 UTC, then measure the return over the REST of the session."""
    print()
    print("=" * 76)
    print("  6.  US OPEN — DOES THE FIRST MOVE REVERSE?")
    print("=" * 76)
    print(f"    {'first move window':20s} {'n':>7} {'P(reverse)':>12} "
          f"{'mean rest-of-session return':>30}")
    for win in (1, 2, 3):
        agree, rest_aligned, rest_against, n = [], [], [], 0
        for sym in SYMS:
            df = load(sym)
            h = df.index.hour
            d = df[(h >= 13) & (h < 21)]
            g = d.groupby(d.index.date)
            for day, sub in g:
                if len(sub) < win + 3:
                    continue
                first = sub.close.iloc[win - 1] / sub.open.iloc[0] - 1
                rest = sub.close.iloc[-1] / sub.close.iloc[win - 1] - 1
                if first == 0:
                    continue
                n += 1
                same = (first > 0) == (rest > 0)
                agree.append(same)
                if first > 0:
                    rest_aligned.append(rest)
                else:
                    rest_against.append(rest)
        if n:
            p_rev = 1 - np.mean(agree)
            up = np.mean(rest_aligned) * 100 if rest_aligned else 0
            dn = np.mean(rest_against) * 100 if rest_against else 0
            print(f"    first {win}h ({13}:00-{13+win}:00) {n:7d} {p_rev*100:11.1f}% "
                  f"   after UP move {up:+.3f}% / after DOWN move {dn:+.3f}%")
    print()
    print("    P(reverse) near 50% = coin flip, no pattern.")
    print("    Above ~55% would support the claim.")


if __name__ == "__main__":
    main()
    us_open_reversal()
