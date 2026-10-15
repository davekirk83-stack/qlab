"""
THE ANATOMY OF A RANGE WINDOW — when they happen, how long they last, what
the other instruments read while they are open.

DK: "Can you identify past occasions where this works, and any pattern between
     them or what the indicators read during those windows?"
    "How long on average they last for? When typically they occur during a
     session/day/week/month etc?"

regime_detect.py found the detector: CONTAINMENT, the share of the last 50
bars whose close sat inside the Keltner bands. Above its own median it is
worth +0.197% a trade over trading in the other state - the widest gap of
nine candidates, and the opposite sign to the volatility filter the book
currently uses.

That answers WHICH instrument. This answers WHAT THE STATE LOOKS LIKE, which
is the part a human needs to recognise it on a chart.

  1. EPISODES. Every contiguous run of the containment state, per symbol, with
     the book's actual P&L earned inside it. Duration distribution, and the
     split between the episodes that made money and those that lost.

  2. THE CLOCK. Hour of day in London time, day of week, day of month, and the
     three trading sessions - Asia, London, New York - measured as the share of
     bars in range and the book's return inside each.

  3. THE INSTRUMENT PANEL. What all nine detectors read during a profitable
     range window versus an unprofitable one versus no window at all. This is
     the part that turns a statistic into something recognisable: if the good
     windows share a signature across several instruments, that signature is a
     better switch than containment alone.

  4. THE EXTREMES. The ten best and ten worst episodes by P&L, dated, so the
     pattern can be checked against what was actually happening in the market.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

NAMES = ["eff","rvol","bandw","adx","autocorr","varratio","touches","contain","hurst"]
SESSIONS = [("Asia", 0, 7), ("London", 7, 13), ("NY", 13, 21), ("late", 21, 24)]


def episodes(data):
    """Every contiguous containment window, with the book's P&L inside it."""
    eps = []; panel = []
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        med = v.expanding(500).median()
        allow = (v > med).values
        if np.isfinite(allow).sum() < 500: continue
        # P&L bar by bar, so it can be attributed to the episode it fell in
        res = RD.run_book_timed(d, allow, ema, lo_b, hi_b, a)
        pnl = pd.Series(0.0, index=range(len(d)))
        for i, r in res: pnl.iloc[i] += r
        al = pd.Series(allow)
        grp = (al != al.shift()).cumsum()
        for _, g in al.groupby(grp):
            if not g.iloc[0]: continue
            i0, i1 = g.index[0], g.index[-1]
            eps.append({"sym": s, "start": d.index[i0], "end": d.index[i1],
                        "bars": len(g), "pnl": float(pnl.iloc[i0:i1+1].sum()),
                        "ntr": int((pnl.iloc[i0:i1+1] != 0).sum())})
        # instrument panel, sampled every 8 bars to keep it manageable
        state = np.where(allow, 1, 0)
        for i in range(250, len(d)-1, 8):
            row = {"state": state[i], "pnl": float(pnl.iloc[i]),
                   "ts": d.index[i], "sym": s}
            for nm in NAMES: row[nm] = D[nm][i]
            panel.append(row)
    return pd.DataFrame(eps), pd.DataFrame(panel)


