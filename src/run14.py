"""
RUN 14 — PORTFOLIO SIMULATION. The test that actually matters.

Expectancy per trade is a misleading headline: trades overlap, position sizes
differ, and a +761% outlier in one microcap does not mean the portfolio made
761%. What DK needs to know is what the ACCOUNT does.

So: run the system as an account.
  - fixed fractional risk per trade (risk R% of equity on the stop distance)
  - cap on simultaneous open positions
  - cap on total portfolio heat
  - trades compete for slots chronologically; if full, the signal is SKIPPED
    (this is what actually happens in practice and backtests usually ignore it)
  - equity compounds

Reported: CAGR, max drawdown, time under water, Sharpe, worst year, and the
same for a BTC buy-and-hold benchmark over the identical period.

If the system cannot beat simply holding BTC, with a comparable drawdown,
it is not worth running.
"""
import numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}

RISK_PCT = 0.01        # risk 1% of equity per trade
MAX_OPEN = 8           # simultaneous positions
MAX_HEAT = 0.06        # total open risk


def build_trades(stop_atr=1.5, tp1_r=1.0, tp2_k=1.618, trail_atr=2.5,
                 max_bars=60, be_offset_r=0.10):
    """Generate every candidate trade with entry/exit dates and R-multiple."""
    out = []
    for s, df in PANEL.items():
        try:
            e = LV.l_break_prior_month_high(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        A = atr(df).values
        H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
        SL = df.low.rolling(10).min().values
        lo50 = df.low.rolling(50).min().values
        hi50 = df.high.rolling(50).max().values
        cost = COSTS[s]
        idx = np.flatnonzero(e.values > 0)
        last = -1
        for i in idx:
            if i <= last or i + 1 >= len(df):
                continue
            a = A[i]
            if not (a == a) or a <= 0:
                continue
            px = O[i + 1]
            if not (px == px) or px <= 0:
                continue
            atr_stop = px - stop_atr * a
            stop = max(atr_stop, SL[i] * 0.995) if SL[i] == SL[i] else atr_stop
            if stop >= px:
                stop = atr_stop
            risk = px - stop
            if risk <= 0:
                continue
            tp1 = px + tp1_r * risk
            tp2 = lo50[i] + (hi50[i] - lo50[i]) * tp2_k if lo50[i] == lo50[i] else px + 3 * risk
            if not (tp2 == tp2) or tp2 <= tp1:
                tp2 = px + 3 * risk
            filled, pnl_r, peak, ex = 0.0, 0.0, px, None
            cur_stop = stop
            for j in range(i + 1, min(i + 1 + max_bars, len(df))):
                if L[j] <= cur_stop:
                    pnl_r += (1 - filled) * (cur_stop - px) / risk
                    ex = j; break
                if filled < 0.34 and H[j] >= tp1:
                    pnl_r += (1 / 3) * (tp1 - px) / risk; filled = 1 / 3
                    cur_stop = max(cur_stop, px + be_offset_r * risk + cost * px)
                if filled < 0.67 and H[j] >= tp2:
                    pnl_r += (1 / 3) * (tp2 - px) / risk; filled = 2 / 3
                if filled >= 0.66:
                    tr = peak - trail_atr * a
                    if L[j] <= tr and tr > cur_stop:
                        pnl_r += (1 - filled) * (tr - px) / risk
                        ex = j; break
                peak = max(peak, H[j])
            if ex is None:
                j = min(i + max_bars, len(df) - 1)
                pnl_r += (1 - filled) * (Cl[j] - px) / risk
                ex = j
            pnl_r -= cost * px / risk        # cost in R terms
            out.append(dict(sym=s, entry=df.index[i + 1], exit=df.index[ex],
                            r=float(pnl_r), risk_frac=float(risk / px)))
            last = ex
    return pd.DataFrame(out).sort_values("entry").reset_index(drop=True)


def simulate(trades, risk_pct=RISK_PCT, max_open=MAX_OPEN, max_heat=MAX_HEAT):
    """Chronological account simulation with slot and heat limits."""
    equity = 1.0
    open_pos = []          # (exit_date, risk_amount, r_multiple)
    curve = []
    taken = skipped = 0
    dates = sorted(set(trades.entry) | set(trades.exit))
    by_entry = {d: g for d, g in trades.groupby("entry")}
    for d in dates:
        # close finished positions
        still = []
        for ex, amt, r in open_pos:
            if ex <= d:
                equity += amt * r
            else:
                still.append((ex, amt, r))
        open_pos = still
        # consider new entries
        for _, t in by_entry.get(d, pd.DataFrame()).iterrows():
            heat = sum(a for _, a, _ in open_pos) / max(equity, 1e-9)
            if len(open_pos) >= max_open or heat >= max_heat:
                skipped += 1
                continue
            amt = equity * risk_pct
            open_pos.append((t.exit, amt, t.r))
            taken += 1
        curve.append((d, equity))
    for ex, amt, r in open_pos:
        equity += amt * r
    c = pd.Series(dict(curve)).sort_index()
    return c, taken, skipped


def metrics(c, label):
    if len(c) < 50:
        return None
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    cagr = c.iloc[-1] ** (1 / max(yrs, 0.1)) - 1
    dd = (c / c.cummax() - 1)
    r = c.pct_change().dropna()
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    uw = float((dd < -0.05).mean())
    ann = c.resample("YE").last().pct_change().dropna()
    print(f"  {label:26s} final {c.iloc[-1]:7.2f}x  CAGR {cagr*100:+7.2f}%  "
          f"maxDD {dd.min()*100:7.1f}%  Sharpe {sharpe:+5.2f}  "
          f"under water {uw*100:4.0f}%  worst yr {ann.min()*100 if len(ann) else 0:+7.1f}%")
    return dict(cagr=cagr, dd=float(dd.min()), sharpe=float(sharpe))


def main():
    print("RUN 14 — PORTFOLIO SIMULATION (1% risk/trade, max 8 open, 6% heat cap)\n")
    print("=" * 96)
    for label, kw in (("baseline plan", {}),
                      ("'optimised' plan", dict(stop_atr=3.0, trail_atr=6.0, tp1_r=2.0,
                                                tp2_k=2.618, max_bars=120, be_offset_r=0.0))):
        t = build_trades(**kw)
        if not len(t):
            continue
        c, taken, skipped = simulate(t)
        print(f"\n  {label}: {len(t)} signals, {taken} taken, {skipped} skipped "
              f"(slots/heat full)")
        metrics(c, label)

        # BTC buy and hold over the identical window
        btc = PANEL.get("BTCUSD")
        if btc is not None:
            w = btc.close[(btc.index >= c.index[0]) & (btc.index <= c.index[-1])]
            if len(w) > 50:
                metrics(w / w.iloc[0], "BTC buy & hold")
        spy = PANEL.get("SPY")
        if spy is not None:
            w = spy.close[(spy.index >= c.index[0]) & (spy.index <= c.index[-1])]
            if len(w) > 50:
                metrics(w / w.iloc[0], "SPY buy & hold")

    C.ledger_bump(2, "run14: portfolio simulation vs buy and hold")


if __name__ == "__main__":
    main()
