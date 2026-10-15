"""
RUN 9 — THE ILLIQUIDITY HYPOTHESIS.

This is the one direction with a real mechanism behind it that the programme
has never tested.

Mechanism (McLean & Pontiff 2016; Falck/Rej/Thesmar 2021): published edges decay
~26% out-of-sample and ~58% post-publication, BUT decay is measurably LOWER where
arbitrage is costly. Institutional capital cannot be deployed into instruments
that are too small to absorb it. So whatever edge survives should concentrate at
the illiquid end.

Falsifier stated in advance: if edge does NOT increase as liquidity falls — or
only does so before realistic costs are applied — the hypothesis is dead.

THE CONTROL THAT DECIDES THIS TEST:
  Costs MUST scale with illiquidity. Applying BTC's 6bp to a microcap would
  manufacture an edge out of nothing. Cost here is estimated per-symbol from
  the data itself:
      spread proxy  = median (high-low)/close on low-volume days
      impact proxy  = scales with 1/sqrt(median daily quote volume)
  and the result is reported at 1x, 2x and 3x that estimate.

Universe is survivorship-clean: the Binance archive retains delisted symbols,
and every symbol with sufficient history is included whether or not it still trades.
"""
import os, json, numpy as np, pandas as pd
import core as C

ALT = "/home/claude/qlab/data_alt"


def load_all(min_bars=500):
    out = {}
    for f in sorted(os.listdir(ALT)):
        if not f.endswith(".csv"):
            continue
        try:
            d = pd.read_csv(f"{ALT}/{f}", parse_dates=["date"]).set_index("date").sort_index()
        except Exception:
            continue
        if len(d) < min_bars or d.close.le(0).any():
            continue
        out[f[:-4]] = d
    return out


def est_cost(df):
    """Per-symbol round-trip cost estimated FROM THE DATA.
    Half-spread proxy from the daily range on quiet days, plus an impact term
    that grows as median turnover falls. Floored at 10bp, capped at 400bp."""
    rng = ((df.high - df.low) / df.close).replace([np.inf, -np.inf], np.nan).dropna()
    if len(rng) < 50:
        return 0.02
    quiet = rng[rng <= rng.quantile(0.25)].mean()      # quiet-day range
    spread = float(quiet) * 0.5
    qv = float(df.quote_volume.tail(250).median()) if "quote_volume" in df else 1e6
    impact = 0.0005 * np.sqrt(max(1e6, 1.0) / max(qv, 1e3))
    return float(np.clip(spread + impact, 0.0010, 0.0400))


def evaluate(panel, builder, costs, hold=5, mult=1.0):
    rets, per = [], {}
    for s, df in panel.items():
        try:
            pos = builder(df).fillna(0.0)
        except Exception:
            return None
        pos = pos.replace(0.0, np.nan).ffill(limit=hold).fillna(0.0).shift(1).fillna(0.0)
        if pos.sum() == 0:
            continue
        ret = df.close.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(-0.9, 3.0)
        turn = pos.diff().abs().fillna(pos.abs())
        r = pos * ret - turn * costs[s] * mult
        if r.std() == 0:
            continue
        per[s] = float(r.mean() / r.std() * np.sqrt(252))
        rets.append(r.rename(s))
    if len(per) < 10:
        return None
    P = pd.concat(rets, axis=1, sort=True).fillna(0.0).mean(axis=1)
    if P.std() == 0:
        return None
    return dict(sharpe=float(P.mean() / P.std() * np.sqrt(252)),
                breadth=float(np.mean([v > 0 for v in per.values()])),
                n=len(per), mean_sym_sharpe=float(np.mean(list(per.values()))),
                series=P)


SIGNALS = {
    "tsmom60":  lambda df: (df.close / df.close.shift(60) - 1 > 0).astype(float),
    "tsmom120": lambda df: (df.close / df.close.shift(120) - 1 > 0).astype(float),
    "donch20":  lambda df: (df.close > df.high.rolling(20).max().shift(1)).astype(float),
    "rangep50": lambda df: (((df.close - df.low.rolling(50).min()) /
                             (df.high.rolling(50).max() - df.low.rolling(50).min())) > 0.8).astype(float),
    "rev5":     lambda df: ((df.close / df.close.shift(5) - 1) < -0.15).astype(float),
}


