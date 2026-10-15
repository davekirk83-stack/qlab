"""
RUN 6 — do liquidation-cluster targets beat a dumb target?

Two separate questions, tested separately:

  Q1. Are the liquidation-derived SIGNALS worth anything?
      (magnet, sweep-reversal) vs the same gates as everything else.

  Q2. Do liquidation-cluster EXIT TARGETS beat a plain ATR target
      on the SAME entries? This is the question that matters. If a clever
      target does not beat a dumb one, the cluster levels are decoration.

Exit schemes compared, all on identical entries:
    atr2         take profit at 2 x ATR            (the control)
    atr3         take profit at 3 x ATR            (control, further)
    fib1272      1.272 extension of the entry swing
    fib1618      1.618 extension
    liq          nearest significant liquidation cluster above
    liq_multi    scale out: 1/3 at 1.5xATR, 1/3 at the cluster, 1/3 trailed
    prior_hi     prior month's high (a structural level)
Stop is identical for every scheme (1.5 x ATR), so only the TARGET varies.
"""
import json, time, numpy as np, pandas as pd
import core as C
import liquidation as LQ

SYMS = C.universe()
PANEL = {s: C.load(s) for s in SYMS}


def atr(df, n=14):
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def trade_sim(df, entries, target_fn, stop_mult=1.5, max_bars=40, cost=0.0015):
    """Event-driven: walk each trade bar by bar. Intrabar order: stop checked
    before target (conservative), both from the NEXT bar after the signal."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    tgt = target_fn(df)
    T = tgt.values if isinstance(tgt, pd.Series) else tgt
    idx = np.flatnonzero(entries.values > 0)
    rets, bars_held, hit = [], [], {"target": 0, "stop": 0, "time": 0}

    last_exit = -1
    for i in idx:
        if i <= last_exit or i + 1 >= len(df):
            continue                      # no overlapping positions
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        entry = O[i + 1]
        stop = entry - stop_mult * a
        target = T[i]
        if not (target == target) or target <= entry:
            target = entry + 2 * a        # fall back to the control
        out = None
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= stop:
                out = (stop / entry - 1, j, "stop"); break
            if H[j] >= target:
                out = (target / entry - 1, j, "target"); break
        if out is None:
            j = min(i + max_bars, len(df) - 1)
            out = (Cl[j] / entry - 1, j, "time")
        r = out[0] - cost
        rets.append(r); bars_held.append(out[1] - i); hit[out[2]] += 1
        last_exit = out[1]
    return np.array(rets), np.array(bars_held), hit


def multi_tp(df, entries, stop_mult=1.5, max_bars=40, cost=0.0015):
    """Scale out in thirds: 1.5xATR, liquidation cluster, trail the rest."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    cl = LQ.liq_targets(df)
    LIQ = cl["above"].values
    idx = np.flatnonzero(entries.values > 0)
    rets, hit = [], {"target": 0, "stop": 0, "time": 0}
    last_exit = -1
    for i in idx:
        if i <= last_exit or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        entry = O[i + 1]
        stop = entry - stop_mult * a
        tp1 = entry + 1.5 * a
        tp2 = LIQ[i] if (LIQ[i] == LIQ[i] and LIQ[i] > tp1) else entry + 3 * a
        filled, pnl, peak = 0.0, 0.0, entry
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= stop:
                pnl += (1 - filled) * (stop / entry - 1); hit["stop"] += 1
                last_exit = j; break
            if filled < 0.34 and H[j] >= tp1:
                pnl += (1 / 3) * (tp1 / entry - 1); filled = 1 / 3
            if filled < 0.67 and H[j] >= tp2:
                pnl += (1 / 3) * (tp2 / entry - 1); filled = 2 / 3
                stop = max(stop, entry)              # move to breakeven
            # LOOKAHEAD FIX: trail is set from the PREVIOUS bar's peak, so the
            # same bar's high cannot both set the trail and trigger the exit.
            if filled >= 0.66:
                trail = peak - 2 * a
                if L[j] <= trail:
                    pnl += (1 - filled) * (trail / entry - 1); hit["target"] += 1
                    last_exit = j; peak = max(peak, H[j]); break
            peak = max(peak, H[j])
        else:
            j = min(i + max_bars, len(df) - 1)
            pnl += (1 - filled) * (Cl[j] / entry - 1); hit["time"] += 1
            last_exit = j
        rets.append(pnl - cost)
    return np.array(rets), None, hit


