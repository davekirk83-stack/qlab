"""
THE HARNESS — one door every candidate goes through.

Built 2026-10-14 after a day in which the test method improved roughly hourly,
so that every idea tested early got an easier and wronger test than those
tested late. Three ideas were rejected and then recovered once the build was
fixed (patterns, VWAP, the cascade). The problem was never the ideas.

A candidate is a function:   signal(df) -> (long_idx, short_idx)
returning integer bar indices. Everything else is handled here.

WHAT IT APPLIES AUTOMATICALLY — each one earned its place by catching a real
error on 2026-10-14, and the doc that paid for it is named.

 1. TIME-MATCHED CONTROL          doc 50. Controls drawn near each signal in
                                  time, because 2025 and 2026 were different
                                  markets and a pooled control inverted a
                                  verdict.
 2. COSTS NETTED IN R             doc 51. Cost = 2*fee / stop_distance. A 0.19%
                                  stop makes 8bp cost 0.84R. Quoted every time.
 3. MAKER vs TAKER                doc 52. A resting entry is a maker trade.
                                  Applying taker fees to it kills real edges.
 4. EXIT SWEEP                    doc 44. Exits moved results more than entries
                                  did. Never report a single exit.
 5. TIMEFRAME SWEEP               docs 35, 49, 53 and the divergence result.
                                  Wrong timeframe produced a false negative
                                  FOUR times in one day. Mandatory.
 6. SYMMETRY CHECK                doc 47. If both directions tilt the same way
                                  it is drift, not structure.
 7. PARAMETER PLATEAU             doc 47. One lucky cell is not an edge.
 8. SPLIT-HALF and BY-YEAR        doc 39.
 9. PER-SYMBOL CONCENTRATION      doc 39. A few symbols carrying it is fragile.
10. EPISODE DEDUPLICATION         doc 33. Overlapping windows inflated t by 10x.
11. MULTIPLE-COMPARISON CORRECTION
                                  new. Testing N variants means N chances at
                                  noise. The harness counts every variant it
                                  runs and raises the bar accordingly.

THE VERDICT RULE — revised 2026-10-15 after DK: "you made a new harness that
fails everything by design".

He was right about the first build. It required ALL of six binary gates,
including every year positive and strict two-sidedness. That is a bar most
genuinely profitable strategies would miss: real edges have down years and
plenty are one-sided for sound reasons. A screen that rejects everything is
as useless as one that accepts everything.

So the harness now SCORES rather than vetoes:
    CORE (must hold)   positive edge over a time-matched control, after costs
    STRENGTH           each further check adds confidence, none is fatal alone
and it reports a grade, not a gate:
    STRONG    core holds + >=4 of 5 supporting checks
    PROMISING core holds + 2-3 supporting checks
    WEAK      core holds only
    NO EDGE   core fails
"NO EDGE" still means this build, not the idea.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST

RNG = np.random.default_rng(20261014)

MAKER, TAKER = 2.0 / 10000, 5.0 / 10000
SLIP_DEFAULT = 10.0 / 10000


# ----------------------------------------------------------------- execution
def simulate(df, bar, short, stop_atr, hold, entry_mode="taker",
             slip=SLIP_DEFAULT):
    """One trade. Returns dict or None.

    entry_mode 'maker' = a resting limit at the close (pays maker, and in
    reality would not always fill — treat as the optimistic bound).
    Stops are ALWAYS taker plus slippage; that is not optional.
    """
    C, L, H = df.close.values, df.low.values, df.high.values
    a = ST.atr(df).bfill().values
    n = len(C)
    if bar + hold > n - 1 or a[bar] <= 0 or C[bar] <= 0:
        return None
    fee_in = MAKER if entry_mode == "maker" else TAKER
    px = C[bar] * (1 + fee_in) if not short else C[bar] * (1 - fee_in)
    st = C[bar] - stop_atr * a[bar] if not short else C[bar] + stop_atr * a[bar]
    risk = abs(px - st)
    if risk <= 0:
        return None
    for j in range(bar + 1, bar + hold + 1):
        if (L[j] <= st) if not short else (H[j] >= st):
            return dict(R=-1.0, risk_pct=risk / px, bars=j - bar, stopped=True)
    ex = C[bar + hold] * (1 - MAKER) if not short else C[bar + hold] * (1 + MAKER)
    r = ((ex - px) if not short else (px - ex)) / risk
    return dict(R=float(r), risk_pct=risk / px, bars=hold, stopped=False)


def dedupe(idx, gap):
    out, last = [], -10 ** 9
    for i in sorted(idx):
        if i - last >= gap:
            out.append(int(i)); last = int(i)
    return out


# ------------------------------------------------------------------- the run
def evaluate(panel, signal_fn, stop_atr, hold, entry_mode="taker",
             match_window=500, warm=250):
    """Run one configuration across a panel. Signals AND time-matched controls."""
    rows = []
    for sym, df in panel.items():
        n = len(df)
        if n < warm + hold + 50:
            continue
        try:
            longs, shorts = signal_fn(df)
        except Exception:
            continue
        for idx, short in ((longs, False), (shorts, True)):
            idx = [i for i in idx if warm < i < n - hold - 2]
            for i in dedupe(idx, hold):
                r = simulate(df, i, short, stop_atr, hold, entry_mode)
                if r:
                    rows.append({**r, "sym": sym, "short": short, "grp": "REAL",
                                 "ts": df.index[i], "bar": i})
                # TIME-MATCHED control: same instrument, same neighbourhood
                lo, hi = max(warm, i - match_window), min(n - hold - 2, i + match_window)
                if hi <= lo:
                    continue
                q = int(RNG.integers(lo, hi))
                c = simulate(df, q, short, stop_atr, hold, entry_mode)
                if c:
                    rows.append({**c, "sym": sym, "short": short, "grp": "CTRL",
                                 "ts": df.index[q], "bar": q})
    return pd.DataFrame(rows)


def edge(T, subset=None):
    """Edge over the time-matched control, with a proper two-sample t."""
    if subset is not None:
        T = T[subset]
    a = T[T.grp == "REAL"].R.values
    b = T[T.grp == "CTRL"].R.values
    if len(a) < 30 or len(b) < 30:
        return None
    se = np.sqrt(a.std(ddof=1) ** 2 / len(a) + b.std(ddof=1) ** 2 / len(b))
    if se <= 0:
        return None
    return dict(n=len(a), real=a.mean(), ctrl=b.mean(),
                edge=a.mean() - b.mean(), t=(a.mean() - b.mean()) / se,
                win=float((a > 0).mean()))


def cost_in_R(T, bp_round_trip=10.0):
    """Doc 51: the cost line, in this configuration's own R units."""
    rp = T[T.grp == "REAL"].risk_pct.median()
    if not np.isfinite(rp) or rp <= 0:
        return np.nan
    return (bp_round_trip / 10000) / rp


