"""
RUN 12 — COMPLETE TRADE PLANS, VALIDATED PERIOD BY PERIOD.

DK's point, which is correct: a trade is planned, executed, scaled out of at
planned levels, and exited. Judging an entry signal in isolation against random
timing answers a narrower question than "does this plan work".

So this run tests PLANS, not signals. Each plan is a full specification:

    ENTRY    a structural trigger
    STOP     volatility-scaled, placed below the structure that triggered it
    TP1      first scale-out, partial size
    TP2      second scale-out at a further structural/fib level
    RUNNER   remainder trailed
    TIME     hard time stop

And it is validated the way a plan would actually be lived with: YEAR BY YEAR,
out of sample, rolling forward. A plan that only works in aggregate but loses in
most individual years is not tradeable, whatever the pooled t-statistic says.

Random entry is retained ONLY as attribution — to show how much of each plan's
return comes from the entry versus the management — never as a pass/fail gate.
"""
import os, numpy as np, pandas as pd
import core as C
import levels as LV
import patterns as P
from run10 import load_universe, atr, est_cost

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}


def swing_low(df, lb=10):
    return df.low.rolling(lb).min()


def execute_plan(df, entries, cost, stop_atr=1.5, tp1_r=1.0, tp2_k=1.618,
                 trail_atr=2.5, max_bars=60, use_struct_stop=True, be_offset_r=0.10):
    """
    Full plan execution, scaling out.
      - stop below the recent swing low (structural) or ATR, whichever is tighter
      - TP1: take 1/3 at tp1_r multiples of initial risk
      - TP2: take 1/3 at the fib extension of the entry swing
      - runner: trail the final 1/3 by trail_atr
      - stop moves to breakeven after TP1
    Returns list of (net_return, entry_date).
    """
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    SL = swing_low(df, 10).values
    lo50 = df.low.rolling(50).min().values
    hi50 = df.high.rolling(50).max().values
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
    for i in idx:
        if i <= last or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        e = O[i + 1]
        if not (e == e) or e <= 0:
            continue
        atr_stop = e - stop_atr * a
        struct = SL[i] if (SL[i] == SL[i]) else atr_stop
        stop = max(atr_stop, struct * 0.995) if use_struct_stop else atr_stop
        if stop >= e:
            stop = atr_stop
        risk = e - stop
        if risk <= 0:
            continue
        tp1 = e + tp1_r * risk
        tp2 = (lo50[i] + (hi50[i] - lo50[i]) * tp2_k) if (lo50[i] == lo50[i]) else e + 3 * risk
        if not (tp2 == tp2) or tp2 <= tp1:
            tp2 = e + 3 * risk

        filled, pnl, peak = 0.0, 0.0, e
        exit_j = None
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= stop:
                pnl += (1 - filled) * (stop / e - 1)
                exit_j = j; break
            if filled < 0.34 and H[j] >= tp1:
                pnl += (1 / 3) * (tp1 / e - 1); filled = 1 / 3
                # DK: after TP1 the stop goes slightly ABOVE breakeven, so the
                # trade is locked green net of fees rather than merely scratch.
                stop = max(stop, e + be_offset_r * risk + cost * e)
            if filled < 0.67 and H[j] >= tp2:
                pnl += (1 / 3) * (tp2 / e - 1); filled = 2 / 3
            if filled >= 0.66:
                trail = peak - trail_atr * a            # peak is PRIOR bars only
                if L[j] <= trail and trail > stop:
                    pnl += (1 - filled) * (trail / e - 1)
                    exit_j = j; break
            peak = max(peak, H[j])                      # update AFTER the test
        if exit_j is None:
            j = min(i + max_bars, len(df) - 1)
            pnl += (1 - filled) * (Cl[j] / e - 1)
            exit_j = j
        out.append((pnl - cost, df.index[i]))
        last = exit_j
    return out


PLANS = {
    "monthly-high break":   lambda d: LV.l_break_prior_month_high(d),
    "quarterly-high break": lambda d: LV.l_break_prior_quarter_high(d),
    "swing break":          lambda d: LV.l_swing_break(d, 20),
    "flag continuation":    lambda d: P.p_flag(d, 2.0, 10, 5, 0.5),
    "donchian 20":          lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
    "trend pullback":       lambda d: C.s_rsi(d, 2, 10) * C.f_trend200(d),
}


