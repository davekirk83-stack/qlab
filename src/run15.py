"""
RUN 15 — OPTIMISE FOR RETURN PER UNIT TIME, NOT PER TRADE.

DK's correction, and it is right: maximising expectancy PER TRADE inevitably
pushes toward longer holds, which is why run 13's sweep converged on buy-and-hold.
That objective function rewards investing, not trading.

A trading system should maximise return per unit of capital-time. A trade earning
8% in 6 days is worth far more than one earning 15% in 120 days, because the
capital comes back and gets redeployed.

Objective:  R_per_bar = R_multiple / bars_held
and the headline metric is ANNUALISED RETURN ON DEPLOYED CAPITAL:
    (1 + mean_return_per_trade) ^ (252 / mean_bars_held) - 1

Horizons are constrained to actual trading timeframes:
    DAY    hold <= 3 bars
    WEEK   hold <= 10 bars
    MONTH  hold <= 25 bars
rather than the 60-120 bar holds that were quietly turning this into investing.
"""
import numpy as np, pandas as pd, itertools
import core as C
import levels as LV
import patterns as P
from run10 import load_universe, atr, est_cost

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}


def trade(df, entries, cost, stop_atr, tp1_r, tp2_r, trail_atr, max_bars,
          be_offset_r=0.10):
    """Returns (ret, bars_held) per trade. TP2 now in R, not fib, so holding
    period is controlled rather than open-ended."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    SL = df.low.rolling(10).min().values
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
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
        tp1, tp2 = px + tp1_r * risk, px + tp2_r * risk
        filled, pnl, peak, ex = 0.0, 0.0, px, None
        cur = stop
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= cur:
                pnl += (1 - filled) * (cur / px - 1); ex = j; break
            if filled < 0.34 and H[j] >= tp1:
                pnl += (1 / 3) * (tp1 / px - 1); filled = 1 / 3
                cur = max(cur, px + be_offset_r * risk + cost * px)
            if filled < 0.67 and H[j] >= tp2:
                pnl += (1 / 3) * (tp2 / px - 1); filled = 2 / 3
            if filled >= 0.66:
                tr = peak - trail_atr * a
                if L[j] <= tr and tr > cur:
                    pnl += (1 - filled) * (tr / px - 1); ex = j; break
            peak = max(peak, H[j])
        if ex is None:
            j = min(i + max_bars, len(df) - 1)
            pnl += (1 - filled) * (Cl[j] / px - 1); ex = j
        out.append((pnl - cost, ex - i))
        last = ex
    return out


ENTRIES = {
    "month-high break":   lambda d: LV.l_break_prior_month_high(d),
    "swing break":        lambda d: LV.l_swing_break(d, 20),
    "donchian 20":        lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
    "flag":               lambda d: P.p_flag(d, 2.0, 10, 5, 0.5),
    "pullback in trend":  lambda d: C.s_rsi(d, 2, 10) * C.f_trend200(d),
}


def run(entry_fn, **kw):
    rets, bars = [], []
    for s, df in PANEL.items():
        try:
            e = entry_fn(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        for r, b in trade(df, e, COSTS[s], **kw):
            rets.append(r); bars.append(max(b, 1))
    if len(rets) < 100:
        return None
    r = np.array(rets); b = np.array(bars)
    mean_bars = float(b.mean())
    exp = float(r.mean())
    # annualised return on deployed capital
    ann = (1 + exp) ** (252 / mean_bars) - 1 if exp > -1 else -1
    return dict(n=len(r), exp=exp, bars=mean_bars, ann=ann,
                per_bar=float((r / b).mean()),
                med=float(np.median(r)), win=float((r > 0).mean()),
                t=float(exp / (r.std() / np.sqrt(len(r)))) if r.std() > 0 else 0)


def main():
    print("RUN 15 — objective is RETURN PER UNIT TIME, not per trade\n")
    HORIZONS = {"DAY (<=3 bars)": 3, "WEEK (<=10)": 10, "MONTH (<=25)": 25,
                "(old default 60)": 60}
    results = []

    print("=" * 100)
    print("A. THE SAME PLAN AT DIFFERENT HORIZONS — note what happens to annualised return")
    print("=" * 100)
    print(f"  {'entry':20s} {'horizon':18s} {'exp/trade':>10} {'avg bars':>9} "
          f"{'ANNUALISED':>12} {'win%':>6} {'n':>6}")
    for ename, efn in ENTRIES.items():
        for hname, mb in HORIZONS.items():
            r = run(efn, stop_atr=1.5, tp1_r=1.0, tp2_r=3.0, trail_atr=2.5, max_bars=mb)
            if r:
                results.append(dict(entry=ename, horizon=hname, **r))
                print(f"  {ename:20s} {hname:18s} {r['exp']*100:+9.3f}% {r['bars']:9.1f} "
                      f"{r['ann']*100:+11.1f}% {r['win']*100:5.1f}% {r['n']:6d}")

    df = pd.DataFrame(results)
    print()
    print("=" * 100)
    print("B. BEST CONFIGURATION BY ANNUALISED RETURN ON DEPLOYED CAPITAL")
    print("=" * 100)
    for _, r in df.sort_values("ann", ascending=False).head(8).iterrows():
        print(f"  {r['entry']:20s} {r['horizon']:18s} annualised {r['ann']*100:+9.1f}%  "
              f"(exp {r['exp']*100:+.3f}% over {r['bars']:.1f} bars, t={r['t']:+.2f})")

    # C. sweep the levers again, but judged on annualised return
    print()
    print("=" * 100)
    print("C. REFINEMENT SWEEP, JUDGED ON ANNUALISED RETURN (week horizon)")
    print("=" * 100)
    best = df.sort_values("ann", ascending=False).iloc[0]["entry"]
    efn = ENTRIES[best]
    print(f"  using the best entry: {best}\n")
    base = dict(stop_atr=1.5, tp1_r=1.0, tp2_r=3.0, trail_atr=2.5, max_bars=10)
    rows = []
    def rep(label, **over):
        kw = dict(base); kw.update(over)
        r = run(efn, **kw)
        if r:
            rows.append(dict(label=label, **r))
            print(f"  {label:24s} exp {r['exp']*100:+7.3f}%  bars {r['bars']:5.1f}  "
                  f"ANN {r['ann']*100:+9.1f}%  win {r['win']*100:5.1f}%  n={r['n']}")
    rep("baseline (week)")
    for x in (0.75, 1.0, 1.5, 2.5):
        rep(f"stop {x} ATR", stop_atr=x)
    for x in (0.5, 1.0, 2.0):
        rep(f"TP1 {x}R", tp1_r=x)
    for x in (1.5, 2.0, 3.0, 5.0):
        rep(f"TP2 {x}R", tp2_r=x)
    for x in (1.0, 2.5, 4.0):
        rep(f"trail {x} ATR", trail_atr=x)
    for x in (3, 5, 10, 15, 25):
        rep(f"max {x} bars", max_bars=x)

    rr = pd.DataFrame(rows)
    b0 = rr[rr.label == "baseline (week)"].iloc[0]
    better = rr[rr.ann > b0.ann].sort_values("ann", ascending=False)
    print()
    print("  improvements over baseline, by annualised return:")
    if len(better):
        for _, r in better.iterrows():
            print(f"    {r['label']:24s} {(r['ann']-b0['ann'])*100:+9.1f}pp annualised")
    else:
        print("    none")

    cum = C.ledger_bump(len(results) + len(rows), "run15: time-adjusted objective")
    print(f"\nLIFETIME TRIALS: {cum}")
    df.to_csv("/home/claude/qlab/runs/run15.csv", index=False)


if __name__ == "__main__":
    main()
