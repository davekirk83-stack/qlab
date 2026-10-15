"""
RUN 10 — RE-TEST EVERYTHING WITH REAL TRADE MANAGEMENT.

Why this run exists. Runs 1-5 tested ~6,000 candidates as binary positions:
in at the close, out when the signal flips or N bars elapse. No stop, no target.
On that basis almost everything was declared dead.

Run 6 then tested the SAME entries with real exits and the verdict reversed:
    Donchian_20 + ATR2 target  -> +0.649% per trade
    Donchian_20 + fib 1.618    -> +2.154% per trade, t=4.90
A signal that was "dead" became strongly positive by changing only the exit.

That means the earlier nulls were a statement about my testing, not about the
signals. This run re-tests every family the way a trader would actually use it:

    entry   signal fires
    stop    1.5 x ATR below entry, fixed
    target  1.618 fib extension of the recent swing (the winner from run 6)
    size    one unit, no overlap
    cost    per-symbol, estimated from the data

Event-driven, bar by bar, stop checked before target (conservative).
Every signal family from runs 1-5 plus the patterns, now with management.
"""
import os, json, time, numpy as np, pandas as pd
import core as C
import patterns as P
import levels as LV

ALT = "/home/claude/qlab/data_alt"
MAJ = "/home/claude/qlab/data"


def load_universe(max_alt=120):
    panel = {}
    for f in sorted(os.listdir(MAJ)):
        if f.endswith(".csv") and not f.startswith("_"):
            try:
                d = pd.read_csv(f"{MAJ}/{f}"); d["date"]=pd.to_datetime(d["date"],errors="coerce"); d=d.dropna(subset=["date"]).set_index("date").sort_index()
                if len(d) > 800:
                    panel[f[:-4]] = d
            except Exception:
                pass
    n = 0
    for f in sorted(os.listdir(ALT)):
        if n >= max_alt:
            break
        if f.endswith(".csv"):
            try:
                d = pd.read_csv(f"{ALT}/{f}"); d["date"]=pd.to_datetime(d["date"],errors="coerce"); d=d.dropna(subset=["date"]).set_index("date").sort_index()
                if len(d) > 800 and not d.close.le(0).any():
                    panel[f[:-4]] = d
                    n += 1
            except Exception:
                pass
    return panel


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def est_cost(df):
    rng = ((df.high - df.low) / df.close).replace([np.inf, -np.inf], np.nan).dropna()
    if len(rng) < 50:
        return 0.004
    return float(np.clip(rng[rng <= rng.quantile(0.25)].mean() * 0.5, 0.0005, 0.030))


def fib_target(df, k=1.618, lb=50):
    lo = df.low.rolling(lb).min()
    hi = df.high.rolling(lb).max()
    return lo + (hi - lo) * k


