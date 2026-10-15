"""
RUN 7 — positioning signals on hourly bars.

First test in the programme using an input that is NOT derived from price:
real open interest and real trader positioning from the Binance public archive.

Three questions, kept separate:

  Q1  Do positioning signals beat matched-random entry at the same exposure?
  Q2  Do they beat the SAME gates applied to price-only signals on the same
      hourly bars? (If price-only does just as well, positioning adds nothing.)
  Q3  Does multi-timeframe confluence help? Signals are computed on 1h, 4h and
      daily resamples of the same series and required to agree.

Costs: 6bp round trip on crypto perps (maker/taker plus slippage). Reported as
a breakeven figure as well, so the assumption is visible rather than load-bearing.
"""
import os, json, time, itertools, numpy as np, pandas as pd
import core as C
import oi_signals as OS

PX = "/home/claude/qlab/data_1h"
COST = 0.0006

SYMS = sorted(f[:-4] for f in os.listdir(PX) if f.endswith(".csv")
              and os.path.exists(f"/home/claude/qlab/data_oi/{f}"))


def load_joined(sym, rule="1h"):
    p = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    if rule != "1h":
        p = p.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                  "close": "last", "volume": "sum",
                                  "taker_buy_volume": "sum"}).dropna()
    oi = OS.load_oi(sym, rule)
    return OS.join_price(oi, p)


PANEL = {}
for s in SYMS:
    for rule in ("1h", "4h", "1D"):
        try:
            j = load_joined(s, rule)
            if len(j) > 500:
                PANEL[(s, rule)] = j
        except Exception:
            pass


def evaluate(builder, rule, hold=4, label=""):
    rets, per = [], {}
    for s in SYMS:
        j = PANEL.get((s, rule))
        if j is None:
            continue
        try:
            pos = builder(j).fillna(0.0)
        except Exception:
            return None
        pos = pos.replace(0.0, np.nan).ffill(limit=hold).fillna(0.0).shift(1).fillna(0.0)
        if pos.sum() == 0:
            continue
        ret = j.close.pct_change().fillna(0.0)
        turn = pos.diff().abs().fillna(pos.abs())
        g = pos * ret
        r = g - turn * COST
        st = C.stats(r, pos)
        if st is None:
            continue
        per[s] = st
        rets.append(r.rename(s))
    if len(per) < 3:
        return None
    P = pd.concat(rets, axis=1, sort=True).fillna(0.0).mean(axis=1)
    bars = {"1h": 24 * 365, "4h": 6 * 365, "1D": 365}[rule]
    x = P[P != 0]
    if len(x) < 200 or x.std() == 0:
        return None
    sharpe = float(P.mean() / P.std() * np.sqrt(bars))
    gross = float(pd.concat([p for p in rets], axis=1).fillna(0).mean(axis=1).mean())
    turnover = float(np.mean([v["trades"] for v in per.values()]))
    return dict(label=label, rule=rule, sharpe=sharpe,
                expectancy=float(P.mean()), total=float((1 + P).prod() - 1),
                breadth_n=int(sum(1 for v in per.values() if v["sharpe"] > 0)),
                breadth_of=len(per), trades=turnover,
                exposure=float(np.mean([v["exposure"] for v in per.values()])))


def main():
    print(f"RUN 7 — positioning signals, {len(SYMS)} symbols with both price and "
          f"positioning data: {SYMS}\n", flush=True)
    results, n_trials = [], 0

    # ---- Q1: positioning signals, each timeframe separately
    for rule in ("1h", "4h", "1D"):
        print(f"\n=== {rule} bars")
        print(f"  {'signal':22s} {'Sharpe':>7} {'expect/bar':>11} {'breadth':>8} {'exp%':>6}")
        for name, (fn, params) in OS.SIGNALS.items():
            for p in params:
                n_trials += 1
                r = evaluate(lambda df, fn=fn, p=p: fn(df, *p), rule,
                             label=f"{name}{p}")
                if r:
                    results.append(r)
                    print(f"  {r['label']:22s} {r['sharpe']:+7.2f} "
                          f"{r['expectancy']*100:+10.4f}% "
                          f"{r['breadth_n']:3d}/{r['breadth_of']:<4d} "
                          f"{r['exposure']*100:5.1f}%", flush=True)

    # ---- Q2: price-only control on the SAME bars
    print(f"\n=== PRICE-ONLY CONTROL (same bars, same gates)")
    CTRL = {
        "tsmom24":  lambda df: (df.close / df.close.shift(24) - 1 > 0).astype(float),
        "donch48":  lambda df: (df.close > df.high.rolling(48).max().shift(1)).astype(float),
        "rsi2":     lambda df: C.s_rsi(df, 2, 10),
        "rangep":   lambda df: C.s_range_pos(df, 48, 0.8),
    }
    for rule in ("1h", "4h", "1D"):
        for name, fn in CTRL.items():
            n_trials += 1
            r = evaluate(fn, rule, label=f"CTRL {name}")
            if r:
                results.append(r)
                print(f"  {rule:3s} {r['label']:18s} {r['sharpe']:+7.2f} "
                      f"{r['expectancy']*100:+10.4f}% {r['breadth_n']:3d}/{r['breadth_of']:<4d}",
                      flush=True)

    # ---- Q3: multi-timeframe confluence
    print(f"\n=== MULTI-TIMEFRAME CONFLUENCE (1h signal must agree with 4h and 1D)")
    for name, (fn, params) in OS.SIGNALS.items():
        p = params[len(params) // 2]
        def mtf(df, fn=fn, p=p):
            base = fn(df, *p)
            d4 = fn(df.resample("4h").last().ffill(), *p).reindex(df.index, method="ffill")
            dd = fn(df.resample("1D").last().ffill(), *p).reindex(df.index, method="ffill")
            return (base * d4.fillna(0) * dd.fillna(0)).fillna(0.0)
        n_trials += 1
        r = evaluate(mtf, "1h", label=f"MTF {name}{p}")
        if r:
            results.append(r)
            print(f"  {r['label']:26s} {r['sharpe']:+7.2f} {r['expectancy']*100:+10.4f}% "
                  f"{r['breadth_n']:3d}/{r['breadth_of']:<4d} {r['exposure']*100:5.1f}%",
                  flush=True)

    cum = C.ledger_bump(n_trials, "run7: positioning signals, hourly, MTF confluence")
    print(f"\nLIFETIME TRIALS: {cum}  (this run: {n_trials})")

    pos_only = [r for r in results if not r["label"].startswith(("CTRL", "MTF"))]
    ctrl = [r for r in results if r["label"].startswith("CTRL")]
    mtf_r = [r for r in results if r["label"].startswith("MTF")]
    if pos_only and ctrl:
        bp = max(pos_only, key=lambda x: x["sharpe"])
        bc = max(ctrl, key=lambda x: x["sharpe"])
        print(f"\n  best POSITIONING signal: {bp['label']} ({bp['rule']}) "
              f"Sharpe {bp['sharpe']:+.2f}")
        print(f"  best PRICE-ONLY control: {bc['label']} ({bc['rule']}) "
              f"Sharpe {bc['sharpe']:+.2f}")
        print(f"  --> positioning data adds "
              f"{bp['sharpe'] - bc['sharpe']:+.2f} Sharpe over price alone")
    if mtf_r:
        bm = max(mtf_r, key=lambda x: x["sharpe"])
        print(f"  best MULTI-TIMEFRAME: {bm['label']} Sharpe {bm['sharpe']:+.2f}")

    json.dump(results, open("/home/claude/qlab/runs/run7.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
