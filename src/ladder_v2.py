"""
LADDERED ENTRIES, ON A BOOK THAT ACTUALLY WORKS.

DK: "do consider the laddered entries thing again."

Doc 65 left this PARTIAL and the reason was never the ladder. It was tested
three times - pullback entries at -0.134%, Keltner with a prior-low stop at
20.6% win, a 1-ATR stop at 26.7% win - and every base had negative
expectancy. A ladder cannot improve a trade that should not be taken. It was
suspension tuning on a car with no engine.

There is now an engine, and the intraday maker book is the natural home for
it: that book already rests limit orders, so laddering is not a new mechanism,
it is just several bids instead of one.

  single   one resting bid at the bottom of the range           (current)
  ladder3  three bids across the lower third of the range
  ladder5  five bids, same span
  deep     five bids extending BELOW the range low, into the stop zone

Weighting is swept too, because DK's earlier instruction was specific: heavier
toward the extreme, lighter on approach.

  flat     equal size on every rung
  heavy    size increasing toward the lowest rung (DK's version)
  front    size decreasing - the opposite, included so 'heavy' has to beat it

Each rung fills independently when the bar trades strictly through it.
Unfilled rungs are simply never filled - deployment is reported, because a
ladder that only ever fills its top rung is a single entry wearing a disguise.
Judged on the equity curve, not the per-trade mean.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import intraday_maker as IM
import im_portfolio as IP

TF, LOOK, EFF, HOLD = "15min", 24, 0.30, 48
TAKER_EXIT, SLIP = IM.TAKER_EXIT, IM.SLIP
START = 2000.0

WEIGHTS = {
    "flat":  lambda k: np.ones(k),
    "heavy": lambda k: np.arange(1, k+1, dtype=float),
    "front": lambda k: np.arange(k, 0, -1, dtype=float),
}


def rung_prices(lo, hi, a, style):
    """CORRECTED. The first rung is ALWAYS at the range low, because that is
    the signal. Extra rungs go BELOW it, never above. The earlier version put
    the top rung a third of the way up the range, which started trades on
    moves that never reached the extreme - 23,067 trades against the single
    bid's 17,474. That was a different, worse trade selection wearing a
    ladder's clothes, not a laddered version of the same trade."""
    if style == "single":  return np.array([lo])
    if style == "ladder3": return lo - np.array([0.0, 0.25, 0.50])*a
    if style == "ladder4": return lo - np.array([0.0, 0.20, 0.40, 0.60])*a
    if style == "ladder5": return lo - np.array([0.0, 0.15, 0.30, 0.45, 0.60])*a
    if style == "wide4":   return lo - np.array([0.0, 0.35, 0.70, 1.05])*a
    raise ValueError(style)


def signals(data, style, wname, maker_bp=3):
    mk = maker_bp/2/10000
    W = WEIGHTS[wname]
    rows = []
    for s, d in data.items():
        b = IM.bars(d, TF)
        if len(b) < 800: continue
        C, H, L = b.close.values, b.high.values, b.low.values
        n = len(C); a = IM.atr_np(H, L, C)
        hi = pd.Series(H).rolling(LOOK).max().values
        lo = pd.Series(L).rolling(LOOK).min().values
        eff = IM.efficiency(C); last = -10**9
        for i in range(LOOK+120, n-HOLD-2):
            if not (eff[i] < EFF) or i-last < HOLD: continue
            w = hi[i]-lo[i]
            if not np.isfinite(w) or w <= 0 or not np.isfinite(a[i]) or w > 6*a[i]: continue
            px = rung_prices(lo[i], hi[i], a[i], style)
            wt = W(len(px)); wt = wt/wt.sum()
            tgt = (hi[i]+lo[i])/2
            stop = lo[i] - 1.5*a[i]
            filled = []
            first = None
            for q in range(i+1, min(i+1+HOLD, n)):
                for k, p in enumerate(px):
                    if L[q] < p and k not in [f[0] for f in filled]:
                        filled.append((k, p, wt[k]))
                        if first is None: first = q
                if filled and C[q] < stop: break
                if filled and H[q] >= tgt: break
                if not filled and C[q] > hi[i]: break
            if not filled: continue
            last = first
            dep = sum(x for _, _, x in filled)
            e = (sum(p*x for _, p, x in filled)/dep)*(1+mk)
            out = None; qq = first
            for q in range(first+1, min(first+1+HOLD, n)):
                qq = q
                if C[q] < stop: out = ((C[q]*(1-SLIP-TAKER_EXIT))/e-1)*dep; break
                if H[q] >= tgt: out = ((tgt*(1-mk))/e-1)*dep; break
            if out is None:
                qq = min(first+HOLD, n-1); out = ((C[qq]*(1-TAKER_EXIT))/e-1)*dep
            rows.append((s, b.index[first], b.index[qq], out, dep, len(filled)))
    return pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "dep", "rungs"]) \
             .sort_values("entry").reset_index(drop=True)


if __name__ == "__main__":
    data = IM.load_1m()
    print("LADDERED ENTRIES ON THE INTRADAY MAKER RANGE BOOK")
    print(f"{TF} bars, {LOOK}-bar range, eff<{EFF}, maker 3bp, exit at the mid\n")
    print(f"  {'entry':<10}{'weight':<8}{'n':>7}{'deploy':>8}{'rungs':>7}"
          f"{'per trade':>11}{'t':>8}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>8}")
    base = None
    for style in ("single", "ladder3", "ladder4", "ladder5", "wide4"):
        for wname in (["flat"] if style == "single" else ["flat", "heavy", "front"]):
            S = signals(data, style, wname)
            if len(S) < 200: print(f"  {style:<10}{wname:<8}too few"); continue
            r = IP.sim(S, 40, 1)
            if r is None: print(f"  {style:<10}{wname:<8}wiped out"); continue
            t = S.ret.mean()/(S.ret.std(ddof=1)/np.sqrt(len(S)))
            print(f"  {style:<10}{wname:<8}{len(S):>7}{S.dep.mean()*100:>7.0f}%"
                  f"{S.rungs.mean():>7.1f}{S.ret.mean()*100:>+10.4f}%{t:>+8.2f}"
                  f"{r['cagr']*100:>8.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}")
            if style == "single": base = r
    if base:
        print(f"\n  baseline (single bid): CAGR {base['cagr']*100:.1f}%, "
              f"maxDD {base['dd']*100:.1f}%, Sharpe {base['sharpe']:.2f}")
        print("  A ladder earns its place only by beating that on Sharpe, not by")
        print("  looking cleverer. Deployment below 100% means rungs went unfilled,")
        print("  which is smaller size on the same signal - that is a real cost.")
