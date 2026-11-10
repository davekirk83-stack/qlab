"""Doc 219 — single-share books on IG spread-bet costs (DK 10:55–10:57: new areas of profit; tailor to our known costs).
Data: data_stocks/ (S&P 500 + FTSE 100 current constituents, 2005–; survivorship bias favours longs). Execution: decided at the close,
traded at the next open, in AND out (review2_fixes.run_o); stop on every bar. Costs: IG share spread bets — about 0.1% spread on large
caps; charged as 0.1% PER SIDE (double, as the buffer) + funding 6%/yr x 1.4. Rules fixed in advance from the literature:
  S1 Connors (2009) stock RSI(2): above 200-day, RSI(2) < 5 -> exit close above the 5-day average (10 days max), stop 3 ATR
  S2 our index RSI(4) dip on shares: above 200-day, RSI(4) < 25 -> exit RSI(4) > 55, 10 days, stop 3 ATR
  S3 short-term reversal (Lehmann 1990 / Jegadeesh 1990): each day the 5 S&P 500 shares above their 200-day with the WORST 5-day return -> hold 5 days
  S4 earnings-gap drift (PEAD proxy): open >= 5% above the prior close on >= 2x normal volume -> buy next open, hold 20 days, stop 3 ATR
  S5 gap-down rebound: open >= 5% below the prior close on >= 2x volume, above the 200-day -> buy next open, hold 5 days, stop 3 ATR"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, review2_fixes as RF, standard_test as S, std_books as B
U = pd.read_csv("data_stocks/universe.csv"); IDX = dict(zip(U.ticker, U["index"]))
SH = []
for f in sorted(glob.glob("data_stocks/*.csv.gz")):
    k = os.path.basename(f)[:-7]; d = pd.read_csv(f, index_col=0, parse_dates=True); d.columns = [c.lower() for c in d.columns]
    d = d[["open", "high", "low", "close", "volume"]].astype(float).dropna(); d = d[(d.close > 0) & (d.open > 0)]
    if len(d) < 400: continue
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs())); d["atr"] = tr.rolling(20).mean()
    F.D[k] = d; F.COST[k] = 0.001; SH.append(k)
US = [k for k in SH if IDX.get(k) == "SP500"]; UK = [k for k in SH if IDX.get(k) == "FTSE100"]
up = lambda d: d.close > d.close.rolling(200).mean(); ma = lambda c, n: c.rolling(n).mean()
def mk(rows): return pd.DataFrame(rows, columns=["t", "R", "m"])
def per_stock(sig, exit_=None, maxd=10, stop=3.0, mkts=None):
    def b(cm=1.0, rnd=None):
        rows = []
        for k in (mkts or SH):
            d = F.D[k]; e = sig(d).fillna(False); x = exit_(d) if exit_ else None; old = F.COST[k]; F.COST[k] = old * cm
            try: rows += [(t, R, k) for t, R in RF.run_o(k, (rnd or (lambda k, e: e))(k, e), x, maxd, stop)]
            finally: F.COST[k] = old
        return mk(rows)
    return b
def s3(cm=1.0, rnd=None):
    px = pd.DataFrame({k: F.D[k].close for k in US}); r5 = px / px.shift(5) - 1; abv = px > px.rolling(200).mean()
    rk = r5.where(abv).rank(axis=1, method="first"); pick = rk <= 5
    return per_stock(lambda d: pick[d.name].reindex(d.index).fillna(False) if hasattr(d, "name") else None, None, 5, 3.0, US)(cm, rnd) if False else \
        mk([(t, R, k) for k in US for t, R in _s3one(k, pick[k], cm, rnd)])
def _s3one(k, e, cm, rnd):
    old = F.COST[k]; F.COST[k] = old * cm
    try: return RF.run_o(k, (rnd or (lambda k, e: e))(k, e.reindex(F.D[k].index).fillna(False)), None, 5, 3.0)
    finally: F.COST[k] = old
vol2 = lambda d: d.volume > 2 * d.volume.rolling(20).mean().shift(1)
BOOKS = {
    "S1 Connors stock RSI(2)<5 above 200-day, exit > 5-day avg": ("stock-dip", per_stock(lambda d: up(d) & (F.rsi(d.close, 2) < 5), lambda d: d.close > ma(d.close, 5), 10, 3.0)),
    "S2 our RSI(4) dip on shares": ("stock-dip", per_stock(lambda d: up(d) & (F.rsi(d.close, 4) < 25), lambda d: F.rsi(d.close, 4) > 55, 10, 3.0)),
    "S3 short-term reversal: 5 worst 5-day S&P shares above 200-day, 5 days": ("stock-reversal", s3),
    "S4 earnings-gap drift: gap up >= 5% on 2x volume, hold 20 days": ("stock-event", per_stock(lambda d: (d.open / d.close.shift(1) - 1 >= 0.05) & vol2(d), None, 20, 3.0)),
    "S5 gap-down rebound: gap down >= 5% on 2x volume above 200-day, 5 days": ("stock-event", per_stock(lambda d: (d.open / d.close.shift(1) - 1 <= -0.05) & vol2(d) & up(d).shift(1), None, 5, 3.0)),
}
if __name__ == "__main__":
    print(f"{len(US)} US + {len(UK)} UK shares loaded; costs 0.1% per side + funding")
    C = B.core()
    for nm, (fam, b) in BOOKS.items():
        o, t = S.judge(nm, fam, ["shares"], b, core=C, random_runs=20)
        print("      by index:", " ".join(f"{g}:{x.R.mean():+.3f}(n{len(x)})" for g, x in t.groupby(t.m.map(IDX))), flush=True)
