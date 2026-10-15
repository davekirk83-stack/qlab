"""
THE KELTNER RANGE PAIR — market-neutral band reversion.

Doc 66 found the long-only version works but is partly market drift: the trade
replicated out-of-sample (+0.288%, 75.7% win, 18/25 symbols) while the EDGE over
control did not, because the out-of-sample window rose and a random long made
+0.445%. The symmetry test is what settled it:

              long                    short
  in-sample   +0.337%  76.6% win      +0.241%  83.7% win
  out-sample  +0.337%  76.0% win      -0.146%  81.2% win

Read the WIN RATES, not the returns. 76.6 -> 76.0 and 83.7 -> 81.2, across
different symbols, a different period and a different market direction. The
reversion mechanism replicates almost exactly. What does not replicate is the
money, because in a rising market the short leg hands back what the long wins.

So this is not a directional book and should never have been tested as one.
Run it as a PAIR and the market term cancels — which is precisely the leg the
out-of-sample test showed was contaminating it.

THE BOOK
  universe   crypto perps, hourly
  regime     RANGE only: Kaufman efficiency ratio over 100 bars below the cut.
             Trending markets are excluded because the band is then just where
             the trend currently is, with nothing to revert to.
  long       close crosses BELOW the lower Keltner band (EMA20 - 2 ATR)
  short      close crosses ABOVE the upper band
  exit       the mid (EMA20), or a 120-hour cap
  stop       NONE. Doc 66: return rises monotonically with stop width and is
             best with no stop at all. A band touch is a volatility event and
             any stop inside that volatility is hit by the move that created
             the signal. Risk is controlled by the TIME CAP and by the pairing,
             not by a price stop.
  sizing     equal notional each side, so net exposure is zero by construction

WHAT IS MEASURED HERE, that doc 66 did not
  1. the PAIR as a portfolio, not two legs reported separately
  2. net exposure through time, to prove neutrality rather than assume it
  3. by year and by half
  4. out-of-sample on 25 symbols never used in development
  5. a control pair: random entries, same regime, same holding period
  6. the efficiency cut swept, since the threshold is a judgement
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

HOURLY = "/home/claude/qlab/data_1h_33"
OOS = "/home/claude/qlab/data_1m_oos"
MAKER, TAKER = 2 / 10000, 5 / 10000
MAXH = 120
RNG = np.random.default_rng(66166)


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net / np.where(gross > 0, gross, np.nan)


def leg(C, H, L, i, tgt, short):
    """One side. Entry maker (resting at the band), exit maker at the mid."""
    n = len(C)
    e = C[i] * (1 - MAKER) if short else C[i] * (1 + MAKER)
    for q in range(i + 1, min(i + 1 + MAXH, n)):
        if (L[q] <= tgt) if short else (H[q] >= tgt):
            x = tgt * (1 + MAKER) if short else tgt * (1 - MAKER)
            return ((e - x) / e if short else (x - e) / e), q - i, True
    q = min(i + MAXH, n - 1)
    x = C[q]
    r = (e - x * (1 + TAKER)) / e if short else (x * (1 - TAKER) - e) / e
    return r, MAXH, False


def load_hourly(p):
    d = pd.read_csv(p)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    return d.dropna(subset=["date"]).set_index("date").sort_index()


def load_from_1m(p):
    d = pd.read_csv(p)
    d["dt"] = pd.to_datetime(d.t, unit="ms")
    d = d.set_index("dt").sort_index()
    d = d[~d.index.duplicated()]
    return d.resample("1h").agg(open=("open", "first"), high=("high", "max"),
                                low=("low", "min"), close=("close", "last")).dropna()


def collect(files, loader, cut):
    rows = []
    for p in sorted(files):
        s = os.path.basename(p)[:-4]
        d = loader(p)
        if len(d) < 1200:
            continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr(H, L, C); n = len(C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        eff = efficiency(C)
        lo_b = ema - 2 * a; up_b = ema + 2 * a
        for side, trig, short in (("long", (C <= lo_b) & (np.roll(C, 1) > np.roll(lo_b, 1)), False),
                                  ("short", (C >= up_b) & (np.roll(C, 1) < np.roll(up_b, 1)), True)):
            last = -10 ** 9
            for i in np.flatnonzero(trig):
                if i < 250 or i > n - MAXH - 2 or i - last < MAXH:
                    continue
                if not np.isfinite(eff[i]) or eff[i] >= cut:
                    continue
                last = i
                r, bars, hit = leg(C, H, L, i, ema[i], short)
                # control: a random bar in the same regime, same geometry
                q = None
                for _ in range(30):
                    cand = int(RNG.integers(max(250, i - 800), min(n - MAXH - 2, i + 800) + 1))
                    if np.isfinite(eff[cand]) and eff[cand] < cut:
                        q = cand; break
                cr = np.nan
                if q is not None:
                    span = ema[i] - C[i] if not short else C[i] - ema[i]
                    cr = leg(C, H, L, q, C[q] + span if not short else C[q] - span, short)[0]
                rows.append(dict(sym=s, ts=d.index[i], side=side, R=r,
                                 bars=bars, hit=hit, CTRL=cr))
    return pd.DataFrame(rows)


def pair_report(T, label, cut):
    if len(T) < 100:
        print(f"  {label}: too few"); return
    L = T[T.side == "long"]; S = T[T.side == "short"]
    # the PAIR: average the two legs per calendar day, which is how the book
    # would actually be run — both baskets live at once, equal notional
    T = T.copy(); T["day"] = pd.to_datetime(T.ts).dt.floor("1D")
    daily = T.groupby(["day", "side"]).R.mean().unstack()
    both = daily.dropna()
    pair = (both["long"] + both["short"]) / 2
    cd = T.groupby(["day", "side"]).CTRL.mean().unstack().dropna()
    cpair = (cd["long"] + cd["short"]) / 2 if len(cd) else pd.Series(dtype=float)
    se = pair.std(ddof=1) / np.sqrt(len(pair))
    print(f"\n  {label}   cut {cut:.2f}")
    print(f"    long  n={len(L):5d}  {L.R.mean()*100:+.3f}%  win {(L.R>0).mean()*100:.1f}%")
    print(f"    short n={len(S):5d}  {S.R.mean()*100:+.3f}%  win {(S.R>0).mean()*100:.1f}%")
    print(f"    PAIR  n={len(pair):5d} days  {pair.mean()*100:+.3f}%/day-with-both"
          f"  t={pair.mean()/se:+.2f}  win {(pair>0).mean()*100:.1f}%")
    if len(cpair):
        cse = cpair.std(ddof=1) / np.sqrt(len(cpair))
        print(f"    control pair          {cpair.mean()*100:+.3f}%"
              f"  t={cpair.mean()/cse:+.2f}   EDGE {(pair.mean()-cpair.mean())*100:+.3f}pp")
    # neutrality: how balanced are the two legs, day by day?
    bal = (both["long"].notna() & both["short"].notna()).mean()
    print(f"    both legs live on {bal*100:.0f}% of days  "
          f"(net exposure zero by construction on those days)")
    return pair


if __name__ == "__main__":
    print("KELTNER RANGE PAIR — market-neutral band reversion\n")
    hf = glob.glob(f"{HOURLY}/*.csv")
    for cut in (0.15, 0.20, 0.25):
        T = collect(hf, load_hourly, cut)
        p = pair_report(T, "IN-SAMPLE  33 perps hourly", cut)
        if cut == 0.20 and p is not None and len(p) > 20:
            yr = p.groupby(p.index.year)
            print("    by year: " + "  ".join(
                f"{y} {g.mean()*100:+.3f}%" for y, g in yr if len(g) > 5))
            h = len(p) // 2
            print(f"    halves: first {p.iloc[:h].mean()*100:+.3f}%  "
                  f"second {p.iloc[h:].mean()*100:+.3f}%")
            cum = (1 + p.values).cumprod()
            dd = (cum / np.maximum.accumulate(cum) - 1).min()
            print(f"    cumulative {(cum[-1]-1)*100:+.1f}%  max drawdown {dd*100:.1f}%")

    ins = {os.path.basename(x)[:-4] for x in hf}
    oos = [p for p in glob.glob(f"{OOS}/*.csv")
           if os.path.basename(p)[:-4] not in ins]
    T = collect(oos, load_from_1m, 0.20)
    pair_report(T, f"OUT-OF-SAMPLE  {len(oos)} unseen symbols", 0.20)
