"""DK 27 Nov 22:40: "What do other traders scan for?" - the best-known published scans, built as their sources give them, on US stocks
(data_stocks, current S&P 500, 2005-26 daily, cost 0.10%/side). Entry at the signal close. Split by market regime (S&P above / below its
200-day), because S3 (doc 280) has no edge in calm uptrends - a scan that works THERE would complement it.
  SB4   Stockbee 4% breakout ("momentum burst"): close/prev close >= 1.04, volume > prev volume, volume >= 100k, close > 3.
        Stockbee holds momentum bursts 3-5 days -> exits: hold 3 days, hold 5 days.
  EP    Stockbee / Qullamaggie episodic pivot: up > 4% (Qullamaggie 5%) on volume > 3x the 50-day average, opening gap >= 2%, close > 3,
        50-day avg volume > 300k. Position trade -> exits: stop at the signal day's low, else hold 20 / 60 days.
  MTT   Minervini trend template + new 52-week high (breakout): close > 50 > 150 > 200-day; 200-day rising over 1 month; close >= 1.3x
        52-week low and within 25% of the 52-week high (here: a new 52-week closing high). Exits: hold 20 days; or trail - first close
        under the 50-day.
  NR7   Crabel narrow range 7 (compression -> expansion; AuclairsDad's coil idea on daily bars): today's range is the narrowest of 7 days,
        in an uptrend (above 50 & 200-day); buy a break of the NR7 high next day, stop at the NR7 low, exit at day 5 close."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import cross_asset_s3 as X
COST = 0.001

def scan(x, spxdn):
    D = x.rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "c", "Volume": "v"})[["o", "h", "l", "c", "v"]].astype(float).dropna()
    D = D[D.c > 0]; c, o, h, l, v = (D[k].values for k in "cohlv"); n = len(D)
    if n < 300: return []
    av50 = D.v.rolling(50).mean().shift(1).values; m50 = D.c.rolling(50).mean().values; m150 = D.c.rolling(150).mean().values; m200 = D.c.rolling(200).mean().values
    m200_1m = pd.Series(m200).shift(21).values; hi252 = D.c.rolling(252).max().shift(1).values; lo252 = D.c.rolling(252).min().values
    rng = h - l; nr7 = (pd.Series(rng).rolling(7).min().values == rng)
    reg = spxdn.reindex(D.index).ffill().fillna(False).values; out = []
    def ret(e, x_): return x_ * (1 - COST) / (e * (1 + COST)) - 1
    for i in range(252, n - 61):
        c1 = c[i - 1]
        if c1 <= 0: continue
        R = "S&P<200d" if reg[i] else "S&P>200d"
        if c[i] / c1 >= 1.04 and v[i] > v[i - 1] and v[i] >= 1e5 and c[i] > 3:
            out.append(("SB4 hold 3d", R, D.index[i], ret(c[i], c[i + 3]))); out.append(("SB4 hold 5d", R, D.index[i], ret(c[i], c[i + 5])))
        if c[i] / c1 > 1.04 and np.isfinite(av50[i]) and v[i] > 3 * av50[i] and av50[i] > 3e5 and o[i] >= c1 * 1.02 and c[i] > 3:
            for hold in (20, 60):
                st = l[i]; px = c[i + hold]
                for k in range(i + 1, i + hold + 1):
                    if l[k] <= st: px = min(o[k], st); break
                out.append((f"EP stop day-low, hold {hold}d", R, D.index[i], ret(c[i], px)))
        if (np.isfinite(m200_1m[i]) and c[i] > m50[i] > m150[i] > m200[i] and m200[i] > m200_1m[i] and c[i] >= 1.3 * lo252[i] and c[i] > hi252[i] and c1 <= hi252[i]):
            out.append(("MTT 52w-high breakout, hold 20d", R, D.index[i], ret(c[i], c[i + 20])))
            px = c[min(n - 1, i + 60)]
            for k in range(i + 1, min(n, i + 61)):
                if c[k] < m50[k]: px = c[k]; break
            out.append(("MTT 52w-high breakout, exit close < 50d (60d max)", R, D.index[i], ret(c[i], px)))
        if nr7[i] and c[i] > m50[i] and c[i] > m200[i] and h[i + 1] > h[i]:
            e = max(o[i + 1], h[i]); st = l[i]; px = c[i + 5]
            for k in range(i + 1, i + 6):
                if l[k] <= st and not (k == i + 1 and o[k] > st and l[k] <= st and False): px = min(o[k], st) if k > i + 1 else st; break
            out.append(("NR7 uptrend, buy break, stop NR7 low, 5d", R, D.index[i + 1], ret(e, px)))
    return out

if __name__ == "__main__":
    U = X.load(); spx = X.prep(U[("indices", "SPX")]); SPXDN = spx.c < spx.c.rolling(200).mean()
    tt = []
    for f in glob.glob("data_stocks/*.csv.gz"):
        if f.endswith(".L.csv.gz"): continue
        x = pd.read_csv(f, parse_dates=["Date"], index_col="Date"); tt += scan(x, SPXDN)
    T = pd.DataFrame(tt, columns=["scan", "regime", "t", "r"]); T["t"] = pd.to_datetime(T.t); T = T.sort_values("t")
    rows = []
    for (sc, rg), g in list(T.groupby(["scan", "regime"])) + [((sc, "all"), g) for sc, g in T.groupby("scan")]:
        r = 100 * g.r; h = len(r) // 2; d = g.groupby(g.t.dt.normalize()).r.mean() * 100; mo = g.groupby(g.t.dt.to_period("M")).r.mean()
        tstat = mo.mean() / (mo.std() / np.sqrt(len(mo))) if len(mo) > 2 else np.nan
        rows.append(dict(scan=sc, regime=rg, n=len(r), per_yr=round(len(r) / 21.8), win=round((r > 0).mean(), 3), mean=round(r.mean(), 3), h1=round(r[:h].mean(), 3), h2=round(r[h:].mean(), 3),
                         per_day=round(d.mean(), 3), month_t=round(tstat, 1), worst=round(r.min(), 1)))
    R = pd.DataFrame(rows).sort_values(["scan", "regime"]); R.to_csv("runs/research/trader_scans.csv", index=False)
    pd.set_option("display.width", 250); print(R.to_string(index=False))