def summarise(rets):
    if len(rets) < 30:
        return None
    exp = float(rets.mean())
    return dict(n=len(rets), expectancy=exp,
                win_rate=float((rets > 0).mean()),
                avg_win=float(rets[rets > 0].mean()) if (rets > 0).any() else 0.0,
                avg_loss=float(rets[rets < 0].mean()) if (rets < 0).any() else 0.0,
                total=float(rets.sum()),
                t_stat=float(exp / (rets.std() / np.sqrt(len(rets)))) if rets.std() > 0 else 0.0)


def main():
    # Entry rules held CONSTANT across all exit schemes.
    ENTRIES = {
        "donch20_break":  lambda df: C.s_donchian(df, 20),
        "tsmom60":        lambda df: C.s_tsmom(df, 60) * (C.s_tsmom(df, 60).diff() > 0),
        "rsi2_oversold":  lambda df: C.s_rsi(df, 2, 10) * C.f_trend200(df),
        "liq_magnet":     lambda df: LQ.liq_magnet_long(df),
        "liq_sweep":      lambda df: LQ.liq_sweep_reversal(df),
    }

    def mk_atr(k):
        return lambda df: df.close + k * atr(df)

    def mk_fib(k):
        def f(df):
            lo = df.low.rolling(50).min()
            hi = df.high.rolling(50).max()
            return lo + (hi - lo) * k
        return f

    def liq_tgt(df):
        return LQ.liq_targets(df)["above"]

    def prior_hi(df):
        g = df[["high"]].resample("ME").max().shift(1)
        return g.reindex(df.index, method="ffill").high

    SCHEMES = {
        "atr2 (control)": mk_atr(2.0),
        "atr3 (control)": mk_atr(3.0),
        "fib 1.272":      mk_fib(1.272),
        "fib 1.618":      mk_fib(1.618),
        "liq cluster":    liq_tgt,
        "prior mo high":  prior_hi,
    }

    n_trials = 0
    results = {}
    t0 = time.time()
    for ename, efn in ENTRIES.items():
        print(f"\n=== ENTRY: {ename}", flush=True)
        print(f"  {'scheme':16s} {'trades':>7} {'expect':>9} {'win%':>7} "
              f"{'avg win':>8} {'avg loss':>9} {'t':>6}")
        for sname, sfn in SCHEMES.items():
            allr = []
            for s in SYMS:
                try:
                    e = efn(PANEL[s]).fillna(0.0)
                    r, _, _ = trade_sim(PANEL[s], e, sfn, cost=C.cost(s))
                    allr.extend(r)
                except Exception as ex:
                    continue
            n_trials += 1
            st = summarise(np.array(allr))
            results[f"{ename}|{sname}"] = st
            if st:
                print(f"  {sname:16s} {st['n']:7d} {st['expectancy']*100:+8.3f}% "
                      f"{st['win_rate']*100:6.1f}% {st['avg_win']*100:+7.2f}% "
                      f"{st['avg_loss']*100:+8.2f}% {st['t_stat']:+6.2f}", flush=True)
            else:
                print(f"  {sname:16s}   too few trades", flush=True)
        # multi-TP scale-out
        allr = []
        for s in SYMS:
            try:
                e = efn(PANEL[s]).fillna(0.0)
                r, _, _ = multi_tp(PANEL[s], e, cost=C.cost(s))
                allr.extend(r)
            except Exception:
                continue
        n_trials += 1
        st = summarise(np.array(allr))
        results[f"{ename}|multi-TP scaleout"] = st
        if st:
            print(f"  {'multi-TP':16s} {st['n']:7d} {st['expectancy']*100:+8.3f}% "
                  f"{st['win_rate']*100:6.1f}% {st['avg_win']*100:+7.2f}% "
                  f"{st['avg_loss']*100:+8.2f}% {st['t_stat']:+6.2f}", flush=True)

    cum = C.ledger_bump(n_trials, "run6: exit-scheme comparison, liquidation vs ATR control")
    print(f"\nLIFETIME TRIALS: {cum}  (this run added {n_trials})")

    # The verdict: for each entry, does any clever target beat the ATR control?
    print("\n=== VERDICT: clever target vs dumb ATR control, same entries ===")
    for ename in ENTRIES:
        base = results.get(f"{ename}|atr2 (control)")
        if not base:
            continue
        print(f"\n  {ename}  (control expectancy {base['expectancy']*100:+.3f}%)")
        for sname in list(SCHEMES) + ["multi-TP scaleout"]:
            if sname == "atr2 (control)":
                continue
            st = results.get(f"{ename}|{sname}")
            if not st:
                continue
            d = (st["expectancy"] - base["expectancy"]) * 100
            verdict = "BEATS control" if d > 0 else "worse"
            print(f"    {sname:18s} {d:+7.3f}pp   {verdict}")

    json.dump(results, open("/home/claude/qlab/runs/run6.json", "w"), indent=1, default=str)
    print(f"\n({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