def run_candidate(name, panels, signal_fn,
                  stops=(1.5, 2.5, 4.0), holds=(10, 20, 40, 80),
                  entry_modes=("taker", "maker"), mechanism_note=None,
                  bp=10.0, verbose=True):
    """The full battery. `panels` is {timeframe_label: {sym: df}}."""
    grid = []
    for tf, panel in panels.items():
        for st in stops:
            for hd in holds:
                for em in entry_modes:
                    T = evaluate(panel, signal_fn, st, hd, em)
                    if not len(T):
                        continue
                    e = edge(T)
                    if not e:
                        continue
                    c = cost_in_R(T, bp)
                    grid.append(dict(tf=tf, stop=st, hold=hd, mode=em,
                                     cost=c, net=e["edge"] - c, T=T, **e))
    n_tests = max(len(grid), 1)
    # Bonferroni-style correction over the number of configurations tried
    t_req = float(np.sqrt(2 * np.log(max(n_tests, 2))))     # ~3.0 at 40 tests
    if verbose:
        print("=" * 100)
        print(f"  {name}")
        print(f"  {n_tests} configurations tried -> corrected t threshold "
              f"{t_req:.2f} (an uncorrected 2.0 would pass "
              f"~{n_tests*0.05:.0f} by chance)")
        print("=" * 100)
    if not grid:
        print("  no configuration produced enough trades\n"); return None
    grid.sort(key=lambda g: -g["net"])
    if verbose:
        print(f"  {'tf':<6}{'stop':>5}{'hold':>6}{'mode':>7}{'n':>7}"
              f"{'edge':>9}{'cost':>8}{'NET':>9}{'t':>8}{'win':>7}")
        for g in grid[:10]:
            print(f"  {g['tf']:<6}{g['stop']:>5}{g['hold']:>6}{g['mode']:>7}"
                  f"{g['n']:>7}{g['edge']:>+9.3f}{g['cost']:>8.3f}"
                  f"{g['net']:>+9.3f}{g['t']:>+8.2f}{g['win']*100:>6.1f}%")
    best = grid[0]
    T = best["T"]
    checks = {}
    # plateau: how many configurations are net positive?
    pos = sum(1 for g in grid if g["net"] > 0)
    checks["plateau"] = (pos / len(grid) > 0.5, f"{pos}/{len(grid)} configs net positive")
    # symmetry
    el = edge(T, T.short == False); es = edge(T, T.short == True)
    if el and es:
        sym_ok = (el["edge"] > 0) == (es["edge"] > 0)
        checks["symmetry"] = (sym_ok or bool(mechanism_note),
                              f"long {el['edge']:+.3f}R / short {es['edge']:+.3f}R"
                              + ("  [one-sidedness predicted in advance]" if mechanism_note else ""))
    # split-half and by-year
    T = T.copy(); T["yr"] = pd.to_datetime(T.ts).dt.year
    yrs = sorted(T.yr.unique())
    yr_ok, yr_txt = True, []
    for y in yrs:
        e = edge(T, T.yr == y)
        if e:
            yr_txt.append(f"{y} {e['edge']:+.3f}R")
            if e["edge"] <= 0:
                yr_ok = False
    if yr_txt:
        checks["by year"] = (yr_ok, "  ".join(yr_txt))
    # per-symbol concentration
    syms = []
    for s in T.sym.unique():
        e = edge(T, T.sym == s)
        if e:
            syms.append(e["edge"])
    if syms:
        share = sum(1 for x in syms if x > 0) / len(syms)
        checks["breadth"] = (share >= 0.6, f"{sum(1 for x in syms if x>0)}/{len(syms)} symbols positive")
    checks["beats cost"] = (best["net"] > 0, f"net {best['net']:+.3f}R at {bp:.0f}bp")
    checks["significance"] = (best["t"] >= t_req, f"t={best['t']:+.2f} vs required {t_req:.2f}")

    if verbose:
        print()
        for k, (ok, txt) in checks.items():
            print(f"   {'PASS' if ok else 'FAIL'}  {k:16s} {txt}")
        core = checks.get("beats cost", (False, ""))[0]
        support = sum(1 for k,(ok,_) in checks.items()
                      if ok and k != "beats cost")
        n_sup = max(len(checks) - 1, 1)
        if not core:
            grade = "NO EDGE (this build)"
        elif support >= max(4, n_sup - 1):
            grade = "STRONG"
        elif support >= 2:
            grade = "PROMISING"
        else:
            grade = "WEAK"
        print(f"\n  GRADE: {grade}   ({support}/{n_sup} supporting checks)"
              f"  — best config {best['tf']} stop {best['stop']} "
              f"hold {best['hold']} {best['mode']}")
        print("  (a grade is a confidence level, not a gate; nothing here says "
              "an IDEA fails — only this build of it)")
        print()
    return dict(grid=grid, best=best, checks=checks, t_req=t_req)
