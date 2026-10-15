"""
TIME SERIES MOMENTUM — Moskowitz, Ooi & Pedersen (Quantpedia #0118).

WHY THIS ONE, OUT OF EVERYTHING THE SWEEP FOUND
It closes three gaps at once:
  1. DIVERSIFICATION. Five of our six books are long-biased crypto mean
     reversion. This is trend, the opposite sign, and it is two-sided.
  2. CROSS-SECTION. Our cross-sectional factor book died twice — first on
     survivorship (98% of the 2024 shorts were coins being delisted), then as
     a plain null on live panels, because 33 perps and 129 equities are too
     narrow for rank dispersion to mean anything. TSMOM is TIME-SERIES: each
     instrument is judged against its own history, so panel width does not bite.
  3. POSITION SIZING. We have none. TSMOM's native rule — size inversely to
     ex-ante volatility — IS volatility targeting, and Quantpedia's own
     backtest of inverse-vol weighting moved a 60/40 from Sharpe 0.79 to 1.02
     and halved max drawdown.

THE PAPER
20.7% p.a., vol 15.74%, max DD -33.87%, Sharpe 1.31, 1965-2009, 58 instruments
across four asset classes, monthly. Costs EXCLUDED — so the headline is an
upper bound. Robustness is unusually good: it holds at every lookback up to 12
months, holds within each asset class separately, and scores Sharpe 1.1 in a
1966-1985 sample that predates publication.

THE HAIRCUT, APPLIED IN ADVANCE
Quantpedia's own replication of 355 strategies found Sharpe decays 33% on the
mean and 44% on the median out of sample. So a paper 1.31 is a realistic
expectation of 0.7-0.9 BEFORE our costs. Anything we measure near or below that
is consistent with the strategy being real; anything far above it should make
us suspicious of our own build, not pleased.

THE RULE
  signal   sign of the trailing 12-month return, per instrument
  size     inversely proportional to trailing realised volatility, so every
           instrument contributes equal risk rather than equal notional
  rebal    monthly
  costs    charged on turnover at each rebalance

WHAT IS MEASURED
  - the paper's own lookback sweep (1, 3, 6, 9, 12 months), because a result
    that only works at 12 is a fitted cell and the paper says it should not be
  - equal-notional vs inverse-vol, to isolate how much the SIZING contributes
  - per asset class separately, as the paper does
  - by year, and the whole equity curve with drawdown
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

PANELS = {
    "us_equities": "/home/claude/qlab/data_wide/*.csv",
    "etf_macro": "/home/claude/qlab/data_vol/*.csv",
    "crypto_daily": "/home/claude/qlab/data/*.csv",
}
COST_BP = 10.0 / 10000      # per unit of turnover, each way


def load_panel(pattern):
    px = {}
    for p in sorted(glob.glob(pattern)):
        s = os.path.basename(p)[:-4]
        try:
            d = pd.read_csv(p)
        except Exception:
            continue
        col = "date" if "date" in d.columns else None
        if col is None:
            continue
        d[col] = pd.to_datetime(d[col], errors="coerce")
        d = d.dropna(subset=[col]).set_index(col).sort_index()
        d = d[~d.index.duplicated()]
        if len(d) < 400 or "close" not in d.columns or d.close.le(0).any():
            continue
        px[s] = d.close
    return pd.DataFrame(px).sort_index()


def tsmom(P, lookback_m=12, vol_window=60, inverse_vol=True, target_vol=0.15):
    """Monthly-rebalanced time-series momentum. Returns a daily return series."""
    R = P.pct_change()
    # month ends present in the data
    me = P.resample("ME").last().index
    me = [d for d in me if d in P.index or True]
    lb = int(lookback_m * 21)
    rows, prev_w = [], pd.Series(dtype=float)
    dates = P.index
    for i, d in enumerate(P.resample("ME").last().index[:-1]):
        pos = dates.searchsorted(d)
        if pos < lb + vol_window or pos >= len(dates) - 1:
            continue
        hist = P.iloc[pos - lb:pos + 1]
        sig = np.sign(hist.iloc[-1] / hist.iloc[0] - 1)
        vol = R.iloc[pos - vol_window:pos + 1].std() * np.sqrt(252)
        ok = sig.notna() & vol.notna() & (vol > 0)
        if ok.sum() < 5:
            continue
        if inverse_vol:
            w = sig[ok] * (target_vol / vol[ok])
        else:
            w = sig[ok]
        w = w / np.abs(w).sum()                 # unit gross exposure
        nxt = dates.searchsorted(P.resample("ME").last().index[i + 1])
        seg = R.iloc[pos + 1:nxt + 1][w.index].fillna(0)
        if not len(seg):
            continue
        turn = float((w - prev_w.reindex(w.index).fillna(0)).abs().sum())
        gross = (seg * w).sum(axis=1)
        gross.iloc[0] -= turn * COST_BP
        rows.append(gross)
        prev_w = w
    if not rows:
        return pd.Series(dtype=float)
    return pd.concat(rows).sort_index()


def stats(r, label):
    if len(r) < 100:
        print(f"  {label:<28} too few"); return None
    ann = r.mean() * 252
    vol = r.std() * np.sqrt(252)
    sh = ann / vol if vol > 0 else np.nan
    cum = (1 + r).cumprod()
    dd = (cum / np.maximum.accumulate(cum) - 1).min()
    print(f"  {label:<28}{ann*100:>8.2f}%{vol*100:>8.2f}%{sh:>8.2f}"
          f"{dd*100:>9.1f}%{(cum.iloc[-1]-1)*100:>10.1f}%")
    return sh


if __name__ == "__main__":
    print("TIME SERIES MOMENTUM — paper Sharpe 1.31, expect 0.7-0.9 after the")
    print("33-44% out-of-sample haircut Quantpedia measured on 355 strategies.\n")
    for name, pat in PANELS.items():
        P = load_panel(pat)
        if P.shape[1] < 5 or len(P) < 600:
            print(f"{name}: only {P.shape[1]} instruments / {len(P)} days — skipped\n")
            continue
        print("=" * 78)
        print(f"  {name.upper()}   {P.shape[1]} instruments   "
              f"{P.index[0].date()} -> {P.index[-1].date()}")
        print("=" * 78)
        print(f"  {'variant':<28}{'CAGR':>8}{'vol':>8}{'Sharpe':>8}{'maxDD':>9}{'cum':>10}")
        best = None
        for lb in (1, 3, 6, 9, 12):
            s = stats(tsmom(P, lb, inverse_vol=True), f"inverse-vol, {lb}m lookback")
        print()
        for lb in (3, 12):
            stats(tsmom(P, lb, inverse_vol=False), f"equal-notional, {lb}m")
        print()
