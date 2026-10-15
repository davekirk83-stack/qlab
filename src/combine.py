"""
Run 3 — COMBINATION.

Runs 1 and 2 tested each rule in isolation (crossed with filters and exits).
This tests what they never did: signals combined WITH EACH OTHER.

Three combination modes, which are genuinely different things:

  A. CONFLUENCE (AND)  — both signals must agree to take the trade.
                         Fewer, higher-conviction entries.
  B. EITHER (OR)       — either signal triggers. More entries, more diversification
                         of timing within one instrument.
  C. PORTFOLIO BLEND   — hold several strategies simultaneously, equal weight.
                         This is the important one: the returns stream is averaged,
                         so uncorrelated-but-marginal signals can produce a portfolio
                         Sharpe that no single component has. Diversification is the
                         only free lunch here, and runs 1-2 could not see it at all.

Same gates. Same lifetime ledger. Nothing gets special treatment for being a combination.
"""
import json, itertools, time, numpy as np, pandas as pd
import core as C
from generate import FAMILIES, FILTERS

SYMS = C.universe()
PANEL = {s: C.load(s) for s in SYMS}

# A diverse base set: one representative per family, spanning trend / reversion /
# volatility / seasonality / structure. Chosen for mechanism diversity, BEFORE
# seeing any results, so this is not selection on outcome.
BASE = [
    ("tsmom60",   lambda df: C.s_tsmom(df, 60)),
    ("tsmom120",  lambda df: C.s_tsmom(df, 120)),
    ("tsmom250",  lambda df: C.s_tsmom(df, 250)),
    ("tsmomsk",   lambda df: C.s_tsmom_skip(df, 250, 21)),
    ("ema20_100", lambda df: C.s_ema(df, 20, 100)),
    ("ema50_200", lambda df: C.s_ema(df, 50, 200)),
    ("donch20",   lambda df: C.s_donchian(df, 20)),
    ("donch55",   lambda df: C.s_donchian(df, 55)),
    ("z20_1.5",   lambda df: C.s_zscore(df, 20, 1.5)),
    ("z50_2",     lambda df: C.s_zscore(df, 50, 2.0)),
    ("rsi2_10",   lambda df: C.s_rsi(df, 2, 10)),
    ("rsi14_30",  lambda df: C.s_rsi(df, 14, 30)),
    ("volbrk20",  lambda df: C.s_volbreak(df, 20, 1.0)),
    ("tom",       lambda df: C.s_tom(df, 28, 3)),
    ("accel",     lambda df: C.s_accel(df, 20, 250)),
    ("lowvol",    lambda df: C.s_lowvol(df, 60, 0.5)),
    ("rangep50",  lambda df: C.s_range_pos(df, 50, 0.8)),
    ("trend200",  lambda df: C.f_trend200(df)),
]

# Patterns join the SAME base set, so every pair below includes
# pattern x indicator crosses (e.g. "flag AND tsmom60"), pattern x pattern,
# and indicator x indicator. No category is privileged.
import patterns as P
BASE += [
    ("flag",      lambda df: P.p_flag(df, 2.0, 10, 5, 0.5)),
    ("pennant",   lambda df: P.p_pennant(df, 2.0, 10, 8)),
    ("dblbottom", lambda df: P.p_double_bottom(df, 40, 0.03)),
    ("invhs",     lambda df: P.p_head_shoulders_inv(df, 60)),
    ("tlbreak",   lambda df: P.p_trendline_break(df, 50)),
    ("sretest",   lambda df: P.p_support_retest(df, 50, 0.02)),
    ("engulf",    lambda df: P.p_engulfing(df)),
    ("pinbar",    lambda df: P.p_pinbar(df, 2.0)),
    ("insidebrk", lambda df: P.p_inside_break(df)),
]


