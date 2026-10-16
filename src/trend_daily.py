"""
TREND FOLLOWING, AT THE TIMEFRAME IT ACTUALLY LIVES ON — and the coin lifecycle.

Two questions, one dataset: 300 crypto products, daily bars, median four
years of history.

WHY THIS EXISTS. decline.py tested a short trend book on 15-MINUTE bars and
lost catastrophically - t = -82, 87% stopped out. The reason was not that
trend-following fails; it was that I built the mirror image of our own
profitable range book. That book buys the lower Keltner band, which is to say
it BUYS breakdowns, and it works. Shorting breakdowns on the same chart is
the losing side of a trade already proven. Short-horizon mean reversion and
long-horizon trend are both real and they do not live on the same timeframe.
So the honest position is not that trend was tested and failed - it is that
it has not been tested yet.

QUESTION 1 — DOES TREND WORK AT DAILY HORIZON, BOTH WAYS?
Classic time-series momentum: hold long while price is above its own moving
average, short while below, rebalanced daily. Swept across lookbacks and run
LONG-ONLY, SHORT-ONLY and BOTH, because the whole point of DK's question is
whether the negative side pays as well as the positive one. Crypto has a
strong upward drift over this sample, so the short side is fighting the tide
and the long side is partly just being long - which is why the comparison
against simply holding the basket is reported alongside, and matters more
than the raw return.

QUESTION 2 — IS THERE A COIN LIFECYCLE WORTH TRADING?
DK: "new coin to coin death trading strategy, capitalising on initial growth,
exiting, the swapping short?" That only works if the arc is real, so every
coin is aligned by its FIRST BAR and the average normalised path measured.
If newly listed coins reliably rise then fade, the shape will show. If the
average path is flat or noisy, the lifecycle idea has no foundation and no
book should be built on it.

Costs: 10bp round trip, charged on every position change. Daily rebalancing
of 300 products is a lot of turnover and the cost line is what usually kills
these books - doc 51 killed VWAP on exactly this.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

COST = 0.0010          # 10bp round trip
STABLE = {"USDT", "USDC", "DAI", "PYUSD", "USDS", "GUSD", "USDTUSD", "USDCUSD"}


def load():
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        s = os.path.basename(f)[:-4]
        if any(s.startswith(x) for x in STABLE): continue
        d = pd.read_csv(f)
        if "t" not in d.columns or len(d) < 400: continue
        d.index = pd.to_datetime(d.t, unit="ms", utc=True)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        out[s] = d[["open", "high", "low", "close", "volume"]].astype(float)
    return out


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} products, daily bars.\n")
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    C = C[C.notna().sum(axis=1) >= 20]
    R = C.pct_change()
    print(f"panel {str(C.index[0])[:10]} -> {str(C.index[-1])[:10]}, "
          f"{len(C):,} days\n")

    print("="*92)
    print("1. TIME-SERIES MOMENTUM ON DAILY BARS — does trend pay, either way?")
    print("="*92)
    print(f"  {'rule':<30}{'side':<8}{'mean/day':>11}{'ann':>9}{'vol':>8}"
          f"{'Sharpe':>8}{'maxDD':>9}{'turnover':>10}")
    bench = R.mean(axis=1)
    bc = (1+bench).cumprod()
    bdd = (bc/bc.cummax()-1).min()
    print(f"  {'hold the basket (benchmark)':<30}{'-':<8}"
          f"{bench.mean()*100:>+10.4f}%{bench.mean()*365*100:>8.0f}%"
          f"{bench.std()*np.sqrt(365)*100:>7.0f}%"
          f"{bench.mean()/bench.std()*np.sqrt(365):>8.2f}{bdd*100:>8.1f}%{'-':>10}")
    for look in (20, 50, 100, 200):
        ma = C.rolling(look).mean()
        raw = np.sign(C - ma).shift(1)          # yesterday's signal, no peeking
        for side, lbl in ((raw.where(raw > 0, 0), "long"),
                          (raw.where(raw < 0, 0), "short"),
                          (raw, "both")):
            w = side.div(side.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
            turn = w.diff().abs().sum(axis=1)
            pnl = (w*R).sum(axis=1) - turn*COST
            pnl = pnl.dropna()
            if len(pnl) < 300 or pnl.std() == 0: continue
            cum = (1+pnl).cumprod()
            dd = (cum/cum.cummax()-1).min()
            print(f"  {'price vs '+str(look)+'d average':<30}{lbl:<8}"
                  f"{pnl.mean()*100:>+10.4f}%{pnl.mean()*365*100:>8.0f}%"
                  f"{pnl.std()*np.sqrt(365)*100:>7.0f}%"
                  f"{pnl.mean()/pnl.std()*np.sqrt(365):>8.2f}{dd*100:>8.1f}%"
                  f"{turn.mean():>10.2f}")
        print()

    print("="*92)
    print("2. THE COIN LIFECYCLE — every product aligned by its first bar")
    print("="*92)
    paths = []
    for s, d in data.items():
        c = d.close.dropna()
        if len(c) < 200: continue
        paths.append(pd.Series((c/c.iloc[0]).values[:1100]))
    P = pd.concat(paths, axis=1)
    print(f"  {len(paths)} products.  Median path, normalised to 1.0 at listing:\n")
    print(f"  {'days since listing':<24}{'median':>10}{'mean':>10}"
          f"{'% above listing':>18}")
    for day in (7, 14, 30, 60, 90, 180, 270, 365, 547, 730, 1095):
        if day >= len(P): continue
        row = P.iloc[day].dropna()
        if len(row) < 20: continue
        print(f"  {'day '+str(day):<24}{row.median():>10.3f}{row.mean():>10.3f}"
              f"{(row>1).mean()*100:>17.0f}%")
    print("\n  If the median rises then falls, the lifecycle arc is real and DK's")
    print("  long-then-short idea has a foundation. If it falls from day one,")
    print("  the 'capitalise on initial growth' half does not exist and only the")
    print("  short side is worth building.")
