"""
WALK-FORWARD — was the containment switch fitted to the sample it was tested on?

Doc 115 chose the operating rule - containment above its own expanding median,
with no efficiency or ADX confirmation stacked on it - by sweeping thresholds
across the WHOLE five-year panel and picking the best. That is the ordinary
way to fit a parameter and the ordinary way to fool yourself, and today has
already produced two examples: doc 127's blow-off trim was a single lucky cell
in an undrawn grid, and doc 113's Sharpe came from an accounting bug. The
containment threshold has had neither check.

It is the most load-bearing unanswered question about the book that is now
paper trading, so it should be answered before three more months accumulate
on top of it.

TWO SPLITS, because they fail differently:

  IN TIME       fit on 2021-2023, test on 2024-2026. Catches a rule that
                worked in one market regime and was then read as universal.
                This is the harder test: the two halves contain genuinely
                different markets (a collapse, then a recovery).

  ACROSS COINS  fit on a random half of the symbols, test on the other half.
                Catches a rule tuned to the quirks of particular coins rather
                than to a general property of crypto. Repeated over several
                random splits so a single lucky partition cannot carry it.

WHAT "FIT" MEANS HERE. For each candidate threshold the book is run on the
training set only; the threshold with the best total P&L is selected; that
one threshold is then run on the test set and compared against what the
whole-sample winner would have given. If the selected threshold is routinely
the same, and its test performance is close to its training performance, the
rule is a property of the market. If the selection jumps around, or test
performance collapses, it was a curve fit.

The expanding median inside the switch is already causal, so the only thing
being validated here is the CHOICE of threshold, which is the part a human
made.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import clean_portfolio as CP
import regime_detect as RD

STABLE = {"USDTUSD","USDCUSD","DAIUSD","PYUSDUSD","USDSUSD","RLUSDUSD"}
QS = [0.40, 0.50, 0.60, 0.70, 0.80]


def load():
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_15m/*USD.csv")):
        s = os.path.basename(f)[:-4]
        if s in STABLE: continue
        d = pd.read_csv(f, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if len(d) > 60000: out[s] = d
    return out


def episodes_at(prep, syms, q, lo=None, hi=None):
    rows = []
    for s in syms:
        d, D, ema, lob, hib, a = prep[s]
        v = pd.Series(D["contain"])
        allow = (v > v.expanding(500).quantile(q)).values
        dd = d
        if lo is not None or hi is not None:
            m = np.ones(len(d), dtype=bool)
            if lo is not None: m &= (d.index >= lo)
            if hi is not None: m &= (d.index < hi)
            if m.sum() < 3000: continue
            allow = allow & m
        rows += CP.episodes(dd, allow, ema, lob, hib, a, None, "optimistic", "L", s)
        rows += CP.episodes(dd, allow, ema, lob, hib, a, None, "optimistic", "S", s)
    R = pd.DataFrame(rows, columns=["sym","entry","exit","ret","side"])
    return R[np.isfinite(R.ret)]


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} coins.\n")
    prep = {}
    for s, d in data.items():
        D, ema, lob, hib, a = RD.detectors(d)
        prep[s] = (d, D, ema, lob, hib, a)
    syms = sorted(prep)

    SPLIT = pd.Timestamp("2024-01-01", tz="UTC")
    print("="*86)
    print("1. SPLIT IN TIME — fit on 2021-2023, test on 2024-2026")
    print("="*86)
    print(f"  {'threshold':<14}{'TRAIN per ep':>15}{'TRAIN total':>14}"
          f"{'TEST per ep':>14}{'TEST total':>13}")
    best_q, best_tot = None, -1e18
    test_by_q = {}
    for q in QS:
        tr = episodes_at(prep, syms, q, hi=SPLIT)
        te = episodes_at(prep, syms, q, lo=SPLIT)
        if len(tr) < 500 or len(te) < 500: continue
        test_by_q[q] = te
        print(f"  contain>p{int(q*100):<5}{tr.ret.mean()*100:>+14.4f}%"
              f"{tr.ret.sum()*100:>+13.0f}%{te.ret.mean()*100:>+13.4f}%"
              f"{te.ret.sum()*100:>+12.0f}%")
        if tr.ret.sum() > best_tot: best_tot, best_q = tr.ret.sum(), q
    if best_q is not None:
        chosen = test_by_q[best_q]
        best_test = max(test_by_q.items(), key=lambda kv: kv[1].ret.sum())
        print(f"\n  Training picked p{int(best_q*100)}. On the unseen later years it "
              f"earned {chosen.ret.mean()*100:+.4f}% an episode.")
        print(f"  The best threshold IN HINDSIGHT on those years was "
              f"p{int(best_test[0]*100)} at {best_test[1].ret.mean()*100:+.4f}%.")
        gap = chosen.ret.mean()/best_test[1].ret.mean()*100 if best_test[1].ret.mean() else 0
        print(f"  The honest choice captured {gap:.0f}% of the hindsight-best.")

    print("\n" + "="*86)
    print("2. SPLIT ACROSS COINS — fit on half the symbols, test on the rest")
    print("="*86)
    print(f"  {'split':<10}{'picked':<10}{'TRAIN per ep':>15}{'TEST per ep':>14}"
          f"{'hindsight best':>17}{'captured':>11}")
    rng = np.random.default_rng(7)
    caps = []
    for trial in range(5):
        perm = list(rng.permutation(syms))
        half = len(perm)//2
        A, B = perm[:half], perm[half:]
        tr_best, tr_val = None, -1e18
        te_cache = {}
        for q in QS:
            tr = episodes_at(prep, A, q)
            te = episodes_at(prep, B, q)
            if len(tr) < 400 or len(te) < 400: continue
            te_cache[q] = te
            if tr.ret.sum() > tr_val: tr_val, tr_best = tr.ret.sum(), q
        if tr_best is None or not te_cache: continue
        chosen = te_cache[tr_best]
        hb = max(te_cache.items(), key=lambda kv: kv[1].ret.mean())
        cap = chosen.ret.mean()/hb[1].ret.mean()*100 if hb[1].ret.mean() else 0
        caps.append(cap)
        trq = episodes_at(prep, A, tr_best)
        print(f"  {'trial '+str(trial+1):<10}{'p'+str(int(tr_best*100)):<10}"
              f"{trq.ret.mean()*100:>+14.4f}%{chosen.ret.mean()*100:>+13.4f}%"
              f"{'p'+str(int(hb[0]*100))+' '+format(hb[1].ret.mean()*100,'+.4f')+'%':>17}"
              f"{cap:>10.0f}%")
    if caps:
        print(f"\n  Across {len(caps)} random splits the honestly-chosen threshold "
              f"captured a median {np.median(caps):.0f}% of the hindsight-best.")
    print("\n  A rule that is a real property of the market picks the same")
    print("  threshold most of the time and loses little out of sample. One that")
    print("  was curve-fitted jumps around and collapses on unseen data.")
