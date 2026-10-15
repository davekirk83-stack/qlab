"""
QUIET VERSUS LOUD, ON THE EQUITY CURVE — the metric that actually decides it.

DK: "I maintain that the quiet ranging environment will be safest and most
     profitable overall for 15min chart with fewer draw downs."

He has named the right measure and I had been arguing from the wrong one. Per
-trade return cannot see loss clustering: it averages a day on which five
positions all broke together with five quiet days that each lost once, and
reports the same number. The equity curve cannot do that, because the five
simultaneous losses compound against a stack that has not had time to recover.

There is already evidence in this project's own output that the clustering is
real. The three worst range windows in seven years - TIA, SUI and ARB - all
opened within forty-five minutes of each other on 14 October 2025. Different
coins, one event. And the loud-window tail is -51% of posted margin at 3x. A
tail like that does not need to be frequent to end an account; it needs to
arrive on several positions at once, which is exactly what that day shows it
does.

THE TEST. The same range book, run on three regimes, through a portfolio
simulator with finite slots and real capital:

  quiet   realised volatility in the bottom third of the symbol's history
  loud    top third
  all     no volatility filter at all

reported as CAGR, maximum drawdown, Sharpe, time under water, and the worst
single day - the measures that answer "safest and most profitable overall".

AND AT MATCHED RISK. Loud trades are roughly twice the size of quiet ones in
risk terms, so running both at the same notional flatters loud. The second
table sizes every position inversely to its volatility at entry, which is
what anyone trading this would actually do, and asks the question again.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
START = 2000.0


def trades(d, allow, ema, lo_b, hi_b, a, rvp, sym):
    """Each trade with entry time, exit time, return and vol bucket."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    out = []; inv = []; opened_i = 0; sold = set(); v0 = np.nan
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-opened_i >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            # conservative fill: the worst tick in the bar, per the break-cost test
            out.append((sym, d.index[opened_i], d.index[i],
                        (L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, v0))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((sym, d.index[opened_i], d.index[i],
                                ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), v0))
                    sold.add(k)
                    inv = [(p, s*(1-sell/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: sold = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: opened_i = i; v0 = rvp[i]
    return out


def simulate(S, slots, lev, risk_parity=False):
    """Finite slots, real capital, positions compounding against one stack."""
    S = S.sort_values("entry").reset_index(drop=True)
    eq = START; open_pos = []; curve = []
    events = sorted(set(S.entry) | set(S.exit))
    ei = 0
    for t in events:
        # close anything due
        still = []
        for p in open_pos:
            if p["exit"] <= t:
                eq += p["margin"]*p["ret"]*lev*p["scale"]
            else: still.append(p)
        open_pos = still
        if eq <= 0: return None
        while ei < len(S) and S.entry.iloc[ei] <= t:
            r = S.iloc[ei]; ei += 1
            if len(open_pos) >= slots: continue
            sc = 1.0
            if risk_parity and np.isfinite(r["vol"]):
                # halve size in the top vol third, double in the bottom
                sc = 1.5 if r["vol"] < 1/3 else (0.5 if r["vol"] > 2/3 else 1.0)
            open_pos.append({"exit": r["exit"], "ret": r["ret"],
                             "margin": eq/slots, "scale": sc})
        curve.append((t, eq))
    if not curve: return None
    E = pd.Series([c[1] for c in curve], index=[c[0] for c in curve])
    E = E[~E.index.duplicated(keep="last")]
    yrs = (E.index[-1]-E.index[0]).days/365.25
    if yrs <= 0 or E.iloc[-1] <= 0: return None
    cagr = (E.iloc[-1]/START)**(1/yrs)-1
    dd = (E/E.cummax()-1).min()
    dly = E.resample("1D").last().ffill().pct_change().dropna()
    sh = dly.mean()/dly.std()*np.sqrt(365) if dly.std() > 0 else np.nan
    uw = float((E < E.cummax()).mean())
    return {"cagr": cagr, "dd": dd, "sharpe": sh, "final": E.iloc[-1],
            "worst_day": dly.min(), "uw": uw, "n": len(E)}


if __name__ == "__main__":
    data = RD.load()
    allt = []
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        allow = (v > v.expanding(500).median()).values
        rv = pd.Series(d.close.values).pct_change().rolling(60).std()
        allt += trades(d, allow, ema, lo_b, hi_b, a, rv.rank(pct=True).values, s)
    S = pd.DataFrame(allt, columns=["sym", "entry", "exit", "ret", "vol"])
    S = S[np.isfinite(S.ret)].copy()
    print(f"{len(data)} symbols, {len(S):,} trades, conservative fills "
          f"(break exits at the worst tick in the bar).\n")

    REG = {"quiet  (bottom third vol)": S[S.vol < 1/3],
           "middle third":              S[(S.vol >= 1/3) & (S.vol < 2/3)],
           "loud   (top third vol)":    S[S.vol >= 2/3],
           "no filter  (all trades)":   S}
    for lev in (1, 3):
        print("="*94)
        print(f"EQUITY CURVE — 40 slots, {lev}x leverage, $2,000 start")
        print("="*94)
        print(f"  {'regime':<28}{'trades':>8}{'per trade':>11}{'CAGR':>9}"
              f"{'maxDD':>9}{'Sharpe':>8}{'worst day':>11}{'under water':>13}{'final':>12}")
        for lbl, G in REG.items():
            if len(G) < 200: continue
            r = simulate(G, 40, lev)
            if r is None:
                print(f"  {lbl:<28}{len(G):>8}  WIPED OUT"); continue
            print(f"  {lbl:<28}{len(G):>8}{G.ret.mean()*100:>+10.3f}%"
                  f"{r['cagr']*100:>8.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}"
                  f"{r['worst_day']*100:>+10.1f}%{r['uw']*100:>12.0f}%"
                  f"{r['final']:>11,.0f}")
        print()

    print("="*94)
    print("AT MATCHED RISK — size scaled inversely to volatility at entry, 3x")
    print("="*94)
    print("  Loud trades are roughly twice the size of quiet ones in risk terms.")
    print("  Running both at the same notional flatters loud. Here quiet positions")
    print("  are sized 1.5x and loud ones 0.5x, which is what anyone would do.\n")
    print(f"  {'book':<28}{'trades':>8}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>8}"
          f"{'worst day':>11}{'final':>12}")
    for lbl, G, rp in (("no filter, flat size", S, False),
                       ("no filter, risk-scaled", S, True),
                       ("quiet only, flat size", S[S.vol < 1/3], False)):
        if len(G) < 200: continue
        r = simulate(G, 40, 3, risk_parity=rp)
        if r is None: print(f"  {lbl:<28}{len(G):>8}  WIPED OUT"); continue
        print(f"  {lbl:<28}{len(G):>8}{r['cagr']*100:>8.1f}%{r['dd']*100:>8.1f}%"
              f"{r['sharpe']:>8.2f}{r['worst_day']*100:>+10.1f}%{r['final']:>11,.0f}")

    print("\n" + "="*94)
    print("DO THE LOSSES ARRIVE TOGETHER?")
    print("="*94)
    S["day"] = pd.to_datetime(S.exit).dt.date
    for lbl, G in (("quiet", S[S.vol < 1/3]), ("loud", S[S.vol >= 2/3])):
        if len(G) < 200: continue
        dd = G.groupby("day").ret.agg(["sum", "count", "min"])
        bad = dd[dd["sum"] < 0]
        print(f"  {lbl:<8}worst day {dd['sum'].min()*100:>+7.1f}% across "
              f"{int(dd.loc[dd['sum'].idxmin(), 'count']):>3} trades   |   "
              f"losing days {len(bad)/len(dd)*100:>3.0f}%   |   "
              f"1st-pct day {dd['sum'].quantile(0.01)*100:>+6.1f}%")
    print("\n  'worst day' sums every trade that closed that day. If the loud")
    print("  number is far worse than its per-trade tail suggests, the losses")
    print("  are clustering - which is the thing per-trade averaging hides.")
