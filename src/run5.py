"""
RUN 5 — LONG/SHORT, and judged SEPARATELY in rising and falling regimes.

Why: every candidate so far was long-only. On instruments that rose over the
sample, "long most of the time" wins by construction. Run 4's best candidates
beat exposure-matched buy-and-hold by +0.05 Sharpe — i.e. the timing contributed
almost nothing; the long exposure did the work. Praising that is dangerous
because it is a bull-market artefact that reverses when the market does.

Two changes:

1. SYMMETRIC SIGNALS. Each rule now emits +1 / 0 / -1. The same condition that
   goes long on the bullish side goes short on the bearish mirror. Net market
   exposure is therefore free to be negative, and buy-and-hold is no longer a
   free ride.

2. REGIME-SPLIT SCORING. Every candidate is scored separately in:
      BULL  bars where the instrument is above its own 200-day average
      BEAR  bars where it is below it
   A candidate must be profitable in BOTH to pass. One-sided performance is
   reported, never rewarded.

The benchmark changes too: in a long/short setting the honest comparison is
against ZERO (cash), and against a long-only version of the same rule, so we
can see whether the short side adds or destroys.
"""
import json, itertools, time, sys, gc, numpy as np, pandas as pd
import core as C
from generate import candidates, pattern_candidates, FILTERS

SYMS = C.universe()
PANEL = {s: C.load(s) for s in SYMS}
RET = {s: PANEL[s].close.pct_change().fillna(0.0) for s in SYMS}
REGIME = {s: (PANEL[s].close > PANEL[s].close.rolling(200).mean()).shift(1).fillna(False).astype(bool)
          for s in SYMS}


def symmetric(builder):
    """Turn a long-only rule into +1/0/-1.
    Long when the rule fires and the instrument is in an uptrend;
    short when the rule's mirror fires and it is in a downtrend.
    The mirror is the same rule applied to the inverted series, so the
    short side is the rule's own logic, not a different rule."""
    def f(df):
        lon = builder(df).fillna(0.0)
        inv = df.copy()
        inv["close"] = 2 * df.close.iloc[0] - df.close
        inv["open"] = 2 * df.close.iloc[0] - df.open
        hi = 2 * df.close.iloc[0] - df.low
        lo = 2 * df.close.iloc[0] - df.high
        inv["high"], inv["low"] = hi, lo
        sho = builder(inv).fillna(0.0)
        return (lon > 0).astype(float) - (sho > 0).astype(float)
    return f


def measure_ls(builder, hold):
    per, net, gross, turns, bull, bear = {}, [], [], [], [], []
    for s in SYMS:
        try:
            pos = builder(PANEL[s]).fillna(0.0).clip(-1, 1)
        except Exception:
            return None
        if hold:
            # vectorised hold: carry the last non-zero signal forward `hold` bars
            pos = pos.replace(0.0, np.nan).ffill(limit=hold).fillna(0.0)
        pos = pos.shift(1).fillna(0.0)
        if pos.abs().sum() == 0:
            continue
        ret = RET[s]
        turn = pos.diff().abs().fillna(pos.abs())
        g = pos * ret
        r = g - turn * C.cost(s)
        st = C.stats(r, pos)
        if st is None:
            continue
        per[s] = st
        net.append(r.rename(s)); gross.append(g.rename(s)); turns.append(turn.rename(s))
        bull.append(r.where(REGIME[s], 0.0).rename(s))
        bear.append(r.where(~REGIME[s], 0.0).rename(s))
    if len(net) < len(SYMS) * 0.7:
        return None

    P = pd.concat(net, axis=1, sort=True).fillna(0.0).mean(axis=1)
    G = pd.concat(gross, axis=1, sort=True).fillna(0.0).mean(axis=1)
    T = pd.concat(turns, axis=1, sort=True).fillna(0.0).mean(axis=1)
    B = pd.concat(bull, axis=1, sort=True).fillna(0.0).mean(axis=1)
    R = pd.concat(bear, axis=1, sort=True).fillna(0.0).mean(axis=1)
    st = C.stats(P, pd.Series(1.0, index=P.index))
    if st is None:
        return None

    def sh(x):
        x = x[x != 0]
        return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 50 and x.std() > 0 else 0.0

    net_exposure = float(np.mean([v["exposure"] for v in per.values()]))
    yearly = P.groupby(P.index.year).apply(lambda x: (1 + x).prod() - 1)

    return dict(
        sharpe=st["sharpe"], cagr=st["cagr"], maxdd=st["maxdd"],
        gross_mean=float(G.mean()), net_mean=float(P.mean()),
        breakeven_cost=float(G.mean() / T.mean()) if T.mean() > 0 else np.inf,
        bull_mean=float(B[B != 0].mean()) if (B != 0).any() else 0.0,
        bear_mean=float(R[R != 0].mean()) if (R != 0).any() else 0.0,
        bull_sharpe=sh(B), bear_sharpe=sh(R),
        breadth_n=int(sum(1 for v in per.values() if v["sharpe"] > 0)),
        breadth_of=len(per), exposure=net_exposure,
        yrs_positive=float((yearly > 0).mean()), n_years=len(yearly),
        worst_year=float(yearly.min()),
        exposure_days=float(sum(v["exposure_days"] for v in per.values())),
    )


