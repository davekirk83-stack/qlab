"""ML4T-style combined-signal test (doc 139).

Protocol, fixed before any result was seen:
- Sealed holdout from 2025-04-01 to the end of data. Nothing is tuned on it; it is scored once at the end.
- Development = walk-forward, expanding window, refit each calendar year (test years 2019..2024 + 2025Q1),
  with a purge gap of `horizon` days between the end of training and the start of the test.
- One fixed LightGBM configuration plus an L2-logistic / ridge baseline. No hyperparameter search.
- Trial count logged for deflation (rule 179).

Test A: BTC and ETH daily, long/flat (no directional shorts on BTC/ETH), horizons 1d and 7d.
         Fill at next close, 10bp per side. Baselines: buy-and-hold, trend (close > EMA200).
Test B: daily crypto panel (point-in-time: listed 200d, trailing $1m median daily volume), weekly rebalance, long the top fifth by predicted 7d
         return, equal weight, 20bp per side. Baselines: equal-weight universe, BTC. (Survivorship bias:
         the universe is coins that exist today; that flatters the equal-weight baseline and the model alike.)
"""
import pandas as pd, numpy as np, glob, os, json, warnings
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import lightgbm as lgb
warnings.filterwarnings("ignore")
HOLD = pd.Timestamp("2025-04-01", tz="UTC")
TEST_STARTS = [pd.Timestamp(f"{y}-01-01", tz="UTC") for y in range(2019, 2026)] + [HOLD]
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=50, subsample=0.8,
           subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, random_state=7)

def load(sym):
    d = pd.read_csv(f"data_daily/{sym}.csv"); d["t"] = pd.to_datetime(d.t, unit="ms", utc=True)
    return d.set_index("t").sort_index()[["open", "high", "low", "close", "volume"]].astype(float)

def feats(d):
    c, h, l, v = d.close, d.high, d.low, d.volume; lr = np.log(c).diff(); f = pd.DataFrame(index=d.index)
    for n in (1, 3, 7, 14, 30, 90): f[f"r{n}"] = np.log(c / c.shift(n))
    f["vol7"], f["vol30"] = lr.rolling(7).std(), lr.rolling(30).std(); f["volratio"] = f.vol7 / f.vol30
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    f["rsi14"] = 100 - 100 / (1 + up / dn)
    f["z20"] = (c - c.rolling(20).mean()) / c.rolling(20).std()
    f["d_ema50"] = c / c.ewm(span=50, adjust=False).mean() - 1; f["d_ema200"] = c / c.ewm(span=200, adjust=False).mean() - 1
    f["dd90"] = c / c.rolling(90).max() - 1; f["up90"] = c / c.rolling(90).min() - 1
    f["range7"] = ((h - l) / c).rolling(7).mean(); f["volz"] = np.log(v / v.rolling(30).mean()).replace([np.inf, -np.inf], np.nan)
    f["dow"] = d.index.dayofweek; f["month"] = d.index.month
    return f

def walk(X, y, model_fn, horizon, dates):
    """Expanding walk-forward; returns out-of-sample predictions for dev folds and holdout (holdout fit on all dev data)."""
    pred = pd.Series(np.nan, index=X.index)
    for i in range(len(TEST_STARTS)):
        s = TEST_STARTS[i]; e = TEST_STARTS[i + 1] if i + 1 < len(TEST_STARTS) else dates.max() + pd.Timedelta(days=1)
        tr = dates < s - pd.Timedelta(days=horizon); te = (dates >= s) & (dates < e)
        if tr.sum() < 500 or te.sum() == 0: continue
        m = model_fn(); m.fit(X[tr], y[tr])
        pred[te] = m.predict_proba(X[te])[:, 1] if hasattr(m, "predict_proba") else m.predict(X[te])
    return pred

def perf(r):
    r = r.dropna(); ann = 365
    if len(r) < 30 or r.std() == 0: return dict(ret=np.nan, sharpe=np.nan, dd=np.nan, n=len(r))
    eq = (1 + r).cumprod()
    return dict(ret=eq.iloc[-1] - 1, sharpe=r.mean() / r.std() * np.sqrt(ann), dd=(eq / eq.cummax() - 1).min(), n=len(r))

def test_a(out, trials):
    for sym in ("BTCUSD", "ETHUSD"):
        d = load(sym); F = feats(d); ret = d.close.pct_change()
        for H in (1, 7):
            y = (d.close.shift(-H) / d.close - 1 > 0).astype(int); ok = F.notna().all(1) & d.close.shift(-H).notna()
            X, Y, dates = F[ok], y[ok], F.index[ok]
            preds = {"logit": walk(X, Y, lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000)), H, dates),
                     "lgbm": walk(X, Y, lambda: lgb.LGBMClassifier(**LGB), H, dates)}
            trials += 2
            for name, p in preds.items():
                p = p.reindex(d.index)
                pos = (p > 0.5).astype(float).where(p.notna())
                held = pos.shift(1)                              # decided at close t, held over t+1 (fill at close t)
                strat = held * ret - 0.0010 * held.diff().abs()
                for seg, mask in (("dev 2019-25Q1", (d.index >= TEST_STARTS[0]) & (d.index < HOLD)), ("HOLDOUT", d.index >= HOLD)):
                    s = perf(strat[mask & held.notna()]); b = perf(ret[mask & held.notna()])
                    tr = d.close > d.close.ewm(span=200, adjust=False).mean(); trs = tr.shift(1).astype(float) * ret - 0.0010 * tr.astype(float).diff().abs().shift(1).fillna(0)
                    t = perf(trs[mask & held.notna()])
                    acc = ((p > 0.5).astype(int) == y.reindex(d.index))[mask & p.notna() & ok.reindex(d.index, fill_value=False)].mean()
                    out.append(dict(test="A", asset=sym, h=H, model=name, seg=seg, ret=s["ret"], sharpe=s["sharpe"], dd=s["dd"],
                                    in_mkt=held[mask].mean(), hit=acc, bh_sharpe=b["sharpe"], trend_sharpe=t["sharpe"], bh_ret=b["ret"], trend_ret=t["ret"]))
    return trials