def main():
    panel = load_all()
    print(f"universe: {len(panel)} symbols with >=500 daily bars "
          f"(survivorship-clean: delisted symbols retained)\n", flush=True)
    if len(panel) < 40:
        print("not enough symbols ingested yet."); return

    costs = {s: est_cost(d) for s, d in panel.items()}
    liq = {s: float(d.quote_volume.tail(250).median()) if "quote_volume" in d else 0.0
           for s, d in panel.items()}

    order = sorted(panel, key=lambda s: liq[s])
    k = len(order) // 3
    buckets = {"THIN (bottom 3rd)": order[:k],
               "MID": order[k:2 * k],
               "LIQUID (top 3rd)": order[2 * k:]}

    print(f"  {'bucket':20s} {'n':>4} {'med $vol/day':>14} {'est cost':>9}")
    for b, syms in buckets.items():
        print(f"  {b:20s} {len(syms):4d} {np.median([liq[s] for s in syms]):14,.0f} "
              f"{np.median([costs[s] for s in syms])*10000:8.0f}bp")

    n_trials = 0
    print(f"\n{'='*86}")
    print("EDGE BY LIQUIDITY BUCKET — at 1x, 2x and 3x the estimated cost")
    print(f"{'='*86}")
    rows = []
    for sig, fn in SIGNALS.items():
        print(f"\n  {sig}")
        print(f"    {'bucket':20s} {'1x cost':>9} {'2x':>8} {'3x':>8} {'breadth':>9} {'n':>5}")
        for b, syms in buckets.items():
            sub = {s: panel[s] for s in syms}
            r1 = evaluate(sub, fn, costs, mult=1.0); n_trials += 1
            r2 = evaluate(sub, fn, costs, mult=2.0); n_trials += 1
            r3 = evaluate(sub, fn, costs, mult=3.0); n_trials += 1
            if r1 and r2 and r3:
                rows.append(dict(signal=sig, bucket=b, s1=r1["sharpe"], s2=r2["sharpe"],
                                 s3=r3["sharpe"], breadth=r1["breadth"], n=r1["n"]))
                print(f"    {b:20s} {r1['sharpe']:+9.2f} {r2['sharpe']:+8.2f} "
                      f"{r3['sharpe']:+8.2f} {r1['breadth']*100:8.0f}% {r1['n']:5d}")

    print(f"\n{'='*86}")
    print("VERDICT ON THE HYPOTHESIS")
    print(f"{'='*86}")
    df = pd.DataFrame(rows)
    if len(df):
        for mult, col in (("1x", "s1"), ("2x", "s2"), ("3x", "s3")):
            thin = df[df.bucket.str.startswith("THIN")][col].mean()
            liqd = df[df.bucket.str.startswith("LIQUID")][col].mean()
            print(f"  at {mult} estimated cost:  THIN {thin:+.2f}  vs  LIQUID {liqd:+.2f}  "
                  f"-> thin minus liquid = {thin - liqd:+.2f}")
        thin1 = df[df.bucket.str.startswith("THIN")]["s1"].mean()
        thin3 = df[df.bucket.str.startswith("THIN")]["s3"].mean()
        print(f"\n  thin-bucket edge survives cost tripling? "
              f"{thin1:+.2f} -> {thin3:+.2f}  "
              f"{'YES' if thin3 > 0 else 'NO — it is a cost artefact'}")

    cum = C.ledger_bump(n_trials, "run9: illiquidity hypothesis, survivorship-clean alt universe")
    print(f"\nLIFETIME TRIALS: {cum}  (this run: {n_trials})")
    if len(df):
        df.to_csv("/home/claude/qlab/runs/run9.csv", index=False)


if __name__ == "__main__":
    main()
