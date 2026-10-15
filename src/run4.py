"""
RUN 4 — measured, not thresholded.

The previous runs killed candidates against conventions I chose: 2x costs,
60% breadth, 95th percentile vs random. Those are inherited numbers, not
derived ones, and the engine calibration showed they produce false negatives
(a real 20bp/day edge, Sharpe +1.18, died at the 2x cost gate).

This run keeps only the gates whose answer is genuinely binary:
    H1  does it make money GROSS            (if not, there is nothing to cost)
    H2  does it make money NET at base cost
    H3  does the TIMING beat doing nothing  (exposure-matched buy & hold,
                                             or matched-random at low exposure)

Everything else is REPORTED AS A MEASURED VALUE, not used to kill:
    breakeven_cost   the round-trip cost at which expectancy hits zero.
                     Replaces "survives 2x costs" with a number you can
                     compare against what you would actually pay.
    breadth          positive on N of 13 instruments
    rand_pct         percentile against matched-random entry
    yrs_positive     fraction of calendar years positive

Covers all three spaces in one pass: indicators, chart patterns, and pairwise
combinations of both. Trial ledger continues cumulatively.
"""
import json, itertools, time, numpy as np, pandas as pd
import core as C
from generate import candidates, pattern_candidates

SYMS = C.universe()
PANEL = {s: C.load(s) for s in SYMS}
RET = {s: PANEL[s].close.pct_change().fillna(0.0) for s in SYMS}


def measure(builder, hold):
    """One candidate -> measured panel record, or None if unusable."""
    per, series, gross, turns = {}, [], [], []
    for s in SYMS:
        try:
            pos = builder(PANEL[s]).fillna(0.0)
        except Exception:
            return None
        if hold:
            pos = pos.rolling(hold, min_periods=1).max()
        pos = pos.shift(1).fillna(0.0)
        if pos.abs().sum() == 0:
            continue
        ret = RET[s]
        turn = pos.diff().abs().fillna(pos.abs())
        g = (pos * ret)
        r = g - turn * C.cost(s)
        st = C.stats(r, pos)
        if st is None:
            continue
        per[s] = st
        series.append(r.rename(s))
        gross.append(g.rename(s))
        turns.append(turn.rename(s))
    if len(series) < len(SYMS) * 0.7:
        return None

    port = pd.concat(series, axis=1, sort=True).fillna(0.0).mean(axis=1)
    gport = pd.concat(gross, axis=1, sort=True).fillna(0.0).mean(axis=1)
    tport = pd.concat(turns, axis=1, sort=True).fillna(0.0).mean(axis=1)
    st = C.stats(port, pd.Series(1.0, index=port.index))
    if st is None:
        return None

    # breakeven cost: gross expectancy / turnover. A measured number.
    be = float(gport.mean() / tport.mean()) if tport.mean() > 0 else np.inf

    exp = float(np.mean([v["exposure"] for v in per.values()]))
    obs = float(np.mean([v["sharpe"] for v in per.values()]))
    bh = float(np.mean([C.buyhold_benchmark(PANEL[k], C.cost(k), per[k]["exposure"])
                        for k in per]))

    rand_pct = np.nan
    if exp < 0.5:                      # only informative at low exposure
        allr = []
        for s in list(per)[:6]:        # subsample instruments for speed
            allr.extend(C.random_benchmark(PANEL[s], C.cost(s), per[s]["exposure"],
                                           per[s]["trades"], n=25, seed=hash(s) % 9999))
        if allr:
            rand_pct = float((np.array(allr) < obs).mean())

    yearly = port.groupby(port.index.year).apply(lambda x: (1 + x).prod() - 1)

    return dict(
        sharpe=st["sharpe"], cagr=st["cagr"], maxdd=st["maxdd"],
        gross_mean=float(gport.mean()), net_mean=float(port.mean()),
        breakeven_cost=be, exposure=exp,
        breadth_n=int(sum(1 for v in per.values() if v["sharpe"] > 0)),
        breadth_of=len(per),
        buyhold_sharpe=bh, timing_delta=obs - bh,
        rand_pct=rand_pct,
        yrs_positive=float((yearly > 0).mean()), n_years=len(yearly),
        exposure_days=float(sum(v["exposure_days"] for v in per.values())),
    )


def hard_gates(m):
    """Only the three binary questions. Returns (passed, reason)."""
    if m["exposure_days"] < 2000:
        return False, "H0 insufficient exposure"
    if m["gross_mean"] <= 0:
        return False, "H1 loses money gross"
    if m["net_mean"] <= 0:
        return False, "H2 loses money after costs"
    if m["exposure"] >= 0.5:
        if m["timing_delta"] <= 0:
            return False, "H3 timing adds nothing over buy&hold"
    else:
        if not (m["rand_pct"] == m["rand_pct"]) or m["rand_pct"] < 0.50:
            return False, "H3 no better than random entry"
    return True, "PASS"