def panel_series(builder, hold, cost_mult=1.0):
    per, series = {}, []
    for s in SYMS:
        try:
            r, pos = C.run_one(PANEL[s], builder, C.cost(s) * cost_mult, hold=hold)
        except Exception:
            return None, None
        st = C.stats(r, pos)
        if st is None:
            continue
        per[s] = st
        series.append(r.rename(s))
    if len(series) < len(SYMS) * 0.7:
        return None, None
    return pd.concat(series, axis=1, sort=True).fillna(0.0).mean(axis=1), per


def gates(port, per, builder, hold, label, kill):
    """Returns a survivor dict, or None, recording which gate killed it."""
    st = C.stats(port, pd.Series(1.0, index=port.index))
    trades = sum(v["trades"] for v in per.values())
    if st is None or trades < 200:
        kill["G1"] += 1; return None
    g, _ = panel_series(builder, hold, 0.0)
    if g is None or g.mean() <= 0:
        kill["G2"] += 1; return None
    if port.mean() <= 0:
        kill["G3"] += 1; return None
    p2, _ = panel_series(builder, hold, 2.0)
    if p2 is None or p2.mean() <= 0:
        kill["G4"] += 1; return None
    breadth = float(np.mean([v["sharpe"] > 0 for v in per.values()]))
    if breadth < 0.60:
        kill["G5"] += 1; return None
    allr = []
    for s in SYMS:
        if s not in per: continue
        allr.extend(C.random_benchmark(PANEL[s], C.cost(s), per[s]["exposure"],
                                       per[s]["trades"], n=40, seed=hash(s) % 10000))
    allr = np.array(allr)
    obs = float(np.mean([v["sharpe"] for v in per.values()]))
    pct = float((allr < obs).mean()) if len(allr) else 0.0
    if pct < 0.95:
        kill["G6"] += 1; return None
    yearly = port.groupby(port.index.year).apply(lambda x: (1 + x).prod() - 1)
    if (yearly > 0).mean() < 0.6 or yearly.median() <= 0:
        kill["G7"] += 1; return None
    return dict(name=label, hold=hold, sharpe=st["sharpe"], cagr=st["cagr"],
                maxdd=st["maxdd"], trades=trades, breadth=breadth, rand_pct=pct,
                yrs_positive=float((yearly > 0).mean()))


