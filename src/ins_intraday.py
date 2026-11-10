"""Doc 223 — insurance short re-tested with INTRADAY stops (IG stops trigger on the day's high), S&P 500 daily OHLC 1962–2026, true-range ATR(20).
Entry: next open after a new all-time closing high. Stop k ATR above entry, checked on the HIGH (gap through -> open); breakeven once the close is
1 ATR below entry; take-profit 5 ATR checked on the LOW (limit order); 60 days max. IG spread + era funding."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hist_study as H
r = pd.read_csv(f"{H.ROOT}/data_hist/SPX_yahoo.csv", index_col=0, parse_dates=True)
r = r[r.index >= "1962-01-02"][["Open", "High", "Low", "Close"]].astype(float); r = r[(r.High > r.Low)]
O, Hh, L, C = r.Open.values, r.High.values, r.Low.values, r.Close.values; IX = r.index; N = len(C)
tr = np.maximum(Hh - L, np.maximum(abs(Hh - np.roll(C, 1)), abs(L - np.roll(C, 1)))); A = pd.Series(tr).rolling(20).mean().values
ath = (r.Close > pd.concat([pd.read_csv(f"{H.ROOT}/data_hist/SPX_yahoo.csv", index_col=0, parse_dates=True).Close[lambda x: x.index < "1962-01-02"], r.Close]).cummax().shift(1).reindex(r.index)).values
def ins(stop=1.0, be=1.0, tp=5.0, maxd=60):
    out = []; i = 0
    while i < N - 2:
        if not ath[i] or not np.isfinite(A[i]): i += 1; continue
        j0 = i + 1; e = O[j0]; st = e + stop * A[i]; tgt = e - tp * A[i] if tp else -1; j = j0; px = None; why = "time"
        while j < N:
            if Hh[j] >= st: px = max(st, O[j]) if j > j0 else st; why = "stop" if st > e + 1e-9 else "breakeven"; break
            if tp and L[j] <= tgt: px = min(tgt, O[j]) if j > j0 else tgt; why = "target"; break
            if be is not None and C[j] <= e - be * A[i]: st = min(st, e)
            if (j - j0) >= maxd: px = C[j]; break
            j += 1
        if px is None: break
        days = (IX[j] - IX[j0]).days; fund = (0.025 - H.rate_at(IX[j0])) / 365 * days * e
        out.append((IX[i], (e - px - H.COST * e * 2 - fund) / A[i], why)); i = j + 1
    return pd.DataFrame(out, columns=["t", "R", "why"])
TOPS = [("1973", "1972-12-01", "1974-06-30"), ("1987", "1987-07-01", "1987-12-31"), ("2000", "2000-01-01", "2001-06-30"), ("2007", "2007-07-01", "2008-12-31"), ("2020", "2020-01-15", "2020-04-30"), ("2022", "2021-11-01", "2022-10-31")]
if __name__ == "__main__":
    for st, be, tp in itertools.product((1.0, 1.5, 2.0, 3.0), (1.0, None), (5.0, 3.0, None)):
        t = ins(st, be, tp); y = t.groupby(t.t.dt.year).R.sum(); tops = " ".join(f"{a}:{t[(t.t >= b) & (t.t <= c)].R.sum():+.0f}" for a, b, c in TOPS)
        print(f"stop {st} ATR, BE {be}, TP {tp}: n{len(t):4d} ({len(t) / 65:.0f}/yr) total {t.R.sum():+6.0f} ATR mean {t.R.mean():+.3f} | worst year {y.min():+5.0f} | since 2001 {t[t.t.dt.year >= 2001].R.sum():+5.0f} | tops {tops} | stops {100 * (t.why == 'stop').mean():.0f}%", flush=True)
