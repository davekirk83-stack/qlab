"""
THE SHORT SIDE — three of DK's questions at once.

  "Can't we just make money from picking shitcoins that are most likely to die
   after their initial spike?"
  "Leaving runners on 'losers' could be very profitable."
  "were you able to establish good conditions for short trades too? Being able
   to short would potentially double our trades if we work both sides."

The premise is sound: 211 of 300 products are down more than 90% from their
peak, median -95%. Something made them fall.

TEST A - SHORT AFTER A SPIKE, swept over spike size, window, hold and stop,
including long holds because DK's point is about letting the short RUN.

TEST B - THE MARKET-GATE MIRROR. The long book only trades when the
equal-weight index is above its 200-day mean. The obvious question is whether
the inverse state is a short regime rather than merely a no-trade state. If it
is, the same machinery works both sides and the trade count doubles.

WHAT COULD KILL IT, measured rather than assumed:
  BORROW   you cannot short what nobody lends. Perpetuals cover perhaps
           30-100 major names, not 300 micro-caps. Everything is therefore
           also run on the liquid quartile as the honest "has a perp" proxy.
  THE TAIL a short that goes 10x against you at 3x leverage is a liquidation,
           not a loss. Worst single trades and liquidation counts are
           reported, never just the average.
  FUNDING  charged at 0.01%/8h = 0.03%/day against the short, the usual
           neutral rate.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

MAKER, TAKER, SLIP = 2/10000, 5/10000, 10/10000
FUNDING_DAY = 0.0003


def load():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        d = pd.read_csv(p)
        if len(d) < 300: continue
        d.index = pd.to_datetime(d.t, unit="ms")
        out[os.path.basename(p)[:-4]] = d[["open", "high", "low", "close", "volume"]].sort_index()
    return out


def short_after_spike(data, up, win, hold, stop_pct, keep=None):
    rows = []
    for s, d in data.items():
        if keep is not None and s not in keep: continue
        C = d.close.values; H = d.high.values; n = len(C)
        run = pd.Series(C).pct_change(win).values
        last = -10**9
        for i in range(win+1, n-hold-1):
            if not np.isfinite(run[i]) or run[i] < up: continue
            if i - last < hold: continue
            last = i
            e = C[i]*(1-MAKER); stop = C[i]*(1+stop_pct)
            out = None; q = i
            for q in range(i+1, min(i+1+hold, n)):
                if H[q] >= stop:
                    out = 1 - (stop*(1+SLIP+TAKER))/e; break
            if out is None:
                q = min(i+hold, n-1); out = 1 - (C[q]*(1+MAKER))/e
            rows.append((s, d.index[i], out - FUNDING_DAY*(q-i), run[i]))
    if not rows: return None
    return pd.DataFrame(rows, columns=["sym", "ts", "ret", "spike"])


def gate_series(data):
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    C = C[C.notna().sum(axis=1) >= 8]
    idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
    return (idx > idx.rolling(200).mean()).shift(1)


def short_band_touch(data, gate, when_gate, hold=16, t_atr=0.5, s_atr=3.0):
    """The mirror of the long book: short the UPPER band in the chosen regime."""
    rows = []
    g = gate.to_dict()
    for s, d in data.items():
        C = d.close.values; H = d.high.values; L = d.low.values; n = len(C)
        pc = np.roll(C, 1); pc[0] = C[0]
        tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
        a = pd.Series(tr).rolling(14).mean().bfill().values
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        upper = ema + 2*a
        net = np.abs(pd.Series(C).diff(100)).values
        gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(100).sum().values
        eff = net/np.where(gross > 0, gross, np.nan)
        trig = (C >= upper) & (np.roll(C, 1) < np.roll(upper, 1)) & (eff < 0.30)
        last = -10**9
        for i in np.flatnonzero(trig):
            if i < 120 or i > n-hold-2 or i-last < hold: continue
            if g.get(d.index[i], None) != when_gate: continue
            last = i
            if not np.isfinite(a[i]) or a[i] <= 0: continue
            e = C[i]*(1-MAKER); stop = C[i]+s_atr*a[i]; tgt = C[i]-t_atr*a[i]
            out = None; q = i
            for q in range(i+1, min(i+1+hold, n)):
                if H[q] >= stop: out = 1-(stop*(1+SLIP+TAKER))/e; break
                if L[q] <= tgt:  out = 1-(tgt*(1+MAKER))/e; break
            if out is None:
                q = min(i+hold, n-1); out = 1-(C[q]*(1+MAKER))/e
            rows.append((s, d.index[i], out - FUNDING_DAY*(q-i)))
    if not rows: return None
    return pd.DataFrame(rows, columns=["sym", "ts", "ret"])


def summarise(T, tag, lev=3):
    if T is None or len(T) < 40:
        print(f"  {tag:<40}too few"); return
    m = T.ret.mean(); t = m/(T.ret.std(ddof=1)/np.sqrt(len(T)))
    liq = (T.ret < -1/lev).mean()
    print(f"  {tag:<40}n={len(T):>5}  {m*100:>+7.2f}%  t={t:>+6.2f}  "
          f"win {(T.ret>0).mean()*100:>3.0f}%  worst {T.ret.min()*100:>+8.1f}%  "
          f"liquidated at {lev}x {liq*100:>4.1f}%")


if __name__ == "__main__":
    data = load()
    liq = pd.Series({s: (d.close*d.volume).tail(60).median() for s, d in data.items()})
    cut = liq.quantile(0.75)
    keep = set(liq[liq >= cut].index)
    print(f"{len(data)} products. 'Has a perp' proxy = liquid quartile, "
          f">=${cut:,.0f}/day: {len(keep)} products\n")

    print("=" * 104)
    print("TEST A — SHORT AFTER A SPIKE, letting it run")
    print(f"  {'setup':<40}{'n':>7}{'mean':>10}{'t':>9}{'win':>7}{'worst':>11}{'liq@3x':>16}")
    best = None
    for up in (0.5, 1.0, 2.0):
        for win in (7, 30):
            for hold in (30, 90, 180):
                for sp in (0.5, 1.0):
                    T = short_after_spike(data, up, win, hold, sp)
                    if T is None or len(T) < 60: continue
                    m = T.ret.mean()
                    summarise(T, f"+{up*100:.0f}% in {win}d, hold {hold}d, stop {sp*100:.0f}%")
                    if best is None or m > best[0]: best = (m, up, win, hold, sp, T)

    if best:
        m, up, win, hold, sp, T = best
        print(f"\n  BEST: short after +{up*100:.0f}% in {win}d, hold {hold}d, "
              f"stop {sp*100:.0f}%  ->  {m*100:+.2f}%/trade")
        TL = short_after_spike(data, up, win, hold, sp, keep=keep)
        summarise(TL, "  same, liquid quartile only")
        T["yr"] = T.ts.dt.year
        print("\n  by year:")
        for y, g in T.groupby("yr"):
            if len(g) < 20: continue
            print(f"    {y}  n={len(g):>4}  {g.ret.mean()*100:>+7.2f}%  "
                  f"win {(g.ret>0).mean()*100:>3.0f}%  worst {g.ret.min()*100:>+7.1f}%")

    print("\n" + "=" * 104)
    print("TEST B — IS THE GATE'S 'OFF' STATE A SHORT REGIME?")
    print("  The long book stands aside when the index is below its 200d mean.")
    print("  If that state is tradeable from the short side, trade count doubles.\n")
    gate = gate_series(data)
    for when, lbl in ((False, "gate OFF (index below its 200d mean)"),
                      (True,  "gate ON  (index above) — control")):
        T = short_band_touch(data, gate, when)
        summarise(T, lbl)
