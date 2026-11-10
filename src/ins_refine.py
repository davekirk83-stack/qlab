"""Doc 223 — DK 11:47 refinements of the insurance short: enter at the CLOSE of the new all-time-high day; once it has dropped back, stop to
breakeven; then take-profit levels. S&P 500 daily 1928–2026 (hist_study: IG spread, era funding; stops/targets checked on closes).
Variants fixed in advance (all reported — choose for robustness, not the single best): breakeven trigger after a drop of 0.5 / 1 ATR;
take-profit at 2 / 3 / 5 ATR or none; time exit 20 / 60 days."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hist_study as H, top_short as T
C, A, IX, N = H.C, H.A, H.IX, H.N
ath = (H.d.close > H.d.close.cummax().shift(1)).values
def ins(be=1.0, tp=None, maxd=20, stop=1.0, at_close=True):
    out = []; i = 0
    while i < N - 2:
        if not ath[i] or not np.isfinite(A[i]): i += 1; continue
        j0 = i if at_close else i + 1; e = C[j0]; st = e + stop * A[i]; j = j0 + 1; px = None; why = "time"
        while j < N:
            if C[j] >= st: px = C[j]; why = "stop" if st > e else "breakeven"; break
            if tp and C[j] <= e - tp * A[i]: px = C[j]; why = "target"; break
            if be is not None and C[j] <= e - be * A[i]: st = min(st, e)
            if (j - j0) >= maxd: px = C[j]; break
            j += 1
        if px is None: break
        days = (IX[j] - IX[j0]).days; fund = (0.025 - H.rate_at(IX[j0])) / 365 * days * e
        out.append((IX[i], (e - px - H.COST * e * 2 - fund) / A[i], why)); i = j
    return pd.DataFrame(out, columns=["t", "R", "why"])
def show(nm, t):
    y = t.groupby(t.t.dt.year).R.sum(); tops = " ".join(f"{a}:{t[(t.t >= b) & (t.t <= c)].R.sum():+.0f}" for a, b, c in T.TOPS if a in ("1929", "1987", "2000", "2007", "2020", "2022"))
    mix = t.why.value_counts(normalize=True); mx = " ".join(f"{k} {100 * v:.0f}%" for k, v in mix.items())
    print(f"{nm:44s} n{len(t):4d} mean {t.R.mean():+.3f} total {t.R.sum():+6.0f} ATR | worst year {y.min():+5.0f} | since 2001 {t[t.t.dt.year >= 2001].R.sum():+5.0f} | tops {tops} | exits: {mx}", flush=True)
    return t.R.sum()
if __name__ == "__main__":
    show("baseline: next close, stop 1 ATR, 20 days", ins(None, None, 20, 1.0, False))
    show("at the ATH close, stop 1 ATR, 20 days", ins(None, None, 20))
    res = {}
    for be, tp, md in itertools.product((0.5, 1.0), (None, 2.0, 3.0, 5.0), (20, 60)):
        res[(be, tp, md)] = show(f"close entry, BE after {be} ATR, TP {tp}, {md} days", ins(be, tp, md))
    pos = sum(v > 0 for v in res.values()); print(f"\n{pos}/{len(res)} variants positive overall; best {max(res, key=res.get)} {max(res.values()):+.0f}, worst {min(res, key=res.get)} {min(res.values()):+.0f}")
