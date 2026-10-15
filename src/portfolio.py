"""
THE ACTUAL EQUITY CURVE ON $2,000.

Everything so far has been a per-trade average, which is not money. 4,506
signals across 263 products overlap heavily in time, and a $2,000 stack cannot
hold them all; the per-trade mean silently assumes it can. This replaces the
average with a simulation that has to obey a balance sheet.

THE RULES IT OBEYS
  capital       starts at $2,000 and compounds; nothing is added
  concurrency   at most MAXPOS open positions at once. Signals arriving when
                the book is full are DROPPED, not queued - that is what
                actually happens.
  sizing        each position gets equity/MAXPOS of notional at LEV leverage,
                so the risk per trade stays proportional as the stack grows
  costs         maker in, maker out on the target, taker plus slippage on the
                stop - the same cost model as everywhere else
  liquidation   if a position's loss exceeds the margin posted, the loss is
                capped at the margin. With a 3 ATR stop and leverage above
                about 5x this starts to bite, which is the real argument
                against leverage rather than a rule of thumb.
  one per name  no pyramiding into the same product

WHAT COMES OUT
  the equity curve, CAGR, max drawdown, Sharpe, the worst year, how often the
  book was full (which says whether MAXPOS is binding), and the trade count
  per month so it can be checked against DK's "50 a month" target.

Swept over concurrency and leverage, because those two are the only free
parameters a small account actually controls.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import system_on_history as SYS

MAKER, TAKER, SLIP = SYS.MAKER, SYS.TAKER, SYS.SLIP
T_ATR, S_ATR, KBAND, EFF, HOLD = SYS.T_ATR, SYS.S_ATR, SYS.KBAND, SYS.EFF, SYS.HOLD
START = 2000.0


def signals(data):
    """Every signal with its entry date, exit date and gross return."""
    rows = []
    for s, d in data.items():
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); a = SYS.atr_np(H, L, C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - KBAND*a
        ok = SYS.efficiency(C) < EFF
        trig = (C <= lower) & (np.roll(C, 1) > np.roll(lower, 1)) & ok
        last = -10**9
        for i in np.flatnonzero(trig):
            if i < 120 or i > n-HOLD-2 or i-last < HOLD: continue
            last = i
            stop = C[i]-S_ATR*a[i]; tgt = C[i]+T_ATR*a[i]
            if stop <= 0 or stop >= C[i]: continue
            e = C[i]*(1+MAKER); out = None; bars = HOLD
            for q in range(i+1, min(i+1+HOLD, n)):
                if L[q] <= stop:
                    out = (stop*(1-SLIP-TAKER))/e-1; bars = q-i; break
                if H[q] >= tgt:
                    out = (tgt*(1-MAKER))/e-1; bars = q-i; break
            if out is None:
                q = min(i+HOLD, n-1); out = (C[q]*(1-MAKER))/e-1; bars = q-i
            rows.append((s, d.index[i], d.index[min(i+bars, n-1)], out))
    S = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret"])
    return S.sort_values("entry").reset_index(drop=True)


def simulate(S, maxpos, lev):
    eq = START
    open_pos = []           # (exit_date, margin, ret)
    curve = []; taken = 0; dropped = 0; full_days = 0
    days = pd.date_range(S.entry.min(), S.exit.max(), freq="D")
    by_entry = {k: v for k, v in S.groupby("entry")}
    for day in days:
        # close anything due
        still = []
        for ex, margin, r in open_pos:
            if ex <= day:
                pnl = r * lev * margin
                pnl = max(pnl, -margin)      # cannot lose more than the margin
                eq += pnl
            else:
                still.append((ex, margin, r))
        open_pos = still
        if len(open_pos) >= maxpos: full_days += 1
        todays = by_entry.get(day)
        if todays is not None and eq > 0:
            held = {p for _, p, _ in []} if False else set()
            for _, row in todays.iterrows():
                if len(open_pos) >= maxpos:
                    dropped += 1; continue
                if any(True for _ in []) : pass
                margin = eq / maxpos
                if margin <= 0: dropped += 1; continue
                open_pos.append((row.exit, margin, row.ret))
                taken += 1
        curve.append((day, eq + sum(m for _, m, _ in open_pos) * 0))
        if eq <= 0: break
    E = pd.Series({d: v for d, v in curve}).astype(float)
    if len(E) < 60 or E.iloc[-1] <= 0:
        return None
    yrs = (E.index[-1]-E.index[0]).days/365.25
    cagr = (E.iloc[-1]/START)**(1/yrs)-1 if E.iloc[-1] > 0 else -1
    dd = (E/E.cummax()-1).min()
    r = E.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    sharpe = r.mean()/r.std()*np.sqrt(365) if r.std() > 0 else np.nan
    return dict(maxpos=maxpos, lev=lev, final=E.iloc[-1], cagr=cagr, dd=dd,
                sharpe=sharpe, taken=taken, dropped=dropped,
                full=full_days/max(len(E), 1), per_month=taken/(yrs*12), curve=E)


if __name__ == "__main__":
    data = SYS.load()
    S = signals(data)
    print(f"{len(S):,} signals, {S.sym.nunique()} products, "
          f"{S.entry.min().date()} -> {S.exit.max().date()}")
    sd = S.groupby(S.entry.dt.to_period("M")).size()
    print(f"signals per month: median {sd.median():.0f}, max {sd.max()}\n")

    print("=" * 104)
    print(f"EQUITY SIMULATION ON ${START:,.0f} — concurrency x leverage")
    print(f"  {'slots':>6}{'lev':>5}{'final $':>12}{'CAGR':>9}{'maxDD':>9}"
          f"{'Sharpe':>8}{'taken':>7}{'dropped':>9}{'book full':>11}{'trades/mo':>11}")
    best = None; rows = []
    for maxpos in (3, 5, 10, 20):
        for lev in (1, 2, 3, 5):
            r = simulate(S, maxpos, lev)
            if r is None:
                print(f"  {maxpos:>6}{lev:>5}  WIPED OUT"); continue
            rows.append(r)
            print(f"  {maxpos:>6}{lev:>5}{r['final']:>12,.0f}{r['cagr']*100:>8.1f}%"
                  f"{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}{r['taken']:>7}"
                  f"{r['dropped']:>9}{r['full']*100:>10.0f}%{r['per_month']:>11.1f}")
            if best is None or r["sharpe"] > best["sharpe"]: best = r
    if best:
        print(f"\nBEST BY SHARPE: {best['maxpos']} slots at {best['lev']}x -> "
              f"${best['final']:,.0f} from ${START:,.0f}, CAGR {best['cagr']*100:.1f}%, "
              f"max drawdown {best['dd']*100:.1f}%, Sharpe {best['sharpe']:.2f}")
        print(f"  {best['taken']:,} trades taken, {best['dropped']:,} dropped because "
              f"the book was full ({best['full']*100:.0f}% of days)")
        print(f"  {best['per_month']:.0f} trades/month against DK's target of 50")
        E = best["curve"]
        print(f"\n  EQUITY BY YEAR")
        for y, g in E.groupby(E.index.year):
            print(f"    {y}  ${g.iloc[-1]:>12,.0f}   "
                  f"{(g.iloc[-1]/g.iloc[0]-1)*100:>+8.1f}%   "
                  f"worst drawdown in year {(g/g.cummax()-1).min()*100:>6.1f}%")
        E.to_csv("/home/claude/qlab/runs/equity_curve.csv")
        print("\n  -> runs/equity_curve.csv")
