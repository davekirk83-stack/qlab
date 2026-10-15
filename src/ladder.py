"""
INCREMENTAL FILL WEIGHTING — size up as price approaches the thesis-break.

DK, 2026-10-15:
  "The better traders establish the stop loss at a point where their thesis or
   plan for the trade breaks down, and they weight their fill sizes
   incrementally as the price action approaches the fill limit / stop loss."

TWO CLAIMS. THE FIRST IS ALREADY SATISFIED.
Cascade v3's stop is 0.05% under the cascade low — a structural, thesis-break
stop, not a distance. The retest book's stop sits just under the broken level,
same logic. Both already obey the first half.

THE SECOND IS NEW, AND IS NOT THE LADDER THAT WAS VOIDED.
Doc 53 tested a ladder of bids DOWN INTO the flush and it was voided as
knife-catching: the position got largest in the cascades that never bounced,
because nothing bounded how far down it kept buying. DK's correction then was
"wait until the cascade had finished and raised up a bit, held a little, then
start filling bids", which produced v3.

What he describes NOW is bounded on both ends. The ladder sits between the
first bid and the STOP, and the stop is where the thesis dies. You cannot
keep averaging down, because below the stop there is no position. So the
failure mode of doc 53 is structurally absent.

THE REAL TRADE-OFF, which is why this needs measuring and not arguing
  in favour   the average fill is closer to the stop, so risk per unit is
              smaller and every winner pays a larger multiple of it
  against     you reach FULL size exactly in the trades that go on to stop
              out, and only partial size in the ones that bounce immediately
              — which are the best trades
These pull hard in opposite directions. Nothing about the idea tells you which
wins; only the data does.

MEASUREMENT
Every variant is scored on return over the SAME intended notional, so a
half-filled trade earns half. Otherwise a ladder that rarely fills would look
good by simply not trading. Also reported: capital actually deployed, and
return on deployed capital, because those answer different questions.

  single        the registered rule: one bid at 0.4% below, full size
  flat_3/flat_5 equal size across 3 or 5 rungs, first bid to just above the stop
  incr_3/incr_5 INCREASING size toward the stop — DK's rule (weights 1:2:3)
  front_3       DECREASING size toward the stop, the opposite, as a control.
                If incr beats single but front also beats single, the gain is
                from laddering per se and not from the weighting.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
DROP, WIN = 0.03, 5
LIFT, HOLD, DEPTHB, TP, MAXH = 0.008, 10, 0.004, 0.015, 60
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000


def find_base(C, L, i, n, mw=60):
    lo = L[i]; k = i
    while k < min(i + mw, n - 1):
        if L[k] < lo: lo = L[k]
        if C[k] >= lo * (1 + LIFT): break
        k += 1
    if k >= min(i + mw, n - 1) or C[k] < lo * (1 + LIFT): return None
    j = k; h = 0
    while j < min(k + mw, n - 1):
        if L[j] < lo: return None
        h += 1
        if h >= HOLD: return j, lo
        j += 1
    return None


def rungs(top, stop, k, weights):
    """k bid prices from `top` down to just above `stop`, with weights."""
    if k == 1:
        return [top], [1.0]
    lowest = stop * 1.0005                      # never rest at or below the stop
    if lowest >= top:
        return [top], [1.0]
    px = list(np.linspace(top, lowest, k))
    w = np.array(weights, dtype=float)[:k]
    return px, list(w / w.sum())


VARIANTS = {
    "single (registered)": (1, [1]),
    "flat 3":              (3, [1, 1, 1]),
    "flat 5":              (5, [1, 1, 1, 1, 1]),
    "incr 3 (1:2:3)":      (3, [1, 2, 3]),
    "incr 5":              (5, [1, 2, 3, 4, 5]),
    "front 3 (3:2:1)":     (3, [3, 2, 1]),
}


def play(C, H, L, j, lo, n, k, weights):
    """Returns (ret_on_intended, ret_on_deployed, deployed, stopped)."""
    top = max(C[j] * (1 - DEPTHB), lo * 1.0010)
    stop = lo * (1 - 0.0005)
    px_list, w_list = rungs(top, stop, k, weights)
    filled = []                                  # (price, weight)
    exit_q = None
    for q in range(j + 1, min(j + 1 + MAXH, n)):
        for p, w in zip(px_list, w_list):
            if L[q] <= p and not any(abs(p - fp) < 1e-12 for fp, _ in filled):
                filled.append((p, w))
        if not filled:
            continue
        dep = sum(w for _, w in filled)
        avg = sum(p * w for p, w in filled) / dep
        entry = avg * (1 + MAKER)
        if L[q] <= stop:
            exit_q = (stop * (1 - SLIP - TAKER)) / entry - 1, dep, True
            break
        if H[q] >= entry * (1 + TP):
            exit_q = (entry * (1 + TP) * (1 - MAKER)) / entry - 1, dep, False
            break
    if not filled:
        return 0.0, np.nan, 0.0, False
    if exit_q is None:
        dep = sum(w for _, w in filled)
        avg = sum(p * w for p, w in filled) / dep
        entry = avg * (1 + MAKER)
        q = min(j + MAXH, n - 1)
        r = (C[q] * (1 - MAKER)) / entry - 1
        exit_q = (r, dep, False)
    r, dep, stopped = exit_q
    return r * dep, r, dep, stopped


def run():
    rows = []
    for f in sorted(glob.glob(f"{M1}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        if len(d) < 50000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); i = WIN
        while i < n - 2 * MAXH:
            if C[i] / C[i - WIN] - 1 > -DROP: i += 1; continue
            b = find_base(C, L, i, n)
            if b is None: i += WIN; continue
            j, lo = b
            rec = {"sym": s}
            for name, (k, w) in VARIANTS.items():
                ri, rd, dep, st = play(C, H, L, j, lo, n, k, w)
                rec[name] = ri
                rec[name + "|dep"] = dep
                rec[name + "|rd"] = rd
            rows.append(rec)
            i = j + MAXH
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("INCREMENTAL FILL WEIGHTING — cascade v3, same signals, paired\n")
    T = run()
    print(f"  {len(T)} base-and-bid setups, {T.sym.nunique()} symbols\n")
    print(f"  {'variant':<22}{'mean/intended':>15}{'t':>8}{'win':>8}"
          f"{'deployed':>11}{'on deployed':>13}{'vs single':>12}")
    base = T["single (registered)"].values
    for name in VARIANTS:
        v = T[name].values
        se = v.std(ddof=1) / np.sqrt(len(v))
        dep = T[name + "|dep"].values
        rd = T[name + "|rd"].values; rd = rd[np.isfinite(rd)]
        d = v - base
        sed = d.std(ddof=1) / np.sqrt(len(d))
        vs = "   —" if name.startswith("single") else \
             f"{d.mean()*100:>+8.3f}pp t{d.mean()/sed:+.2f}"
        print(f"  {name:<22}{v.mean()*100:>+14.3f}%{v.mean()/se:>+8.2f}"
              f"{(v>0).mean()*100:>7.1f}%{dep.mean()*100:>10.1f}%"
              f"{rd.mean()*100:>+12.3f}%{vs:>12}")
    print("\n  'mean/intended' charges unfilled size as zero return, so a variant")
    print("  cannot win by simply trading less. 'on deployed' is the fill quality.")
