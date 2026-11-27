"""Creation round, step 2 (DK 27 Nov 22:18: "Use screening to find set ups to trade across all asset classes"). The best combination from
creation_combos.py - S3: Connors RSI(2) < 10 pullback, taken only in DK v2's context (deep flush >= 15% off the 20-day high, OR uptrend:
close above the 50- and 200-day), buy the close, sell the first close above the 5-day mean (10-day limit) - and S4 (same, but a resting
maker bid next day 0.5 daily-sigma under the signal close) - run across every daily history we hold:
  US stocks 501 (data_stocks, 2005-26; current S&P 500 members -> survivorship bias, read with care), UK stocks 100 (FTSE 100, .L),
  21 macro markets (data_daily: SPX NDX DJI RUT DAX FTSE N225, gold silver copper oil natgas, EURUSD GBPUSD AUDUSD USDJPY USDCAD, TNOTE, BTC ETH),
  10 coins (Binance 15m -> daily, 2021-26).
Costs per side: stocks / indices / commodities 0.10% (CFD/ETF spread + commission, conservative), FX 0.02%, crypto 0.14%.
Also the classic Connors filter (above 200-day only) for comparison, so we can see what v2's context adds."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FX = {"EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCAD"}

def prep(D):
    D = D[["o", "h", "l", "c"]].astype(float).dropna(); D = D[D.c > 0]
    D["sig"] = D.c.pct_change().rolling(14).std().shift(1)
    m50, m200 = D.c.rolling(50).mean(), D.c.rolling(200, min_periods=150).mean()
    D["up"] = (D.c > m50) & (D.c > m200); D["up200"] = D.c > m200
    D["deep"] = D.c <= D.h.rolling(20).max() * 0.85; D["ctx"] = D.up | D.deep
    dd = D.c.diff(); u = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    D["rsi2"] = 100 - 100 / (1 + u / dn.replace(0, np.nan)); D["ma5"] = D.c.rolling(5).mean()
    return D

def trades(D, cost, filt="ctx", maker=False, rsi=10):
    c, l, ma5, r2, sig, F = D.c.values, D.l.values, D.ma5.values, D.rsi2.values, D.sig.values, D[filt].values
    out = []; i = 210; n = len(D)
    while i < n - 2:
        if r2[i] < rsi and F[i] and np.isfinite(sig[i]):
            if maker:
                bid = c[i] * (1 - 0.5 * sig[i])
                if l[i + 1] >= bid: i += 1; continue
                e, j0, ce = bid, i + 1, 0.0
            else: e, j0, ce = c[i], i, cost
            j = j0 + 1
            while j < min(n - 1, j0 + 10) and c[j] <= ma5[j]: j += 1
            out.append((D.index[j0], c[j] * (1 - cost) / (e * (1 + ce)) - 1, j - j0)); i = j
        i += 1
    return out

def load():
    U = {}
    for f in glob.glob("data_stocks/*.csv.gz"):
        s = os.path.basename(f)[:-7]; x = pd.read_csv(f, parse_dates=["Date"], index_col="Date")
        U[("UK stocks" if s.endswith(".L") else "US stocks", s)] = x.rename(columns={"Open": "o", "High": "h", "Low": "l", "Close": "c"})
    for f in glob.glob("data_daily/*.csv"):
        s = os.path.basename(f)[:-4]
        if s in ("FEDFUNDS", "VIX", "BTC", "ETH"): continue
        x = pd.read_csv(f, index_col=0); x.index = pd.to_datetime(x.index, utc=True).tz_localize(None).normalize()
        cls = "FX" if s in FX else ("commodities" if s in ("GOLD", "SILVER", "COPPER", "OIL", "NATGAS") else ("bonds" if s == "TNOTE" else "indices"))
        U[(cls, s)] = x.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"})
    import dk_v2_all_charts as A
    for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT"):
        d = A.coin(s); U[("crypto", s)] = pd.DataFrame({"o": d.open.resample("1D").first(), "h": d.high.resample("1D").max(), "l": d.low.resample("1D").min(), "c": d.close.resample("1D").last()}); U[("crypto", s)].index = U[("crypto", s)].index.tz_localize(None)
    return U

def summ(t, lab, cls):
    t = t.sort_values("t"); r = t.r; h = len(r) // 2; y = t.groupby(t.t.dt.year).r.mean()
    return dict(cls=cls, variant=lab, trades=len(r), win=round((r > 0).mean(), 3), mean_pct=round(100 * r.mean(), 3), median_pct=round(100 * r.median(), 3),
                h1=round(100 * r[:h].mean(), 3), h2=round(100 * r[h:].mean(), 3), yrs_pos=f"{(y > 0).sum()}/{len(y)}", worst_yr=round(100 * y.min(), 2),
                days=round(t.days.mean(), 1), syms_pos=f"{(t.groupby('sym').r.mean() > 0).sum()}/{t.sym.nunique()}")

if __name__ == "__main__":
    U = load(); rows = []; ALL = {}
    for lab, kw in (("S3 v2 context", {}), ("classic Connors (above 200d)", {"filt": "up200"}), ("S4 v2 context, maker bid", {"maker": True}), ("S3 v2 context, RSI2<5", {"rsi": 5})):
        tt = []
        for (cls, s), x in U.items():
            D = prep(x); cost = 0.0002 if cls == "FX" else (0.0014 if cls == "crypto" else 0.001)
            tt += [(cls, s, t, r, dd) for t, r, dd in trades(D, cost, **kw)]
        T = pd.DataFrame(tt, columns=["cls", "sym", "t", "r", "days"]); T["t"] = pd.to_datetime(T.t); ALL[lab] = T
        for cls, g in T.groupby("cls"): rows.append(summ(g, lab, cls))
        print(lab, "done", flush=True)
    R = pd.DataFrame(rows).sort_values(["cls", "variant"]); R.to_csv("runs/research/cross_asset_s3.csv", index=False)
    pd.to_pickle(ALL, "runs/research/cross_asset_s3.pkl"); pd.set_option("display.width", 300); print(R.to_string(index=False))
    T = ALL["S3 v2 context"]
    for cls in ("indices", "commodities", "FX", "bonds", "crypto"):
        g = T[T.cls == cls]; print(cls, g.groupby("sym").r.agg(["count", "mean"]).assign(mean=lambda x: (100 * x["mean"]).round(2)).to_dict("index"))