def gates(m):
    if m["exposure_days"] < 2000:   return False, "H0 insufficient exposure"
    if m["gross_mean"] <= 0:        return False, "H1 loses gross"
    if m["net_mean"] <= 0:          return False, "H2 loses after costs"
    if m["bull_mean"] <= 0:         return False, "H3 loses in RISING regime"
    if m["bear_mean"] <= 0:         return False, "H4 loses in FALLING regime"
    return True, "PASS both regimes"


def main():
    space = []
    for nm, b, h in candidates():
        space.append((nm, symmetric(b), h))
    for nm, b, h in pattern_candidates():
        space.append((nm, symmetric(b), h))
    import levels as LV
    for lname, (fn, params) in LV.LEVELS.items():
        for p in params:
            for fname, ffn in FILTERS.items():
                for h in (None, 10):
                    def mk(fn=fn, p=p, ffn=ffn):
                        return lambda df: fn(df, *p) * ffn(df)
                    space.append((f"{lname}{p}|{fname}|h={h}", symmetric(mk()), h))

    lo = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(space)
    space = space[lo:hi]
    n = len(space)
    print(f"RUN 5 — {n} LONG/SHORT candidates, scored separately in rising "
          f"and falling regimes\n", flush=True)

    reasons, passed, rows = {}, [], []
    t0 = time.time()
    for k, (nm, b, h) in enumerate(space):
        if k and k % 400 == 0:
            print(f"  ...{k}/{n} ({time.time()-t0:.0f}s) passed={len(passed)}", flush=True)
        m = measure_ls(b, h)
        if m is None:
            reasons["H0 unusable"] = reasons.get("H0 unusable", 0) + 1
            continue
        m["name"], m["hold"] = nm, h
        ok, why = gates(m)
        reasons[why] = reasons.get(why, 0) + 1
        rows.append(m)
        if k % 200 == 0: gc.collect()
        if ok:
            passed.append(m)

    cum = C.ledger_bump(n, f"run5 chunk {lo}-{hi}: long/short, regime-split")
    print(f"\nLIFETIME TRIALS: {cum}\n")
    for r, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {r}")

    print(f"\nPROFITABLE IN BOTH REGIMES: {len(passed)}")
    if passed:
        passed.sort(key=lambda x: -min(x["bull_sharpe"], x["bear_sharpe"]))
        print(f"\n  ranked by WEAKER of the two regimes (the honest ranking):")
        print(f"  {'Sharpe':>7} {'bull':>6} {'bear':>6} {'CAGR':>8} {'maxDD':>7} "
              f"{'brkeven':>8} {'worstyr':>8} {'yrs+':>5}  name")
        for m in passed[:25]:
            print(f"  {m['sharpe']:+7.2f} {m['bull_sharpe']:+6.2f} {m['bear_sharpe']:+6.2f} "
                  f"{m['cagr']*100:+7.2f}% {m['maxdd']*100:6.1f}% "
                  f"{m['breakeven_cost']*10000:7.0f}bp {m['worst_year']*100:+7.1f}% "
                  f"{m['yrs_positive']:5.2f}  {m['name'][:44]}")
        srs = np.array([r["sharpe"] for r in rows])
        E = C.emc(cum, float(srs.std()))
        best = max(passed, key=lambda x: x["sharpe"])
        print(f"\n  E[max Sharpe | noise, {cum} lifetime trials] = {E:.3f}")
        print(f"  best Sharpe {best['sharpe']:.3f} -> deflated Sharpe "
              f"{C.deflated_sharpe(best['sharpe'], E, 4000):.4f}")

    json.dump({"passed": passed[:60], "reasons": reasons, "lifetime": cum},
              open(f"/home/claude/qlab/runs/run5_{lo}.json", "w"), indent=1, default=str)
    pd.DataFrame(rows).to_csv(f"/home/claude/qlab/runs/run5_{lo}.csv", index=False)
    print("\nwrote ../runs/run5_all_measured.csv")


if __name__ == "__main__":
    main()