def managed(df, entries, cost, stop_mult=1.5, max_bars=40, tgt_k=1.618):
    """Event-driven. Returns per-trade net returns."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    T = fib_target(df, tgt_k).values
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
        stop = e - stop_mult * a
        tgt = T[i]
        if not (tgt == tgt) or tgt <= e:
            tgt = e + 2 * a
        res = None
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= stop:
                res = (stop / e - 1, j); break
            if H[j] >= tgt:
                res = (tgt / e - 1, j); break
        if res is None:
            j = min(i + max_bars, len(df) - 1)
            res = (Cl[j] / e - 1, j)
        out.append(res[0] - cost)
        last = res[1]
    return np.array(out)


def summarise(r):
    if len(r) < 100:
        return None
    exp = float(r.mean())
    se = r.std() / np.sqrt(len(r))
    return dict(n=len(r), expectancy=exp, t=float(exp / se) if se > 0 else 0.0,
                win=float((r > 0).mean()),
                avg_win=float(r[r > 0].mean()) if (r > 0).any() else 0.0,
                avg_loss=float(r[r < 0].mean()) if (r < 0).any() else 0.0,
                total=float(r.sum()))


def bootstrap_t(r, n=2000, seed=5):
    rng = np.random.default_rng(seed)
    m = np.array([rng.choice(r, len(r), replace=True).mean() for _ in range(n)])
    return float((m > 0).mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


SIGNALS = {
    # trend / momentum
    "tsmom60":    lambda d: (d.close / d.close.shift(60) - 1 > 0).astype(float)
                            * (d.close / d.close.shift(60) - 1).diff().gt(0).astype(float),
    "ema20_100":  lambda d: (d.close.ewm(span=20).mean() > d.close.ewm(span=100).mean()).astype(float)
                            & (d.close.ewm(span=20).mean().shift(1) <= d.close.ewm(span=100).mean().shift(1)),
    # breakout
    "donch20":    lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
    "donch55":    lambda d: (d.close > d.high.rolling(55).max().shift(1)).astype(float),
    "volbrk":     lambda d: (d.close > d.close.shift(1) + 1.0 *
                             (d.high - d.low).rolling(20).mean()).astype(float),
    # mean reversion
    "rsi2":       lambda d: C.s_rsi(d, 2, 10) * C.f_trend200(d),
    "rsi14":      lambda d: C.s_rsi(d, 14, 30) * C.f_trend200(d),
    "zscore2":    lambda d: C.s_zscore(d, 20, 2.0) * C.f_trend200(d),
    # patterns
    "flag":       lambda d: P.p_flag(d, 2.0, 10, 5, 0.5),
    "pennant":    lambda d: P.p_pennant(d, 2.0, 10, 8),
    "dblbottom":  lambda d: P.p_double_bottom(d, 40, 0.03),
    "invhs":      lambda d: P.p_head_shoulders_inv(d, 60),
    "tlbreak":    lambda d: P.p_trendline_break(d, 50),
    "sretest":    lambda d: P.p_support_retest(d, 50, 0.02),
    "engulf":     lambda d: P.p_engulfing(d) * C.f_trend200(d),
    "pinbar":     lambda d: P.p_pinbar(d, 2.0) * C.f_trend200(d),
    "insidebrk":  lambda d: P.p_inside_break(d),
    # levels
    "brk_mo_hi":  lambda d: LV.l_break_prior_month_high(d),
    "brk_qt_hi":  lambda d: LV.l_break_prior_quarter_high(d),
    "swingbrk":   lambda d: LV.l_swing_break(d, 20),
    "ath":        lambda d: LV.l_at_all_time_high(d, 0.02),
    "retest_mo":  lambda d: LV.l_retest_prior_month_high(d, 0.015),
}


def main():
    panel = load_universe()
    costs = {s: est_cost(d) for s, d in panel.items()}
    print(f"RUN 10 — {len(panel)} instruments, event-driven, "
          f"1.5xATR stop + 1.618 fib target\n", flush=True)
    print(f"  {'signal':12s} {'trades':>7} {'expect':>9} {'t':>7} {'win%':>6} "
          f"{'avgW':>7} {'avgL':>7} {'boot>0':>8}", flush=True)

    rows, n_trials = [], 0
    for name, fn in SIGNALS.items():
        allr = []
        for s, df in panel.items():
            try:
                e = fn(df)
                e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
            except Exception:
                continue
            if e.sum() == 0:
                continue
            allr.append(managed(df, e, costs[s]))
        n_trials += 1
        if not allr:
            continue
        r = np.concatenate(allr)
        st = summarise(r)
        if not st:
            print(f"  {name:12s}   too few trades"); continue
        bp, lo, hi = bootstrap_t(r)
        st.update(name=name, boot_pos=bp, ci_lo=lo, ci_hi=hi)
        rows.append(st)
        print(f"  {name:12s} {st['n']:7d} {st['expectancy']*100:+8.3f}% {st['t']:+7.2f} "
              f"{st['win']*100:5.1f}% {st['avg_win']*100:+6.2f}% {st['avg_loss']*100:+6.2f}% "
              f"{bp*100:7.1f}%", flush=True)

    cum = C.ledger_bump(n_trials, "run10: all families re-tested with real trade management")
    print(f"\nLIFETIME TRIALS: {cum}")

    df = pd.DataFrame(rows).sort_values("t", ascending=False)
    sig = df[(df.t > 3) & (df.boot_pos > 0.99)]
    print(f"\n{'='*78}")
    print(f"SURVIVING with t>3 AND bootstrap >99% positive: {len(sig)} of {len(df)}")
    print(f"{'='*78}")
    for _, r in sig.iterrows():
        print(f"  {r['name']:12s} expectancy {r['expectancy']*100:+.3f}% per trade, "
              f"t={r['t']:+.2f}, n={int(r['n'])}, 95% CI "
              f"[{r['ci_lo']*100:+.3f}%, {r['ci_hi']*100:+.3f}%]")
    df.to_csv("/home/claude/qlab/runs/run10.csv", index=False)
    print("\nwrote run10.csv")


if __name__ == "__main__":
    main()
