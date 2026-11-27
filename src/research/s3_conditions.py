"""DK 27 Nov 22:34: "establishing best conditions". Step 2 of the S3 refinement (doc 280).
Step 1 (s3_refine.py) winners: IBS < 0.25 (close in the bottom quarter of the day's range) and 'nogap' (skip a > 3-sigma shock day)
improved the mean in both halves; the scale-in (DK's ladder) cut the tail everywhere. Here:
  A) combinations: base / ibs+nogap / ibs+nogap+scale / rsi5+ibs+nogap  (commodities: IBS hurt there, so nogap and nogap+scale)
  B) on the best combination, the result split by the CONDITIONS at entry, to establish which conditions give the best trades:
     context (uptrend vs deep flush), RSI(2) depth, IBS depth, volatility regime (sigma vs its 1-year median), market regime
     (S&P 500 above / below its 200-day), VIX level, day of week, distance under the 5-day mean (in sigmas)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import cross_asset_s3 as X, s3_refine as R

if __name__ == "__main__":
    U = X.load(); spx = X.prep(U[("indices", "SPX")]); SPXUP = (spx.c > spx.c.rolling(200).mean())
    vix = pd.read_csv("data_daily/VIX.csv", index_col=0); vix.index = pd.to_datetime(vix.index, utc=True).tz_localize(None).normalize(); VIX = vix.close
    P = {k: R.prep2(v) for k, v in U.items() if k[0] in ("US stocks", "indices", "commodities", "crypto")}
    COMBOS = {"base": {}, "ibs+nogap": {"ibs": 1, "nogap": 1}, "ibs+nogap+scale": {"ibs": 1, "nogap": 1, "scale": 1}, "rsi5+ibs+nogap": {"rsi5": 1, "ibs": 1, "nogap": 1},
              "nogap": {"nogap": 1}, "nogap+scale": {"nogap": 1, "scale": 1}}
    rows = []; keep = {}
    for lab, o in COMBOS.items():
        tt = []
        for (cls, s), D in P.items():
            cost = 0.0014 if cls == "crypto" else 0.001
            for t, r in R.trades(D, cost, o):
                x = D.loc[t]; tt.append((cls, s, t, r, x.ctx and x.up, x.rsi2, x.ibs, x.sig, (x.c - x.ma5) / (x.c * x.sig) if x.sig > 0 else np.nan))
        T = pd.DataFrame(tt, columns=["cls", "sym", "t", "r", "up", "rsi2", "ibs", "sig", "dist"]); T["t"] = pd.to_datetime(T.t); keep[lab] = T
        for cls, g in T.groupby("cls"): rows.append(dict(combo=lab, cls=cls, **R.stats(g)))
        print(lab, "done", flush=True)
    C = pd.DataFrame(rows); C.to_csv("runs/research/s3_combos.csv", index=False); pd.to_pickle(keep, "runs/research/s3_conditions.pkl")
    pd.set_option("display.width", 250)
    for cls, g in C.groupby("cls"): print("\n==", cls); print(g.drop(columns="cls").to_string(index=False))
    # B) conditions, on ibs+nogap (commodities: nogap)
    B = pd.concat([keep["ibs+nogap"][keep["ibs+nogap"].cls != "commodities"], keep["nogap"][keep["nogap"].cls == "commodities"]])
    B["sig_med"] = B.groupby("sym").sig.transform(lambda s: s.rolling(250, min_periods=60).median())
    B["context"] = np.where(B.up, "uptrend", "deep flush")
    B["rsi_b"] = pd.cut(B.rsi2, [0, 2, 5, 10, 100], labels=["<2", "2-5", "5-10", ">10"])
    B["ibs_b"] = pd.cut(B.ibs, [-0.01, 0.1, 0.25, 1.01], labels=["<0.10", "0.10-0.25", ">0.25"])
    B["vol"] = np.where(B.sig > B.sig_med, "high vol", "low vol")
    B["mkt"] = np.where(SPXUP.reindex(B.t.dt.normalize()).ffill().values == True, "S&P above 200d", "S&P below 200d")
    vx = VIX.reindex(B.t.dt.normalize()).ffill().values; B["vix"] = pd.cut(vx, [0, 15, 20, 30, 200], labels=["VIX<15", "15-20", "20-30", ">30"])
    B["dow"] = B.t.dt.day_name().str[:3]
    B["dist_b"] = pd.cut(B.dist, [-99, -3, -2, -1, 99], labels=["< -3 sig", "-3..-2", "-2..-1", "> -1"])
    out = []
    for f in ("context", "rsi_b", "ibs_b", "vol", "mkt", "vix", "dow", "dist_b"):
        for (cls, lvl), g in B.groupby(["cls", f]):
            if len(g) >= 15: out.append(dict(cond=f, level=str(lvl), cls=cls, **R.stats(g)))
    Q = pd.DataFrame(out); Q.to_csv("runs/research/s3_conditions.csv", index=False)
    for f, g in Q.groupby("cond", sort=False): print("\n## by", f); print(g.drop(columns="cond")[["level", "cls", "n", "win", "mean", "h1", "h2", "pf", "worst", "tail10"]].to_string(index=False))