if __name__ == "__main__":
    data = RD.load()
    E, P = episodes(data)
    E = E[E.ntr > 0].copy()
    print(f"{len(data)} symbols. {len(E):,} containment windows that contained "
          f"at least one trade.\n")

    print("="*82)
    print("1. HOW LONG THEY LAST")
    print("="*82)
    q = E.bars.quantile([.25, .5, .75, .9, .99])
    print(f"  mean      {E.bars.mean():>6.0f} bars  = {E.bars.mean()*15/60:>5.1f} hours")
    print(f"  median    {q[.5]:>6.0f} bars  = {q[.5]*15/60:>5.1f} hours")
    print(f"  25th pct  {q[.25]:>6.0f} bars        75th pct {q[.75]:>5.0f} bars "
          f"= {q[.75]*15/60:.1f} hours")
    print(f"  90th pct  {q[.9]:>6.0f} bars  = {q[.9]*15/60:>5.1f} hours")
    print(f"  99th pct  {q[.99]:>6.0f} bars  = {q[.99]*15/60:>5.1f} hours")
    print(f"\n  {'duration':<18}{'windows':>9}{'share':>8}{'total P&L':>12}"
          f"{'mean P&L':>11}{'win rate':>10}")
    E["dur"] = pd.cut(E.bars, [0, 8, 24, 48, 96, 10**6],
                      labels=["<=2h", "2-6h", "6-12h", "12-24h", ">24h"])
    for b, g in E.groupby("dur", observed=True):
        print(f"  {str(b):<18}{len(g):>9}{len(g)/len(E)*100:>7.0f}%"
              f"{g.pnl.sum()*100:>+11.1f}%{g.pnl.mean()*100:>+10.3f}%"
              f"{(g.pnl>0).mean()*100:>9.0f}%")

    print("\n" + "="*82)
    print("2. WHEN THEY HAPPEN  (all times London)")
    print("="*82)
    P["lon"] = P.ts.dt.tz_convert("Europe/London")
    P["hour"] = P.lon.dt.hour; P["dow"] = P.lon.dt.dayofweek
    P["dom"] = P.lon.dt.day; P["mon"] = P.lon.dt.month
    def clock(col, labels, title):
        print(f"\n  {title}")
        print(f"  {'':<12}{'% of bars in range':>20}{'book P&L per bar':>20}"
              f"{'relative':>11}")
        base = P.state.mean()
        for k in sorted(P[col].unique()):
            g = P[P[col] == k]
            if len(g) < 200: continue
            lab = labels[k] if isinstance(labels, dict) else str(k)
            rel = g.state.mean()/base if base > 0 else np.nan
            gp = g[g.state == 1]
            print(f"  {lab:<12}{g.state.mean()*100:>19.0f}%"
                  f"{gp.pnl.mean()*100:>+19.4f}%{rel:>10.2f}x")
    clock("hour", {h: f"{h:02d}:00" for h in range(24)}, "BY HOUR OF DAY")
    clock("dow", {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
                  4:"Friday",5:"Saturday",6:"Sunday"}, "BY DAY OF WEEK")
    print("\n  BY SESSION")
    print(f"  {'':<12}{'% of bars in range':>20}{'book P&L per bar':>20}{'relative':>11}")
    base = P.state.mean()
    for nm, h0, h1 in SESSIONS:
        g = P[(P.hour >= h0) & (P.hour < h1)]
        if len(g) < 200: continue
        gp = g[g.state == 1]
        print(f"  {nm:<12}{g.state.mean()*100:>19.0f}%{gp.pnl.mean()*100:>+19.4f}%"
              f"{g.state.mean()/base:>10.2f}x")
    print("\n  BY WEEK OF MONTH")
    P["wom"] = ((P.dom-1)//7+1).clip(upper=5)
    print(f"  {'':<12}{'% of bars in range':>20}{'book P&L per bar':>20}{'relative':>11}")
    for k in sorted(P.wom.unique()):
        g = P[P.wom == k]
        if len(g) < 200: continue
        gp = g[g.state == 1]
        print(f"  {'week '+str(k):<12}{g.state.mean()*100:>19.0f}%"
              f"{gp.pnl.mean()*100:>+19.4f}%{g.state.mean()/base:>10.2f}x")

    print("\n" + "="*82)
    print("3. THE INSTRUMENT PANEL — what everything reads in each state")
    print("="*82)
    print("  Each detector is signed so HIGHER ALWAYS MEANS MORE RANGE-LIKE.")
    print("  Values are percentiles within each symbol's own history, so they")
    print("  are comparable across instruments and across coins.\n")
    for nm in NAMES:
        P[nm+"_p"] = P.groupby("sym")[nm].rank(pct=True)
    good = P[(P.state == 1) & (P.pnl > 0)]
    bad  = P[(P.state == 1) & (P.pnl < 0)]
    off  = P[P.state == 0]
    print(f"  {'detector':<12}{'PROFITABLE range':>19}{'LOSING range':>16}"
          f"{'not in range':>16}{'good - bad':>13}")
    sig = []
    for nm in NAMES:
        g, b, o = good[nm+"_p"].mean(), bad[nm+"_p"].mean(), off[nm+"_p"].mean()
        sig.append((nm, g, b, o, g-b))
        print(f"  {nm:<12}{g*100:>18.0f}{b*100:>16.0f}{o*100:>16.0f}{(g-b)*100:>+12.0f}")
    sig.sort(key=lambda z: -abs(z[4]))
    print(f"\n  Biggest separator of GOOD range windows from BAD ones: {sig[0][0]}"
          f" ({sig[0][4]*100:+.0f} percentile points)")

    print("\n" + "="*82)
    print("4. THE EXTREMES — biggest and worst windows, dated")
    print("="*82)
    E = E.sort_values("pnl", ascending=False)
    print(f"\n  TEN BEST\n  {'symbol':<14}{'opened':<20}{'bars':>6}{'hours':>7}"
          f"{'trades':>8}{'P&L':>10}")
    for _, r in E.head(10).iterrows():
        print(f"  {r['sym']:<14}{str(r['start'])[:16]:<20}{r['bars']:>6}"
              f"{r['bars']*15/60:>7.1f}{r['ntr']:>8}{r['pnl']*100:>+9.2f}%")
    print(f"\n  TEN WORST\n  {'symbol':<14}{'opened':<20}{'bars':>6}{'hours':>7}"
          f"{'trades':>8}{'P&L':>10}")
    for _, r in E.tail(10).iloc[::-1].iterrows():
        print(f"  {r['sym']:<14}{str(r['start'])[:16]:<20}{r['bars']:>6}"
              f"{r['bars']*15/60:>7.1f}{r['ntr']:>8}{r['pnl']*100:>+9.2f}%")
    print(f"\n  {(E.pnl>0).mean()*100:.0f}% of windows profitable. "
          f"Best {E.pnl.max()*100:+.1f}%, worst {E.pnl.min()*100:+.1f}%. "
          f"Top 10% of windows earn {E.pnl.nlargest(max(len(E)//10,1)).sum()/E.pnl.sum()*100:.0f}% of total P&L.")
    E.to_csv("/home/claude/qlab/runs/range_episodes.csv", index=False)
    print("\n  All windows written to runs/range_episodes.csv")
