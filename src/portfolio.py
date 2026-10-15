"""
PORTFOLIO SIMULATOR — corrected. Marks open positions to market every day.

The bug in run14.simulate(), which has been inflating every drawdown and Sharpe
figure reported in this project:

    equity only changed when a trade CLOSED.

So the equity curve was a staircase of realised P&L. A position could be 40%
underwater for three weeks and the curve would not move. Drawdown was therefore
measuring the sequence of realised losses, not what the account was actually
worth, and Sharpe was computed on an irregular series sampled at trade dates
while being annualised by sqrt(252) as if it were daily.

That produced a -10.7% maximum drawdown for a long-only equity breakout book
held through March 2020, and a Sharpe of 3.30. Both impossible.

This version:
  - walks a real daily calendar
  - marks every open position to market each day on that symbol's close
  - compounds on daily total equity (realised + unrealised)
  - so drawdown is peak-to-trough on what the account was actually worth
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd


def simulate(trades, prices, risk_pct=0.005, max_open=8, max_heat=0.06,
             start=1.0):
    """
    trades: DataFrame with sym, entry, exit, r (R-multiple), side, entry_px, stop_px
    prices: dict sym -> DataFrame indexed by date with a close column
    Returns a DAILY equity series.
    """
    t = trades.sort_values("entry").reset_index(drop=True)
    cal = sorted(set().union(*[set(p.index) for p in prices.values()]))
    cal = pd.DatetimeIndex(cal)
    by_entry = {d: g for d, g in t.groupby("entry")}

    equity = start
    open_pos = []          # dicts: sym, exit, units, entry_px, stop_px, side, r, risk_amt
    curve = []
    taken = skipped = 0

    for d in cal:
        # 1. close anything whose exit has arrived — realise at the trade's own r
        still = []
        for p in open_pos:
            if p["exit"] <= d:
                equity += p["risk_amt"] * p["r"]
            else:
                still.append(p)
        open_pos = still

        # 2. open new positions
        for _, row in by_entry.get(d, pd.DataFrame()).iterrows():
            heat = sum(x["risk_amt"] for x in open_pos) / max(equity, 1e-9)
            if len(open_pos) >= max_open or heat >= max_heat or equity <= 0:
                skipped += 1
                continue
            risk_amt = equity * risk_pct
            open_pos.append(dict(sym=row["sym"], exit=row["exit"], r=row["r"],
                                 entry_px=row["entry_px"], stop_px=row["stop_px"],
                                 side=row["side"], risk_amt=risk_amt))
            taken += 1

        # 3. MARK TO MARKET — the part that was missing
        unreal = 0.0
        for p in open_pos:
            px = prices.get(p["sym"])
            if px is None or d not in px.index:
                continue
            now = px.close.loc[d]
            risk_per_unit = abs(p["entry_px"] - p["stop_px"])
            if risk_per_unit <= 0:
                continue
            move = (now - p["entry_px"]) if p["side"] == "long" \
                else (p["entry_px"] - now)
            unreal += p["risk_amt"] * (move / risk_per_unit)
        curve.append((d, equity + unreal))

    for p in open_pos:
        equity += p["risk_amt"] * p["r"]
    c = pd.Series(dict(curve)).sort_index()
    return c, taken, skipped


def metrics(c, label, show=True):
    if len(c) < 100:
        return None
    c = c[c > 0]
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    cagr = c.iloc[-1] ** (1 / max(yrs, 0.1)) - 1
    ddc = c / c.cummax() - 1
    dd = float(ddc.min())
    r = c.pct_change().dropna()
    r = r[np.isfinite(r)]
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    # time under water
    uw = float((ddc < -0.05).mean())
    # longest drawdown in days
    peak = c.cummax()
    under = (c < peak * 0.999)
    longest, run = 0, 0
    for v in under:
        run = run + 1 if v else 0
        longest = max(longest, run)
    if show:
        print(f"  {label:26s} {c.iloc[-1]:9.2f}x  CAGR {cagr*100:+7.2f}%  "
              f"maxDD {dd*100:7.1f}%  Sharpe {sharpe:+5.2f}  "
              f"uw {uw*100:3.0f}%  longest DD {longest:4d}d")
    return dict(cagr=cagr, dd=dd, sharpe=sharpe, final=float(c.iloc[-1]))