def main():
    kill = {f"G{i}": 0 for i in range(1, 10)}
    survivors = []
    n_trials = 0
    t0 = time.time()

    # ---------------- A + B: pairwise AND / OR ----------------
    pairs = list(itertools.combinations(range(len(BASE)), 2))
    print(f"A/B: {len(pairs)} pairs x 2 modes x 2 exits = {len(pairs)*4} trials")
    for (i, j) in pairs:
        (na, fa), (nb, fb) = BASE[i], BASE[j]
        for mode in ("AND", "OR"):
            for hold in (10, 20):
                n_trials += 1
                if mode == "AND":
                    b = (lambda df, fa=fa, fb=fb: fa(df) * fb(df))
                else:
                    b = (lambda df, fa=fa, fb=fb: ((fa(df) + fb(df)) > 0).astype(float))
                port, per = panel_series(b, hold)
                if port is None:
                    kill["G1"] += 1; continue
                s = gates(port, per, b, hold, f"{na} {mode} {nb}|hold={hold}", kill)
                if s: survivors.append(s)
        if (pairs.index((i, j)) + 1) % 40 == 0:
            print(f"  ...{pairs.index((i,j))+1}/{len(pairs)} pairs ({time.time()-t0:.0f}s) alive={len(survivors)}")

    # ---------------- C: portfolio blends ----------------
    # Build each base signal's panel return stream once, then blend.
    print("\nC: portfolio blends")
    streams = {}
    for name, fn in BASE:
        p, _ = panel_series(fn, None)
        if p is not None:
            streams[name] = p
    S = pd.concat(streams, axis=1, sort=True).fillna(0.0)
    print(f"  {len(streams)} component streams")

    corr = S.corr()
    print("  mean pairwise correlation: %.3f" % (
        corr.values[np.triu_indices_from(corr.values, 1)].mean()))

    blends = []
    # equal-weight blend of all
    blends.append(("blend_all", list(streams)))
    # blends by mechanism group
    groups = {
        "trend":   ["tsmom60","tsmom120","tsmom250","tsmomsk","ema20_100","ema50_200","accel"],
        "breakout":["donch20","donch55","volbrk20","rangep50"],
        "revert":  ["z20_1.5","z50_2","rsi2_10","rsi14_30"],
        "other":   ["tom","lowvol","trend200"],
        "pattern": ["flag","pennant","dblbottom","invhs","tlbreak","sretest",
                    "engulf","pinbar","insidebrk"],
    }
    for g, members in groups.items():
        m = [x for x in members if x in streams]
        if len(m) > 1: blends.append((f"blend_{g}", m))
    # one-per-group diversified blend
    blends.append(("blend_diverse", [g[0] for g in
                   [[x for x in v if x in streams] for v in groups.values()] if g]))
    # all random size-k subsets, k=3..6, capped
    rng = np.random.default_rng(11)
    names = list(streams)
    for k in (3, 4, 5, 6):
        for _ in range(60):
            m = list(rng.choice(names, size=k, replace=False))
            blends.append((f"blend_k{k}_" + "+".join(sorted(m)), m))

    print(f"  {len(blends)} blends")
    blend_results = []
    for label, members in blends:
        n_trials += 1
        port = S[members].mean(axis=1)
        st = C.stats(port, pd.Series(1.0, index=port.index))
        if st is None:
            kill["G1"] += 1; continue
        if port.mean() <= 0:
            kill["G3"] += 1; continue
        yearly = port.groupby(port.index.year).apply(lambda x: (1 + x).prod() - 1)
        blend_results.append(dict(name=label, k=len(members), sharpe=st["sharpe"],
                                  cagr=st["cagr"], maxdd=st["maxdd"],
                                  yrs_positive=float((yearly > 0).mean()),
                                  members=members))

    blend_results.sort(key=lambda x: -x["sharpe"])
    print("\n  top blends by Sharpe:")
    for b in blend_results[:10]:
        print(f"    {b['sharpe']:+.2f}  CAGR {b['cagr']*100:+6.2f}%  DD {b['maxdd']*100:6.1f}%  "
              f"yrs+ {b['yrs_positive']:.2f}  {b['name'][:60]}")

    # best single component, for comparison — the question that matters is
    # whether the blend beats its own best part.
    singles = []
    for name, p in streams.items():
        st = C.stats(p, pd.Series(1.0, index=p.index))
        if st: singles.append((name, st["sharpe"], st["cagr"], st["maxdd"]))
    singles.sort(key=lambda x: -x[1])
    print("\n  best single components:")
    for s in singles[:6]:
        print(f"    {s[1]:+.2f}  CAGR {s[2]*100:+6.2f}%  DD {s[3]*100:6.1f}%  {s[0]}")

    cum = C.ledger_bump(n_trials, "run3: combination — pairwise AND/OR + portfolio blends")
    print(f"\nLIFETIME TRIALS: {cum}")
    print("killed by gate (pairwise):", {k: v for k, v in kill.items() if v})
    print(f"pairwise survivors reaching G8: {len(survivors)}")

    if blend_results:
        srs = np.array([b["sharpe"] for b in blend_results])
        E = C.emc(cum, float(srs.std()))
        best = blend_results[0]
        dsr = C.deflated_sharpe(best["sharpe"], E, len(S))
        print(f"\nbest blend Sharpe {best['sharpe']:+.3f} vs best single {singles[0][1]:+.3f}")
        print(f"E[max Sharpe | noise, {cum} trials] = {E:.3f}")
        print(f"DEFLATED SHARPE of best blend = {dsr:.4f}  (gate: >= 0.95)")

    json.dump({"blends": blend_results[:40], "singles": singles,
               "pairwise_survivors": survivors, "gates": kill,
               "lifetime_trials": cum},
              open("../runs/run3_combination.json", "w"), indent=1)


if __name__ == "__main__":
    main()
