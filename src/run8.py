"""
RUN 8 — is multi-timeframe confluence real, or is it just "trade less"?

Run 7 found MTF confluence turned oi_price_up from -0.86 Sharpe to +1.96.
That is the only idea all programme that IMPROVED a result. Before believing it,
three alternative explanations must be killed:

  A. IT ONLY WORKS ON POSITIONING SIGNALS.
     Test: apply the same MTF treatment to price-only signals. If it lifts
     those too, confluence is the finding and positioning is irrelevant.

  B. IT IS JUST LOWER EXPOSURE.
     MTF cut exposure to 1.7% of bars. A rule that trades rarely avoids cost
     drag and chop. Control: RANDOM entries at the SAME low exposure and the
     same average holding period. If random-at-1.7%-exposure scores similarly,
     the confluence is doing nothing.

  C. IT IS A SMALL-SAMPLE ARTEFACT.
     1.7% of 400 days is very few independent events. Control: block bootstrap
     over calendar months, and per-symbol breakdown. A result driven by one
     symbol or one month is not a result.

Now with all 8 symbols (was 4).
"""
import os, json, numpy as np, pandas as pd
import core as C
import oi_signals as OS

PX = "/home/claude/qlab/data_1h"
COST = 0.0006
SYMS = sorted(f[:-4] for f in os.listdir(PX) if f.endswith(".csv")
              and os.path.exists(f"/home/claude/qlab/data_oi/{f}"))
BARS_YR = 24 * 365


def joined(sym):
    p = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    oi = OS.load_oi(sym, "1h")
    return OS.join_price(oi, p)


PANEL = {}
for s in SYMS:
    try:
        j = joined(s)
        if len(j) > 1000:
            PANEL[s] = j
    except Exception:
        pass
print(f"{len(PANEL)} symbols with both price and positioning: {list(PANEL)}\n", flush=True)


def run(builder, hold=4, per_symbol=False):
    rets, per = [], {}
    for s, j in PANEL.items():
        try:
            pos = builder(j).fillna(0.0)
        except Exception:
            return None
        pos = pos.replace(0.0, np.nan).ffill(limit=hold).fillna(0.0).shift(1).fillna(0.0)
        if pos.sum() == 0:
            continue
        ret = j.close.pct_change().fillna(0.0)
        turn = pos.diff().abs().fillna(pos.abs())
        r = pos * ret - turn * COST
        if r.std() == 0:
            continue
        per[s] = dict(sharpe=float(r.mean() / r.std() * np.sqrt(BARS_YR)),
                      exposure=float((pos.abs() > 0).mean()),
                      total=float((1 + r).prod() - 1))
        rets.append(r.rename(s))
    if len(per) < 4:
        return None
    P = pd.concat(rets, axis=1, sort=True).fillna(0.0).mean(axis=1)
    if P.std() == 0:
        return None
    out = dict(sharpe=float(P.mean() / P.std() * np.sqrt(BARS_YR)),
               exposure=float(np.mean([v["exposure"] for v in per.values()])),
               breadth=int(sum(1 for v in per.values() if v["sharpe"] > 0)),
               n=len(per), total=float((1 + P).prod() - 1), series=P)
    if per_symbol:
        out["per"] = {k: round(v["sharpe"], 2) for k, v in per.items()}
    return out


def mtf(fn, p):
    """LOOKAHEAD FIX. A resampled bar labelled T contains data up to the END of
    that period, so reindexing it back with ffill lets bar T see its own future.
    Each higher-timeframe series is therefore shifted by one full period, so an
    hourly decision only ever sees COMPLETED 4h and daily bars."""
    def f(df):
        base = fn(df, *p)
        h4 = df.resample("4h").agg({"open":"first","high":"max","low":"min",
                                    "close":"last","volume":"sum"}).dropna()
        d1 = df.resample("1D").agg({"open":"first","high":"max","low":"min",
                                    "close":"last","volume":"sum"}).dropna()
        for c in df.columns:
            if c not in h4.columns and df[c].dtype.kind in "fi":
                h4[c] = df[c].resample("4h").last()
                d1[c] = df[c].resample("1D").last()
        s4 = fn(h4, *p).shift(1).reindex(df.index, method="ffill")
        sd = fn(d1, *p).shift(1).reindex(df.index, method="ffill")
        return (base * s4.fillna(0) * sd.fillna(0)).fillna(0.0)
    return f


# price-only signals, defined on the joined frame
def px_tsmom(df, lb): return (df.close / df.close.shift(lb) - 1 > 0).astype(float)
def px_donch(df, lb): return (df.close > df.high.rolling(lb).max().shift(1)).astype(float)
def px_rangep(df, lb, th):
    lo = df.low.rolling(lb).min(); hi = df.high.rolling(lb).max()
    return (((df.close - lo) / (hi - lo)) > th).astype(float)
def px_rsi(df, lb, th):
    d = df.close.diff(); up = d.clip(lower=0).rolling(lb).mean()
    dn = (-d.clip(upper=0)).rolling(lb).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan)) < th).astype(float)