def collect(fn, **kw):
    rows = []
    for s, df in PANEL.items():
        try:
            e = fn(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        for r, d in execute_plan(df, e, COSTS[s], **kw):
            rows.append((r, d, s))
    d = pd.DataFrame(rows, columns=["ret", "date", "sym"])
    d["date"] = pd.to_datetime(d["date"])
    return d


def yearly(d):
    g = d.groupby(d.date.dt.year).ret
    return pd.DataFrame({"n": g.count(), "expectancy": g.mean(), "total": g.sum()})


def main():
    print(f"RUN 12 — COMPLETE TRADE PLANS, {len(PANEL)} instruments")
    print("plan: structural stop · TP1 at 1R (1/3) · TP2 at 1.618 fib (1/3) · "
          "2.5 ATR trail on the runner · breakeven stop after TP1\n")

    summary = []
    for name, fn in PLANS.items():
        d = collect(fn)
        if len(d) < 200:
            print(f"{name}: too few trades\n"); continue
        exp = d.ret.mean(); se = d.ret.std() / np.sqrt(len(d))
        y = yearly(d)
        y = y[y.n >= 25]
        pos_years = int((y.expectancy > 0).sum())
        print(f"{'='*74}")
        print(f"  {name}")
        print(f"{'='*74}")
        print(f"  pooled: n={len(d)}  expectancy {exp*100:+.3f}%  t={exp/se:+.2f}  "
              f"win {float((d.ret>0).mean())*100:.1f}%")
        print(f"  YEAR BY YEAR (>=25 trades):")
        for yr, row in y.iterrows():
            flag = "+" if row.expectancy > 0 else "-"
            print(f"     {yr}  n={int(row.n):5d}  {row.expectancy*100:+8.3f}%  {flag}")
        print(f"  --> positive in {pos_years}/{len(y)} years")
        summary.append(dict(name=name, n=len(d), exp=exp, t=exp / se,
                            pos_years=pos_years, n_years=len(y),
                            worst=float(y.expectancy.min()) if len(y) else 0.0))
        print()

    # attribution: how much comes from management vs entry
    print(f"{'='*74}")
    print("  ATTRIBUTION — the same plan on random entries (not a gate, a diagnostic)")
    print(f"{'='*74}")
    rng = np.random.default_rng(23)
    rows = []
    for s, df in PANEL.items():
        freq = 0.02
        fake = pd.Series((rng.random(len(df)) < freq).astype(float), index=df.index)
        for r, dt in execute_plan(df, fake, COSTS[s]):
            rows.append((r, dt, s))
    rd = pd.DataFrame(rows, columns=["ret", "date", "sym"])
    if len(rd):
        ry = yearly(rd)
        ry = ry[ry.n >= 25]
        print(f"  random entry, same management: n={len(rd)}  "
              f"expectancy {rd.ret.mean()*100:+.3f}%  "
              f"positive in {int((ry.expectancy>0).sum())}/{len(ry)} years")
        print(f"  --> any plan must beat {rd.ret.mean()*100:+.3f}% to be adding "
              f"anything through its ENTRY")

    print(f"\n{'='*74}")
    print("  VERDICT — a plan is tradeable only if it is positive in MOST years")
    print(f"{'='*74}")
    s = pd.DataFrame(summary).sort_values("pos_years", ascending=False)
    for _, r in s.iterrows():
        frac = r.pos_years / max(r.n_years, 1)
        v = "TRADEABLE" if frac >= 0.6 and r.exp > rd.ret.mean() else "no"
        print(f"  {r['name']:22s} {r['exp']*100:+7.3f}%  t={r['t']:+5.2f}  "
              f"years {int(r.pos_years)}/{int(r.n_years)}  worst {r.worst*100:+7.2f}%  {v}")

    cum = C.ledger_bump(len(PLANS) + 1, "run12: complete trade plans, year-by-year")
    print(f"\nLIFETIME TRIALS: {cum}")
    s.to_csv("/home/claude/qlab/runs/run12.csv", index=False)


if __name__ == "__main__":
    main()