def test_b(out, trials):
    syms = []
    for p in glob.glob("data_daily/*USD.csv"):
        s = os.path.basename(p)[:-4]
        try: d = load(s)
        except Exception: continue
        if len(d) > 250 and d.index[-1] >= pd.Timestamp("2026-10-01", tz="UTC"): syms.append(s)
    rows = []; btc_r7 = np.log(load("BTCUSD").close).diff(7)
    for s in syms:
        d = load(s); F = feats(d); F["btc_r7"] = btc_r7.reindex(F.index); F["fwd7"] = np.log(d.close.shift(-7) / d.close); F["sym"] = s
        dv = (d.close * d.volume).rolling(30).median(); age = np.arange(len(d))
        F = F[(dv > 1e6).values & (age >= 200)]          # point-in-time universe: 200d listed, $1m median daily volume
        rows.append(F)
    P = pd.concat(rows).reset_index()
    P = P[P.t.dt.dayofweek == 0]                                     # weekly, Mondays
    for col in ("r7", "r30", "r90", "vol30", "d_ema200"): P[col + "_xs"] = P.groupby("t")[col].rank(pct=True)
    P["y"] = P.groupby("t")["fwd7"].rank(pct=True)                   # cross-sectional rank target
    feat_cols = [c for c in P.columns if c not in ("t", "sym", "fwd7", "y", "dow")]
    P = P.dropna(subset=feat_cols + ["y"]).reset_index(drop=True)
    dates = P.t; X = P[feat_cols]; Y = P.y
    preds = {"ridge": walk(X, Y, lambda: make_pipeline(StandardScaler(), Ridge(alpha=10.0)), 7, dates),
             "lgbm": walk(X, Y, lambda: lgb.LGBMRegressor(**LGB), 7, dates)}
    trials += 2
    for name, p in preds.items():
        P["p"] = p; wk = []
        prev = set()
        for t, g in P.dropna(subset=["p"]).groupby("t"):
            k = max(1, len(g) // 5); top = g.nlargest(k, "p"); held = set(top.sym)
            turn = len(held ^ prev) / (2 * k) if prev else 1.0; prev = held
            wk.append(dict(t=t, strat=np.expm1(top.fwd7).mean() - 0.0020 * 2 * turn, ew=np.expm1(g.fwd7).mean(),
                           ls=np.expm1(top.fwd7).mean() - np.expm1(g.nsmallest(k, "p").fwd7).mean(),
                           ic=g[["p", "fwd7"]].corr(method="spearman").iloc[0, 1], n=len(g)))
        W = pd.DataFrame(wk).set_index("t")
        for seg, mask in (("dev 2019-25Q1", W.index < HOLD), ("HOLDOUT", W.index >= HOLD)):
            w = W[mask]; sh = lambda r: r.mean() / r.std() * np.sqrt(52)
            out.append(dict(test="B", asset=f"panel {int(w.n.median())} coins", h=7, model=name, seg=seg,
                            ret=(1 + w.strat).prod() - 1, sharpe=sh(w.strat), dd=((1 + w.strat).cumprod() / (1 + w.strat).cumprod().cummax() - 1).min(),
                            in_mkt=1.0, hit=w.ic.mean(), bh_sharpe=sh(w.ew), trend_sharpe=sh(w.ls), bh_ret=(1 + w.ew).prod() - 1, trend_ret=np.nan))
    return trials, syms

if __name__ == "__main__":
    out = []; trials = 0
    trials = test_a(out, trials)
    trials, syms = test_b(out, trials)
    R = pd.DataFrame(out)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    fmt = R.copy()
    for c in ("ret", "dd", "in_mkt", "bh_ret", "trend_ret"): fmt[c] = (fmt[c] * 100).round(1)
    for c in ("sharpe", "bh_sharpe", "trend_sharpe", "hit"): fmt[c] = fmt[c].round(3)
    txt = fmt.to_string(index=False) + f"\n\nTrials (model x horizon x asset/test): {trials}\nPanel coins: {len(syms)}: {' '.join(sorted(syms))}\n" \
          "Test A: hit = directional accuracy; bh/trend = buy-and-hold / close>EMA200 on same days.\n" \
          "Test B: hit = mean weekly Spearman IC; bh = equal-weight universe; trend_sharpe column = top-minus-bottom fifth spread Sharpe (diagnostic).\n"
    print(txt); open("runs/ml4t_combined_test.txt", "w").write(txt)