def random_at_exposure(exposure, hold, seed, n=100):
    """Control B: random entries at matched exposure and holding period."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        rets = []
        for s, j in PANEL.items():
            ret = j.close.pct_change().fillna(0.0)
            p = max(exposure / max(hold, 1), 1e-6)
            raw = (rng.random(len(ret)) < p).astype(float)
            pos = pd.Series(raw, index=ret.index).replace(0.0, np.nan)\
                    .ffill(limit=hold).fillna(0.0).shift(1).fillna(0.0)
            turn = pos.diff().abs().fillna(pos.abs())
            r = pos * ret - turn * COST
            rets.append(r.rename(s))
        P = pd.concat(rets, axis=1, sort=True).fillna(0.0).mean(axis=1)
        if P.std() > 0:
            out.append(float(P.mean() / P.std() * np.sqrt(BARS_YR)))
    return np.array(out)


def month_bootstrap(series, n=2000, seed=3):
    """Control C: resample calendar months with replacement."""
    rng = np.random.default_rng(seed)
    g = [x for _, x in series.groupby([series.index.year, series.index.month])]
    if len(g) < 6:
        return None
    out = []
    for _ in range(n):
        pick = [g[i] for i in rng.integers(0, len(g), len(g))]
        v = pd.concat(pick)
        if v.std() > 0:
            out.append(float(v.mean() / v.std() * np.sqrt(BARS_YR)))
    return np.array(out)


def main():
    n_trials = 0
    print("=" * 78)
    print("A. DOES MTF HELP PRICE-ONLY SIGNALS TOO?")
    print("=" * 78)
    print(f"  {'signal':22s} {'plain':>8} {'MTF':>8} {'delta':>8} {'exp%':>7} {'breadth':>8}")
    PX_SIGS = [("tsmom24", px_tsmom, (24,)), ("tsmom72", px_tsmom, (72,)),
               ("donch48", px_donch, (48,)), ("donch168", px_donch, (168,)),
               ("rangep48", px_rangep, (48, 0.8)), ("rsi14", px_rsi, (14, 30))]
    px_deltas = []
    for name, fn, p in PX_SIGS:
        a = run(lambda df, fn=fn, p=p: fn(df, *p)); n_trials += 1
        b = run(mtf(fn, p)); n_trials += 1
        if a and b:
            d = b["sharpe"] - a["sharpe"]
            px_deltas.append(d)
            print(f"  {name:22s} {a['sharpe']:+8.2f} {b['sharpe']:+8.2f} {d:+8.2f} "
                  f"{b['exposure']*100:6.1f}% {b['breadth']:3d}/{b['n']}")

    print()
    print("=" * 78)
    print("   POSITIONING SIGNALS, same treatment, now 8 symbols")
    print("=" * 78)
    print(f"  {'signal':22s} {'plain':>8} {'MTF':>8} {'delta':>8} {'exp%':>7} {'breadth':>8}")
    best = None
    oi_deltas = []
    for name, (fn, params) in OS.SIGNALS.items():
        p = params[len(params) // 2]
        a = run(lambda df, fn=fn, p=p: fn(df, *p)); n_trials += 1
        b = run(mtf(fn, p), per_symbol=True); n_trials += 1
        if a and b:
            d = b["sharpe"] - a["sharpe"]
            oi_deltas.append(d)
            print(f"  {name+str(p):22s} {a['sharpe']:+8.2f} {b['sharpe']:+8.2f} {d:+8.2f} "
                  f"{b['exposure']*100:6.1f}% {b['breadth']:3d}/{b['n']}")
            if best is None or b["sharpe"] > best[1]["sharpe"]:
                best = (f"MTF {name}{p}", b)

    print(f"\n  mean MTF delta, price-only signals : {np.mean(px_deltas):+.2f}")
    print(f"  mean MTF delta, positioning signals: {np.mean(oi_deltas):+.2f}")

    if best is None:
        print("\nno MTF candidate to stress.")
        C.ledger_bump(n_trials, "run8: MTF confluence stress tests")
        return

    label, B = best
    print()
    print("=" * 78)
    print(f"B. IS IT JUST LOW EXPOSURE?   stressing: {label}")
    print("=" * 78)
    print(f"  observed Sharpe {B['sharpe']:+.2f} at {B['exposure']*100:.2f}% exposure, "
          f"positive on {B['breadth']}/{B['n']} symbols")
    print(f"  per-symbol: {B.get('per')}")
    rnd = random_at_exposure(B["exposure"], 4, seed=11, n=100)
    n_trials += 1
    if len(rnd):
        pct = float((rnd < B["sharpe"]).mean())
        print(f"\n  RANDOM entries at the SAME {B['exposure']*100:.2f}% exposure, same hold:")
        print(f"    mean {rnd.mean():+.2f}, sd {rnd.std():.2f}, "
              f"95th pct {np.percentile(rnd,95):+.2f}, max {rnd.max():+.2f}")
        print(f"    --> observed sits at the {pct*100:.1f}th percentile of random")
        print(f"    --> {'SURVIVES' if pct >= 0.95 else 'FAILS — indistinguishable from trading rarely at random'}")

    print()
    print("=" * 78)
    print("C. IS IT A SMALL-SAMPLE ARTEFACT?")
    print("=" * 78)
    bs = month_bootstrap(B["series"])
    if bs is not None:
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f"  month block bootstrap, 2000 draws: mean {bs.mean():+.2f}, "
              f"95% CI [{lo:+.2f}, {hi:+.2f}]")
        print(f"  fraction of draws above zero: {float((bs>0).mean())*100:.1f}%")
        print(f"  --> {'CI excludes zero' if lo > 0 else 'CI INCLUDES ZERO — not established'}")
    yr = B["series"].groupby([B["series"].index.year, B["series"].index.month]).sum()
    print(f"  positive months: {int((yr>0).sum())}/{len(yr)}")
    print(f"  best month contributes {yr.max()/yr[yr>0].sum()*100:.0f}% of all gains")

    cum = C.ledger_bump(n_trials, "run8: MTF confluence stress tests")
    print(f"\nLIFETIME TRIALS: {cum}  (this run: {n_trials})")


if __name__ == "__main__":
    main()
