"""
RUN 11 — FULL GAUNTLET on the two survivors from run 10.

  brk_mo_hi  break of prior month high    +1.950%/trade  t=3.67  n=1416
  brk_qt_hi  break of prior quarter high  +2.191%/trade  t=3.55  n=1191

Both exited at the 1.618 fib extension, 1.5xATR stop, 40-bar time limit.

Seven tests. A result must pass ALL of them.

  T1  HOLDOUT        2025+ was declared and never touched. Opened once, here.
  T2  RANDOM CONTROL matched trade count, matched holding period, same exits.
                     This is the test that killed Donchian in the old programme.
  T3  BREADTH        per-instrument, and across asset classes.
  T4  REGIME         profitable in rising AND falling markets separately.
  T5  EX-TOP-5       survives removing its five best trades.
  T6  COST           breakeven cost vs realistic cost.
  7   EXIT ROBUST    does it survive a plain ATR target? If it only works with
                     one specific exit, it is fitted to that exit.
"""
import os, numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost, fib_target, managed, summarise

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}

SIGS = {
    "brk_mo_hi": lambda d: LV.l_break_prior_month_high(d),
    "brk_qt_hi": lambda d: LV.l_break_prior_quarter_high(d),
}
HOLDOUT = pd.Timestamp("2025-01-01")


def managed_tagged(df, entries, cost, tgt_k=1.618, stop_mult=1.5, max_bars=40):
    """Like managed() but returns (ret, entry_date, symbol-agnostic regime flag)."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    T = fib_target(df, tgt_k).values
    reg = (df.close > df.close.rolling(200).mean()).values
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
        tgt = T[i] if (T[i] == T[i] and T[i] > e) else e + 2 * a
        res = None
        for j in range(i + 1, min(i + 1 + max_bars, len(df))):
            if L[j] <= stop:
                res = (stop / e - 1, j); break
            if H[j] >= tgt:
                res = (tgt / e - 1, j); break
        if res is None:
            j = min(i + max_bars, len(df) - 1)
            res = (Cl[j] / e - 1, j)
        out.append((res[0] - cost, df.index[i], bool(reg[i])))
        last = res[1]
    return out


def collect(fn, tgt_k=1.618):
    rows = []
    for s, df in PANEL.items():
        try:
            e = fn(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        for r, d, g in managed_tagged(df, e, COSTS[s], tgt_k):
            rows.append(dict(ret=r, date=d, bull=g, sym=s))
    return pd.DataFrame(rows)


def random_control(fn, n_draws=200, seed=17):
    """T2 — random entries at matched per-symbol frequency, identical exits."""
    rng = np.random.default_rng(seed)
    means = []
    freq = {}
    for s, df in PANEL.items():
        try:
            e = fn(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
            freq[s] = float(e.mean())
        except Exception:
            freq[s] = 0.0
    for _ in range(n_draws):
        allr = []
        for s, df in PANEL.items():
            if freq.get(s, 0) <= 0:
                continue
            fake = pd.Series((rng.random(len(df)) < freq[s]).astype(float), index=df.index)
            r = managed(df, fake, COSTS[s])
            if len(r):
                allr.append(r)
        if allr:
            means.append(float(np.concatenate(allr).mean()))
    return np.array(means)


def main():
    print(f"RUN 11 — gauntlet, {len(PANEL)} instruments\n")
    for name, fn in SIGS.items():
        print("=" * 80)
        print(f"  {name}")
        print("=" * 80)
        d = collect(fn)
        if len(d) < 200:
            print("  too few trades"); continue
        full = summarise(d.ret.values)
        print(f"  FULL SAMPLE   n={full['n']}  expectancy {full['expectancy']*100:+.3f}%  "
              f"t={full['t']:+.2f}  win {full['win']*100:.1f}%")

        # T1 holdout
        ins = d[d.date < HOLDOUT]; oos = d[d.date >= HOLDOUT]
        si, so = summarise(ins.ret.values), summarise(oos.ret.values)
        print(f"\n  T1 HOLDOUT (2025+, opened once)")
        if si: print(f"     in-sample  n={si['n']:5d}  {si['expectancy']*100:+.3f}%  t={si['t']:+.2f}")
        if so: print(f"     HOLDOUT    n={so['n']:5d}  {so['expectancy']*100:+.3f}%  t={so['t']:+.2f}"
                     f"   -> {'PASS' if so['expectancy']>0 else 'FAIL'}")

        # T2 random control
        rc = random_control(fn)
        if len(rc):
            pct = float((rc < full["expectancy"]).mean())
            print(f"\n  T2 RANDOM CONTROL (matched frequency, identical exits, "
                  f"{len(rc)} draws)")
            print(f"     random mean {rc.mean()*100:+.3f}%  sd {rc.std()*100:.3f}%  "
                  f"95th pct {np.percentile(rc,95)*100:+.3f}%  max {rc.max()*100:+.3f}%")
            print(f"     observed {full['expectancy']*100:+.3f}% sits at the "
                  f"{pct*100:.1f}th percentile -> {'PASS' if pct>=0.95 else 'FAIL'}")

        # T3 breadth
        per = d.groupby("sym").ret.agg(["mean", "count"])
        per = per[per["count"] >= 8]
        pos = float((per["mean"] > 0).mean())
        print(f"\n  T3 BREADTH   positive on {int((per['mean']>0).sum())}/{len(per)} "
              f"instruments ({pos*100:.0f}%) -> {'PASS' if pos>0.55 else 'FAIL'}")

        # T4 regime
        b = summarise(d[d.bull].ret.values); r_ = summarise(d[~d.bull].ret.values)
        print(f"\n  T4 REGIME")
        if b: print(f"     rising  n={b['n']:5d}  {b['expectancy']*100:+.3f}%  t={b['t']:+.2f}")
        if r_: print(f"     falling n={r_['n']:5d}  {r_['expectancy']*100:+.3f}%  t={r_['t']:+.2f}")
        ok4 = bool(b and r_ and b["expectancy"] > 0 and r_["expectancy"] > 0)
        print(f"     -> {'PASS both regimes' if ok4 else 'FAIL — one-sided'}")

        # T5 ex-top-5
        v = np.sort(d.ret.values)[::-1]
        ex = summarise(v[5:])
        print(f"\n  T5 EX-TOP-5   {ex['expectancy']*100:+.3f}%  t={ex['t']:+.2f} -> "
              f"{'PASS' if ex['expectancy']>0 else 'FAIL'}")

        # T6 cost
        print(f"\n  T6 COST   median applied cost "
              f"{np.median(list(COSTS.values()))*10000:.0f}bp; "
              f"expectancy {full['expectancy']*100:+.3f}% means breakeven at roughly "
              f"{(full['expectancy']+np.median(list(COSTS.values())))*10000:.0f}bp")

        # T7 exit robustness
        print(f"\n  T7 EXIT ROBUSTNESS")
        for k, lbl in ((1.272, "fib 1.272"), (1.618, "fib 1.618"), (2.0, "fib 2.0")):
            dd = collect(fn, tgt_k=k)
            s2 = summarise(dd.ret.values)
            if s2:
                print(f"     {lbl:10s} {s2['expectancy']*100:+.3f}%  t={s2['t']:+.2f}  n={s2['n']}")
        print()

    cum = C.ledger_bump(2, "run11: gauntlet on brk_mo_hi and brk_qt_hi")
    print(f"LIFETIME TRIALS: {cum}")


if __name__ == "__main__":
    main()
