"""
CALIBRATION OF THE ENGINE ITSELF.

The challenge this answers: am I rejecting everything because everything fails,
or because my gates are set so harshly that nothing could pass?

The only honest way to settle it is a control experiment with a KNOWN answer.

  POSITIVE CONTROL — synthetic price series with a real, planted edge.
    Returns are generated so that a specific observable condition genuinely
    predicts the next bar. The edge is real by construction. If the engine
    rejects it, the engine is broken and every null result so far is worthless.

  NEGATIVE CONTROL — pure random walk, same volatility, no edge whatsoever.
    If the engine passes anything here, it is too loose.

Three edge sizes are planted, so we also learn HOW SMALL an edge the engine
can still detect. That number is the real answer to "are the gates too harsh".
"""
import numpy as np, pandas as pd
import core as C

N_DAYS = 3000
N_INST = 13
SEED = 20261013


def synth(edge_bp, seed, vol=0.015):
    """
    Build a series where a visible condition predicts the next return.
    Condition: previous bar closed in the upper half of its own range.
    When true, the next day's drift is +edge_bp basis points. That is the
    entire edge — nothing else is planted.
    """
    rng = np.random.default_rng(seed)
    r = np.zeros(N_DAYS)
    cond = np.zeros(N_DAYS, dtype=bool)
    close = np.zeros(N_DAYS); high = np.zeros(N_DAYS); low = np.zeros(N_DAYS)
    close[0] = 100.0; high[0] = 100.5; low[0] = 99.5
    for t in range(1, N_DAYS):
        # symmetric: +edge when the condition holds, -edge when it does not.
        # This makes buy-and-hold flat by construction, so ONLY timing can earn.
        drift = (edge_bp / 10000.0) * (1.0 if cond[t - 1] else -1.0)
        r[t] = rng.normal(drift, vol)
        close[t] = close[t - 1] * (1 + r[t])
        rng_day = abs(rng.normal(0, vol)) * close[t]
        high[t] = close[t] + rng_day * rng.random()
        low[t] = close[t] - rng_day * rng.random()
        pos = (close[t] - low[t]) / max(high[t] - low[t], 1e-9)
        cond[t] = pos > 0.5
    idx = pd.date_range("2010-01-04", periods=N_DAYS, freq="B")
    return pd.DataFrame({"open": close, "high": high, "low": low,
                         "close": close, "volume": 1e6}, index=idx)


def planted_signal(df):
    """The rule that matches the planted edge. Uses only past bars."""
    pos = (df.close - df.low) / (df.high - df.low).replace(0, np.nan)
    return (pos > 0.5).astype(float).fillna(0.0)


def noise_signal(df):
    """A rule with no relationship to anything planted."""
    return (df.close.rolling(7).mean() > df.close.rolling(23).mean()).astype(float)


def run_gates(panel, builder, cost=0.0015, label=""):
    per, series = {}, []
    for k, df in panel.items():
        r, p = C.run_one(df, builder, cost)
        st = C.stats(r, p)
        if st is None:
            continue
        per[k] = st; series.append(r.rename(k))
    if not series:
        return {"verdict": "G1 no data"}
    port = pd.concat(series, axis=1, sort=True).fillna(0.0).mean(axis=1)
    st = C.stats(port, pd.Series(1.0, index=port.index))
    trades = sum(v["trades"] for v in per.values())

    res = {"label": label, "sharpe": st["sharpe"], "cagr": st["cagr"], "trades": trades}
    ev = sum(v["exposure_days"] for v in per.values())
    res["exposure_days"] = ev
    if trades < 50 and ev < 2000:          res["verdict"] = "KILLED G1"; return res
    gr = []
    for k, df in panel.items():
        r, p = C.run_one(df, builder, 0.0); gr.append(r)
    if pd.concat(gr, axis=1).fillna(0).mean(axis=1).mean() <= 0:
        res["verdict"] = "KILLED G2"; return res
    if port.mean() <= 0:                   res["verdict"] = "KILLED G3"; return res
    p2 = []
    for k, df in panel.items():
        r, p = C.run_one(df, builder, cost * 2); p2.append(r)
    if pd.concat(p2, axis=1).fillna(0).mean(axis=1).mean() <= 0:
        res["verdict"] = "KILLED G4"; return res
    breadth = float(np.mean([v["sharpe"] > 0 for v in per.values()]))
    res["breadth"] = breadth
    if breadth < 0.60:                     res["verdict"] = "KILLED G5"; return res
    allr = []
    for k, df in panel.items():
        if k not in per: continue
        allr.extend(C.random_benchmark(df, cost, per[k]["exposure"],
                                       per[k]["trades"], n=40, seed=7))
    allr = np.array(allr)
    obs = float(np.mean([v["sharpe"] for v in per.values()]))
    pct = float((allr < obs).mean()) if len(allr) else 0.0
    res["rand_pct"] = pct
    ok, why = C.timing_gate(per, panel, lambda k: cost, obs, pct)
    res["g6"] = why
    if not ok:                             res["verdict"] = "KILLED G6"; return res
    yearly = port.groupby(port.index.year).apply(lambda x: (1 + x).prod() - 1)
    res["yrs_positive"] = float((yearly > 0).mean())
    if res["yrs_positive"] < 0.6 or yearly.median() <= 0:
        res["verdict"] = "KILLED G7"; return res
    res["verdict"] = "PASSED G1-G7"
    return res


if __name__ == "__main__":
    print("ENGINE CALIBRATION — does the rejection engine detect a real edge?\n")
    print(f"{N_INST} synthetic instruments x {N_DAYS} days each, costs 15bp round trip\n")

    for edge in (0, 5, 10, 20, 40, 80):
        panel = {f"S{i}": synth(edge, SEED + i) for i in range(N_INST)}
        r = run_gates(panel, planted_signal, label=f"planted edge {edge}bp/day")
        tag = "NEGATIVE CONTROL" if edge == 0 else "positive control"
        extra = ""
        if "breadth" in r: extra += f" breadth={r['breadth']:.2f}"
        if "rand_pct" in r: extra += f" randpct={r['rand_pct']:.2f}"
        print(f"  {edge:3d}bp  Sharpe {r['sharpe']:+6.2f}  trades {r['trades']:6d}  "
              f"{r['verdict']:14s}{extra}   [{tag}]")

    print("\n  control: an unrelated rule on the 40bp series (should be killed)")
    panel = {f"S{i}": synth(40, SEED + i) for i in range(N_INST)}
    r = run_gates(panel, noise_signal, label="unrelated rule")
    print(f"         Sharpe {r['sharpe']:+6.2f}  trades {r['trades']:6d}  {r['verdict']}")

    print("\n  control: the planted rule on PURE NOISE (should be killed)")
    panel = {f"S{i}": synth(0, SEED + 500 + i) for i in range(N_INST)}
    r = run_gates(panel, planted_signal, label="planted rule, no edge present")
    print(f"         Sharpe {r['sharpe']:+6.2f}  trades {r['trades']:6d}  {r['verdict']}")