def main():
    space = []
    for nm, b, h in candidates():
        space.append(("indicator", nm, b, h))
    for nm, b, h in pattern_candidates():
        space.append(("pattern", nm, b, h))

    # standalone level candidates
    import levels as LV
    from generate import FILTERS
    for lname, (fn, params) in LV.LEVELS.items():
        for p in params:
            for fname, ffn in FILTERS.items():
                for h in (None, 10, 20):
                    def mk(fn=fn, p=p, ffn=ffn):
                        return lambda df: fn(df, *p) * ffn(df)
                    space.append(("level",
                                  f"{lname}({','.join(map(str,p))})|{fname}|hold={h}",
                                  mk(), h))

    # pairwise combinations, built from the combine.py base set
    import combine as CB
    CB.BASE = CB.BASE + [
        ("brk_mo_hi",  lambda df: LV.l_break_prior_month_high(df)),
        ("brk_qt_hi",  lambda df: LV.l_break_prior_quarter_high(df)),
        ("ath",        lambda df: LV.l_at_all_time_high(df, 0.02)),
        ("swingbrk",   lambda df: LV.l_swing_break(df, 20)),
        ("topofyear",  lambda df: LV.l_dist_from_year_high(df, 0.95)),
        ("roundnum",   lambda df: LV.l_round_number(df, 0.005)),
    ]
    pairs = list(itertools.combinations(range(len(CB.BASE)), 2))
    for (i, j) in pairs:
        (na, fa), (nb, fb) = CB.BASE[i], CB.BASE[j]
        for mode in ("AND", "OR"):
            if mode == "AND":
                bb = (lambda df, fa=fa, fb=fb: fa(df) * fb(df))
            else:
                bb = (lambda df, fa=fa, fb=fb: ((fa(df) + fb(df)) > 0).astype(float))
            space.append(("combo", f"{na} {mode} {nb}", bb, 10))

    n = len(space)
    print(f"RUN 4 — {n} candidates "
          f"({sum(1 for x in space if x[0]=='indicator')} indicator, "
          f"{sum(1 for x in space if x[0]=='pattern')} pattern, "
          f"{sum(1 for x in space if x[0]=='level')} level, "
          f"{sum(1 for x in space if x[0]=='combo')} combination)\n", flush=True)

    reasons, passed, rows = {}, [], []
    t0 = time.time()
    for k, (kind, nm, b, h) in enumerate(space):
        if k and k % 400 == 0:
            print(f"  ...{k}/{n} ({time.time()-t0:.0f}s) passed={len(passed)}", flush=True)
        m = measure(b, h)
        if m is None:
            reasons["H0 unusable"] = reasons.get("H0 unusable", 0) + 1
            continue
        m["kind"], m["name"], m["hold"] = kind, nm, h
        ok, why = hard_gates(m)
        reasons[why] = reasons.get(why, 0) + 1
        rows.append(m)
        if ok:
            passed.append(m)

    cum = C.ledger_bump(n, "run4: measured scheme — indicators + patterns + pairwise combos")
    print(f"\nLIFETIME TRIALS: {cum}")
    print("\noutcome of every candidate:")
    for r, v in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {r}")

    print(f"\nPASSED the three hard gates: {len(passed)}")
    if passed:
        passed.sort(key=lambda x: -x["sharpe"])
        print("\n  top by Sharpe — breakeven cost is the number that replaces "
              "'survives 2x costs':")
        print(f"  {'Sharpe':>7} {'CAGR':>8} {'maxDD':>8} {'breakeven':>10} "
              f"{'breadth':>8} {'vs B&H':>7} {'yrs+':>5}  name")
        for m in passed[:25]:
            print(f"  {m['sharpe']:+7.2f} {m['cagr']*100:+7.2f}% {m['maxdd']*100:7.1f}% "
                  f"{m['breakeven_cost']*10000:9.1f}bp "
                  f"{m['breadth_n']:3d}/{m['breadth_of']:<4d} "
                  f"{m['timing_delta']:+6.2f} {m['yrs_positive']:5.2f}  {m['name'][:48]}")

        # deflated Sharpe on the best, against the lifetime count
        srs = np.array([m["sharpe"] for m in rows])
        E = C.emc(cum, float(srs.std()))
        best = passed[0]
        dsr = C.deflated_sharpe(best["sharpe"], E, 4000)
        print(f"\n  sr_std across all {len(rows)} measured = {srs.std():.3f}")
        print(f"  E[max Sharpe | noise, {cum} lifetime trials] = {E:.3f}")
        print(f"  best candidate Sharpe {best['sharpe']:.3f} -> deflated Sharpe {dsr:.4f}")

    json.dump({"passed": passed[:80], "reasons": reasons, "lifetime": cum,
               "n_measured": len(rows)},
              open("../runs/run4.json", "w"), indent=1, default=str)
    pd.DataFrame(rows).to_csv("../runs/run4_all_measured.csv", index=False)
    print("\nwrote ../runs/run4_all_measured.csv (every candidate, every measure)")


if __name__ == "__main__":
    main()
