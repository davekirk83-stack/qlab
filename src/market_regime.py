"""
IS THERE A MARKET-WIDE RANGE SEASON? — DK's diagnostic, built properly.

DK: "If you can study enough periods where our system would have worked
     historically, I would imagine that calendar / time / session patterns
     might exist and that the indicators would have something to say as well
     to use as a general diagnostic."

Doc 106 looked for calendar structure across ALL range windows and found it
flat - 38-53% of bars ranging in every hour of the day, 40-49% on every
weekday. But that asked the wrong question. It asked WHEN DOES A RANGE EXIST,
which is a property of each coin on its own. DK is asking WHEN DOES THE BOOK
WORK, which may be a property of the whole market at once.

There is already a reason to think it is. The three worst windows in seven
years - TIA, SUI and ARB - opened within forty-five minutes of each other on
one day. That is not three coins each having a bad range. That is one market
event arriving everywhere, and it means the unit of analysis should be the
DAY ACROSS ALL SYMBOLS, not the window on one symbol.

FOUR QUESTIONS

  1. BREADTH AS AN INDEX. On each bar, what share of the 49 symbols is in a
     containment range at the same time? If that index swings between broad
     range-seasons and broad trend-seasons, it is a market-wide regime signal
     and the single most useful diagnostic this book could have.

  2. DOES THE INDEX PREDICT PROFIT? Split days by the index reading at the
     START of the day - causal, no peeking - and compare what the book earned.
     An index that describes the day is useless; one that forecasts it is a
     dashboard.

  3. DOES A GOOD PERIOD PERSIST? Autocorrelation of daily P&L and of the
     index. A range season you can only identify after it ends cannot be
     traded. If today's reading says something about next week, it can.

  4. THE CALENDAR, ASKED THE RIGHT WAY. Month, week of month, weekday and
     session - but measured on the BOOK'S DAILY P&L rather than on whether a
     range existed. And the market-wide instruments alongside it: BTC trend,
     aggregate volatility, cross-sectional dispersion.

Worst-tick break fills, containment at its own median, per the registered book.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48


def per_bar(d, allow, ema, lo_b, hi_b, a):
    """Book P&L attributed to the bar it was booked on."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); pnl = np.zeros(n); inv = []; oi = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            sz = sum(x for _, x in inv); cost = sum(p*x for p, x in inv)/sz
            pnl[i] += (L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(x for _, x in inv); sell = min(sz*frac, sz)
                    cost = sum(p*x for p, x in inv)/sz
                    pnl[i] += ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz)
                    sold.add(k)
                    inv = [(p, x*(1-sell/sz)) for p, x in inv]
                    inv = [(p, x) for p, x in inv if x > 1e-9]
                    if not inv: sold = set()
        held = sum(x for _, x in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: oi = i
    return pnl


if __name__ == "__main__":
    data = RD.load()
    P, S = {}, {}
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        al = (v > v.expanding(500).median()).values
        P[s] = pd.Series(per_bar(d, al, ema, lo_b, hi_b, a), index=d.index)
        S[s] = pd.Series(al.astype(float), index=d.index)
    PN = pd.DataFrame(P).sort_index()
    ST = pd.DataFrame(S).sort_index()
    print(f"{len(data)} symbols, {len(PN):,} bars.\n")

    # ---------- 1. breadth index ----------
    breadth = ST.mean(axis=1)
    dpnl = PN.sum(axis=1).resample("1D").sum()
    dbr = breadth.resample("1D").mean()
    J = pd.concat([dpnl.rename("pnl"), dbr.rename("br")], axis=1).dropna()
    J = J[J.index >= J.index[5]]
    print("="*88)
    print("1. RANGE BREADTH — share of the market ranging at the same time")
    print("="*88)
    print(f"  mean {breadth.mean()*100:.0f}%   "
          f"10th pct {breadth.quantile(.1)*100:.0f}%   "
          f"90th pct {breadth.quantile(.9)*100:.0f}%   "
          f"min {breadth.min()*100:.0f}%   max {breadth.max()*100:.0f}%")
    print(f"  If this only ever sat near 50% there would be no market-wide")
    print(f"  regime to find. The spread above is how much there is to work with.")

    # ---------- 2. does it predict ----------
    J["br_y"] = J.br.shift(1)                       # yesterday's reading
    Jd = J.dropna()
    print("\n" + "="*88)
    print("2. DOES YESTERDAY'S BREADTH PREDICT TODAY'S P&L?")
    print("="*88)
    print(f"  {'yesterday breadth':<26}{'days':>7}{'P&L per day':>14}"
          f"{'win rate':>11}{'worst day':>12}")
    Jd["q"] = pd.qcut(Jd.br_y, 4, labels=["lowest", "low", "high", "highest"])
    for b, g in Jd.groupby("q", observed=True):
        print(f"  {str(b):<26}{len(g):>7}{g.pnl.mean()*100:>+13.2f}%"
              f"{(g.pnl>0).mean()*100:>10.0f}%{g.pnl.min()*100:>+11.1f}%")
    print(f"\n  correlation, yesterday's breadth vs today's P&L: "
          f"{Jd.br_y.corr(Jd.pnl):+.3f}")
    print(f"  correlation, SAME-day breadth vs same-day P&L:    "
          f"{Jd.br.corr(Jd.pnl):+.3f}   (describes, cannot be traded)")

    # ---------- 3. persistence ----------
    print("\n" + "="*88)
    print("3. DOES A GOOD PERIOD PERSIST?")
    print("="*88)
    print(f"  {'lag':<10}{'breadth autocorr':>20}{'daily P&L autocorr':>22}")
    for lag in (1, 2, 5, 10, 20):
        print(f"  {str(lag)+' day' + ('s' if lag>1 else ''):<10}"
              f"{J.br.autocorr(lag):>+20.3f}{J.pnl.autocorr(lag):>+22.3f}")
    print("\n  Breadth persisting while P&L does not means the REGIME is")
    print("  forecastable even though the daily result is not — which is")
    print("  exactly what a position-sizing dial needs.")

    # ---------- 4. calendar, on P&L ----------
    print("\n" + "="*88)
    print("4. THE CALENDAR, MEASURED ON THE BOOK'S P&L (London time)")
    print("="*88)
    D2 = J.copy()
    lon = D2.index.tz_convert("Europe/London")
    D2["dow"] = lon.dayofweek; D2["mon"] = lon.month
    D2["wom"] = np.clip((lon.day-1)//7+1, None, 5)
    for col, lab, title in (
        ("dow", {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
                 4:"Friday",5:"Saturday",6:"Sunday"}, "BY WEEKDAY"),
        ("wom", {i:f"week {i}" for i in range(1,6)}, "BY WEEK OF MONTH"),
        ("mon", {i:pd.Timestamp(2025,i,1).strftime("%B") for i in range(1,13)},
         "BY MONTH")):
        print(f"\n  {title}")
        print(f"  {'':<12}{'days':>7}{'P&L per day':>14}{'win rate':>11}"
              f"{'breadth':>10}")
        for k in sorted(D2[col].unique()):
            g = D2[D2[col] == k]
            if len(g) < 8: continue
            print(f"  {lab.get(k,str(k)):<12}{len(g):>7}{g.pnl.mean()*100:>+13.2f}%"
                  f"{(g.pnl>0).mean()*100:>10.0f}%{g.br.mean()*100:>9.0f}%")

    # ---------- market-wide instruments ----------
    print("\n" + "="*88)
    print("5. WHAT THE MARKET-WIDE INSTRUMENTS READ ON GOOD DAYS vs BAD")
    print("="*88)
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    idx = (C/C.ffill().bfill().iloc[0]).mean(axis=1)
    di = idx.resample("1D").last().ffill()
    inst = pd.DataFrame({
        "mkt trend (20d)": di.pct_change(20),
        "mkt vol (20d)":   di.pct_change().rolling(20).std(),
        "dispersion":      C.pct_change().resample("1D").last().std(axis=1),
        "breadth":         dbr,
    }).reindex(J.index).dropna()
    K = J.join(inst, how="inner").dropna()
    good = K[K.pnl > K.pnl.quantile(0.8)]
    bad = K[K.pnl < K.pnl.quantile(0.2)]
    print(f"  {'instrument':<20}{'BEST 20% of days':>20}{'WORST 20%':>16}"
          f"{'all days':>14}")
    for c in inst.columns:
        print(f"  {c:<20}{good[c].mean():>20.5f}{bad[c].mean():>16.5f}"
              f"{K[c].mean():>14.5f}")
    print(f"\n  {len(K):,} days. If an instrument reads clearly differently on")
    print("  the best days than the worst, it belongs on the dashboard.")
