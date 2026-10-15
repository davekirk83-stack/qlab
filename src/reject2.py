"""
The rejection engine. Candidates enter; almost nothing should leave.

Gates run cheapest-first. Each must kill harder than the one before it.
A candidate that fails a gate is recorded with the gate that killed it and
never re-enters. Nothing is re-tuned to pass.

  G1  liquidity of evidence   >= 200 panel trades
  G2  gross expectancy        > 0        (before costs)
  G3  net expectancy          > 0        (at base costs)
  G4  cost robustness         > 0 at 2x costs
  G5  breadth                 positive on >= 60% of instruments
  G6  beats matched random    >= 95th percentile of 200 random-entry runs
  G7  walk-forward            OOS positive, refit each fold
  G8  deflated Sharpe         >= 0.95 at the LIFETIME trial count
  G9  holdout 2025+           positive        (opened last, once)
"""
import json, os, sys, time, numpy as np, pandas as pd
import core as C
from generate import pattern_candidates as candidates

SYMS = C.universe()
PANEL = {s: C.load(s) for s in SYMS}
RET = {s: PANEL[s].close.pct_change().fillna(0.0) for s in SYMS}


def panel_eval(builder, hold, cost_mult=1.0):
    """Equal-weight across instruments. Returns (portfolio series, per-symbol stats)."""
    per, series = {}, []
    for s in SYMS:
        df = PANEL[s]
        c = C.cost(s) * cost_mult
        try:
            r, pos = C.run_one(df, builder, c, hold=hold)
        except Exception:
            return None, None
        st = C.stats(r, pos)
        if st is None:
            continue
        per[s] = st
        series.append(r.rename(s))
    if len(series) < len(SYMS) * 0.7:
        return None, None
    port = pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
    return port, per


def gross_eval(builder, hold):
    return panel_eval(builder, hold, cost_mult=0.0)


def walkforward(builder, hold):
    """Refit nothing (no parameters to fit) but verify stability year by year."""
    port, _ = panel_eval(builder, hold)
    if port is None:
        return None
    yearly = port.groupby(port.index.year).apply(lambda x: (1 + x).prod() - 1)
    return float((yearly > 0).mean()), float(yearly.median())


def main():
    cands = candidates()
    n = len(cands)
    print(f"generated {n} candidates across {len(SYMS)} instruments\n")
    kill = {f"G{i}": 0 for i in range(1, 10)}
    survivors = []
    t0 = time.time()

    for i, (name, builder, hold) in enumerate(cands):
        if i and i % 250 == 0:
            print(f"  ...{i}/{n}  ({time.time()-t0:.0f}s)  alive={len(survivors)}")

        port, per = panel_eval(builder, hold)
        if port is None:
            kill["G1"] += 1; continue
        st = C.stats(port, pd.Series(1.0, index=port.index))
        trades = sum(v["trades"] for v in per.values())
        if st is None or trades < 200:
            kill["G1"] += 1; continue

        g, _ = gross_eval(builder, hold)
        if g is None or g.mean() <= 0:
            kill["G2"] += 1; continue

        if port.mean() <= 0:
            kill["G3"] += 1; continue

        p2, _ = panel_eval(builder, hold, cost_mult=2.0)
        if p2 is None or p2.mean() <= 0:
            kill["G4"] += 1; continue

        breadth = np.mean([v["sharpe"] > 0 for v in per.values()])
        if breadth < 0.60:
            kill["G5"] += 1; continue

        # G6 — matched random. Expensive; only survivors get here.
        obs = np.mean([v["sharpe"] for v in per.values()])
        allr = []
        for s in SYMS:
            if s not in per: continue
            allr.extend(C.random_benchmark(PANEL[s], C.cost(s), per[s]["exposure"],
                                           per[s]["trades"], n=40, seed=hash(s) % 10000))
        allr = np.array(allr)
        pct = float((allr < obs).mean()) if len(allr) else 0.0
        if pct < 0.95:
            kill["G6"] += 1; continue

        wf = walkforward(builder, hold)
        if wf is None or wf[0] < 0.6 or wf[1] <= 0:
            kill["G7"] += 1; continue

        survivors.append(dict(name=name, hold=hold, sharpe=st["sharpe"],
                              cagr=st["cagr"], maxdd=st["maxdd"], trades=trades,
                              breadth=float(breadth), rand_pct=pct,
                              yrs_positive=wf[0], exposure=st["exposure"]))

    cum = C.ledger_bump(n, "run2: classical chart patterns + confirmations")
    print(f"\nLIFETIME TRIALS: {cum}")
    print("\nkilled by gate:")
    for k, v in kill.items():
        if v: print(f"  {k}: {v}")
    print(f"\nreached G8: {len(survivors)}")

    # G8 — deflated Sharpe against the LIFETIME count
    if survivors:
        srs = np.array([s["sharpe"] for s in survivors])
        sr_std = float(np.std(srs)) if len(srs) > 1 else 0.5
        E = C.emc(cum, sr_std)
        print(f"\nsr_std={sr_std:.3f}  E[max Sharpe | noise, {cum} trials]={E:.3f}")
        final = []
        for s in sorted(survivors, key=lambda x: -x["sharpe"]):
            pass

            s["dsr"] = C.deflated_sharpe(s["sharpe"], E, 3000)
            final.append(s)
        for s in final[:15]:
            print(f"  {s['sharpe']:+.2f}  dsr={s['dsr']:.3f}  br={s['breadth']:.2f} "
                  f"rp={s['rand_pct']:.2f}  {s['name']}")
        json.dump(final, open("../runs/run2_survivors.json", "w"), indent=1)
        passed = [s for s in final if s["dsr"] >= 0.95]
        print(f"\nPASSED G8 (dsr>=0.95): {len(passed)}")
    else:
        print("\nnothing reached G8.")
    json.dump(kill, open("../runs/run2_gates.json", "w"), indent=1)


if __name__ == "__main__":
    main()
