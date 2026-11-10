"""Doc 224 addendum — 'toxic order flow' (DK 15:58–15:59). A VPIN-style toxicity score from Binance BTC taker flow (delta = taker buy − taker
sell volume), on 15-min bars: TOX = |sum delta| / sum volume over the last 12 bars (3 hours) — how one-sided the aggressive flow is (0 = balanced,
1 = all one way); SIGN = sum delta / sum volume (− = sellers); TOX rank = percentile vs the previous 30 days; COOLING = TOX lower than 3 bars ago.
Applied to every tap of a LONG liquidation level (doc 224 rebuild): does 'toxic and still accelerating' vs 'toxic but cooling' vs 'calm' change the bounce?"""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import liq_levels_test as LT
m = pd.read_parquet("data_long/btc_1m.parquet")
q = m.resample("15min").agg({"vol": "sum", "delta": "sum"}).reindex(LT.d.index).fillna(0)
sd, sv = q.delta.rolling(12).sum(), q.vol.rolling(12).sum()
TOX = (sd.abs() / sv).values; SIGN = (sd / sv).values
RANK = pd.Series(TOX).rolling(2880, min_periods=500).rank(pct=True).values      # vs the previous 30 days of 15-min bars
COOL = TOX < np.roll(TOX, 3)
lv = LT.levels("long"); rows = []
for start, lvl, lev in lv:
    seg = np.nonzero(LT.L[start:] <= lvl)[0]
    if not len(seg): continue
    j = start + seg[0]
    if j >= LT.N - 100 or not np.isfinite(RANK[j]): continue
    r4 = (LT.C[j + 16] / lvl - 1) * 100 - 0.04; r24 = (LT.C[j + 96] / lvl - 1) * 100 - 0.04; r1 = (LT.C[j + 4] / lvl - 1) * 100 - 0.04
    rows.append((LT.IX[j], lev, RANK[j], SIGN[j], bool(COOL[j]), r1, r4, r24))
t = pd.DataFrame(rows, columns=["t", "lev", "rank", "sign", "cool", "h1", "h4", "h24"]).drop_duplicates(subset=["t"])
def show(nm, g):
    if len(g) < 20: print(f"   {nm:52s} n{len(g)}"); return
    tt = g.h4.mean() / g.h4.std() * np.sqrt(len(g))
    print(f"   {nm:52s} n{len(g):5d} | 1h {g.h1.mean():+.3f}% | 4h {g.h4.mean():+.3f}% (t {tt:+.2f}, win {100 * (g.h4 > 0).mean():.0f}%) | 24h {g.h24.mean():+.3f}%")
if __name__ == "__main__":
    print("Taps of LONG liquidation levels, by order-flow toxicity at the tap (one event per 15-min bar):")
    show("all taps", t)
    tox = (t["rank"] >= 0.8) & (t.sign < 0)
    show("TOXIC (top 20% of 30 days, sellers) and still ACCELERATING", t[tox & ~t.cool])
    show("TOXIC (sellers) but COOLING  <- 'cooling after a burst'", t[tox & t.cool])
    show("moderate (rank 40-80%)", t[t["rank"].between(0.4, 0.8)])
    show("CALM (bottom 40%)", t[t["rank"] < 0.4])
    for half, g in (("2020-22", t[t.t.dt.year <= 2022]), ("2023-26", t[t.t.dt.year >= 2023])):
        gt = (g["rank"] >= 0.8) & (g.sign < 0)
        show(f"{half}: toxic+cooling", g[gt & g.cool]); show(f"{half}: toxic+accelerating", g[gt & ~g.cool])
