"""
THE EQUITY SHORT — directional, bear-armed. Item 1 of doc 75.

DK, 16 Oct: "We still need to grapple with a real shorting strategy ... Stocks,
however, I think are going to get battered soon ... we need to be ready for
when that change happens."

Every directional short tried so far failed, all on crypto. Equities have what
crypto lacks: two full bears (2008, 2022) inside 20 years of daily bars on
disk. This is time-series momentum, short side only, the classic bear-market
earner, tested the way everything else here is tested.

THE TRADE (one row per episode, return on the capital committed)
  entry   the first close below the instrument's own 10-month (210-day) average
  exit    the first close back above it, or the time stop
  cost    2bp a side, plus stock borrow at 1%/yr pro rata

VARIANTS
  trend          as above, no other condition
  trend+mom      also require 12-month momentum < 0
  trend 60d      with a 60-trading-day time stop
  ARMED          the trend short, but only while SPY itself is below its
                 10-month average - the crash watch's own signal. This is the
                 one DK is asking for: a short that switches itself on when
                 the market turns rather than on a view.

CONTROL  for every real episode, a random entry in the same instrument held for
         the same number of days, shorted. Same geometry, no signal.

Reported overall, and for 2008 and 2022 separately, so one crash cannot carry
it. Both panels: 79 stocks (survivorship-light, doc 72) and 37 ETFs.
"""
import warnings; warnings.filterwarnings("ignore")
import glob, os
import numpy as np, pandas as pd

COST = 2/10000; BORROW = 0.01
RNG = np.random.default_rng(11)


def load(folder):
    out = {}
    for f in sorted(glob.glob(f"/home/claude/qlab/{folder}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        if s == "PARA": continue   # merger stub at the end of the series
        if len(d) > 800: out[s] = d.close.astype(float)
    return out


def episodes(px, gate=None, mom=False, maxhold=None, sym=""):
    p = px.dropna(); sma = p.rolling(210).mean()
    below = (p < sma)
    if mom: below &= (p / p.shift(252) - 1 < 0)
    if gate is not None: below &= gate.reindex(p.index).fillna(False).astype(bool)
    b = below.values; rows = []; i = 210
    n = len(p)
    while i < n - 1:
        if b[i] and not b[i-1]:
            e = i + 1  # enter next open ~ next close here (daily, conservative: next close)
            if e >= n: break
            j = e
            while j < n - 1:
                j += 1
                if not b[j] or (maxhold and j - e >= maxhold): break
            entry, exit_ = p.iloc[e], p.iloc[j]
            days = j - e
            r = (entry * (1 - COST) - exit_ * (1 + COST)) / entry - BORROW * days / 252
            rows.append((sym, p.index[e], p.index[j], r, days))
            i = j
        i += 1
    return rows


def control(px, real, sym=""):
    p = px.dropna(); n = len(p); rows = []
    for _, _, _, _, days in real:
        if days < 1 or n - days - 2 <= 211: continue
        e = int(RNG.integers(211, n - days - 1)); j = e + days
        entry, exit_ = p.iloc[e], p.iloc[j]
        r = (entry * (1 - COST) - exit_ * (1 + COST)) / entry - BORROW * days / 252
        rows.append((sym, p.index[e], p.index[j], r, days))
    return rows


def table(name, R, C):
    R = pd.DataFrame(R, columns=["sym", "entry", "exit", "ret", "days"])
    C = pd.DataFrame(C, columns=["sym", "entry", "exit", "ret", "days"])
    R["y"] = R.entry.dt.year; C["y"] = C.entry.dt.year
    def line(lbl, g, c):
        if len(g) < 20: print(f"    {lbl:<14} n={len(g):<5} too few"); return
        t = g.ret.mean() / (g.ret.std(ddof=1) / np.sqrt(len(g)))
        ct = c.ret.mean() if len(c) else np.nan
        print(f"    {lbl:<14}{len(g):>6}{g.ret.mean()*100:>+9.2f}%{t:>+7.2f}{(g.ret>0).mean()*100:>6.0f}%"
              f"{g.days.median():>7.0f}d{g.ret.sum()*100:>+9.0f}%{ct*100:>+10.2f}%{(g.ret.mean()-ct)*100:>+9.2f}")
    print(f"  {name}")
    print(f"    {'window':<14}{'n':>6}{'per ep':>10}{'t':>7}{'win':>7}{'hold':>8}{'total':>9}{'control':>11}{'edge':>9}")
    line("all", R, C)
    for y in (2008, 2022):
        line(str(y), R[R.y == y], C[C.y == y])
    line("ex 2008/2022", R[~R.y.isin([2008, 2022])], C[~C.y.isin([2008, 2022])])
    line("2023-2026", R[R.y >= 2023], C[C.y >= 2023])
    return R


if __name__ == "__main__":
    spy = load("data_etf20")["SPY"]
    spy_gate = (spy < spy.rolling(210).mean())
    for folder, label in (("data_stocks20", "79 STOCKS"), ("data_etf20", "37 ETFs")):
        P = load(folder)
        print("=" * 100); print(f"{label}, daily, 2001-2026, short side only"); print("=" * 100)
        for vname, kw in (("trend", {}), ("trend+mom", {"mom": True}), ("trend 60d", {"maxhold": 60}),
                          ("ARMED (SPY < 10m avg)", {"gate": spy_gate})):
            R, C = [], []
            for s, px in P.items():
                r = episodes(px, sym=s, **kw); R += r; C += control(px, r, sym=s)
            table(vname, R, C)
            print()
    print("  Benchmark: the range book's SHORT side on the same stocks earned +0.46%/episode overall,")
    print("  +7.5% in 2008 and +2.1% in 2022 (doc 72), holding a median 24 days.")
