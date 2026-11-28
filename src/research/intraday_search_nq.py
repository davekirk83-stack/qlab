"""Doc 283: the definitive day-trading search on the instrument we actually trade - IG US Tech 100 (Dukascopy NQ CFD 5-min -> 15-min,
2020-26 once the long history is in; tick-rule delta). Everything in intraday_search.py PLUS order-flow conditions:
  bar delta share (delta / ticks) > 0.10 / < -0.10, day cumulative delta > 0 / < 0, bullish / bearish delta divergence (new 20-bar low
  with cumulative 6-bar delta higher than at the previous low, and the reverse), absorption (top-decile ticks with a bottom-half range),
  delta flip (bar delta opposite to the bar's direction).
US cash session (09:30-16:00 NY) AND the full IG day (all bars, sessions split at 18:00 NY) as two universes.
PER TRADE (first bar of each signal run), costs in points: 1 pt spread + 0.5 pt slippage each side (2 pts round trip; +1 pt outside cash
hours). Edge = net minus the unconditional average of the same exit (train years). Train 2020-23 (t >= 3), test 2024-26 (unseen).
Usage: python intraday_search_nq.py [path to long nq_5m csv]"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I

def load(path, session):
    q = pd.read_csv(path, index_col=0); q.index = pd.to_datetime(q.index, utc=True)
    q = q.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum", "delta": "sum"}).dropna(subset=["close"])
    q.index = q.index.tz_convert("America/New_York")
    if session == "cash":
        m = q.index.hour * 60 + q.index.minute; q = q[(m >= 570) & (m < 960)]
    else:   # IG day: 18:00 NY -> 17:00 NY next day, labelled by the trading date
        q = q.copy(); q.index = q.index + pd.Timedelta("6h")   # shift so each trading session falls on one calendar date for the day grouping
    return q

def of_features(d, q):
    F = {}
    dl = q.delta.reindex(d.index).values if "delta" in q else np.zeros(len(d)); tk = q.vol.reindex(d.index).replace(0, np.nan).values
    sh = dl / tk; F["dshare>0.1"] = sh > 0.10; F["dshare<-0.1"] = sh < -0.10
    cd = pd.Series(dl, index=d.index).groupby(d.index.normalize()).cumsum().values; F["cumdelta>0"] = cd > 0; F["cumdelta<0"] = cd < 0
    nd6 = pd.Series(dl).rolling(6).sum().values; L = d.low.values; H = d.high.values
    ll = pd.Series(L).rolling(20).min().shift(1).values; hh = pd.Series(H).rolling(20).max().shift(1).values
    il = pd.Series(L).rolling(20).apply(np.argmin, raw=True).shift(1).values; ih = pd.Series(H).rolling(20).apply(np.argmax, raw=True).shift(1).values
    n = len(d); idx = np.arange(n); pl = np.where(np.isfinite(il), idx - 20 + np.nan_to_num(il).astype(int), 0); ph = np.where(np.isfinite(ih), idx - 20 + np.nan_to_num(ih).astype(int), 0)
    F["bull_div"] = (L < ll) & (nd6 > nd6[np.clip(pl, 0, n - 1)]); F["bear_div"] = (H > hh) & (nd6 < nd6[np.clip(ph, 0, n - 1)])
    rng = d.high - d.low; tkS = pd.Series(tk, index=d.index)
    F["absorption"] = (tkS > tkS.rolling(100).quantile(0.9)).values & (rng < rng.rolling(100).median()).values
    F["delta_flip_up"] = (d.close.values < d.open.values) & (dl > 0); F["delta_flip_dn"] = (d.close.values > d.open.values) & (dl < 0)
    return pd.DataFrame({k: np.nan_to_num(np.asarray(v, dtype=float), nan=0).astype(bool) for k, v in F.items()}, index=d.index)

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data_nq_cache/nq_5m.csv"
    spy = I.rth("data_alpaca/SPY_15m.csv.gz"); spy_day = spy.close / spy.groupby(spy.index.normalize()).open.transform("first") - 1
    allrows = []
    for session in ("cash", "allday"):
        q = load(path, session); d, C = I.features(q[["open", "high", "low", "close", "vol"]], spy_day); X = I.exits(d)
        C = pd.concat([C, of_features(d, q)], axis=1)
        if session == "allday": C = C.drop(columns=["spy_day_up", "spy_day_dn"], errors="ignore")
        C["_sym"] = "NQ_" + session; C["_grp"] = session; C["_t"] = d.index; C["_day"] = d["day"].values
        for k in X: C[f"_g{k}"] = X[k].values
        cash = ((d.index - (pd.Timedelta("6h") if session == "allday" else pd.Timedelta(0))).hour * 60 + (d.index - (pd.Timedelta("6h") if session == "allday" else pd.Timedelta(0))).minute)
        pts_side = np.where((cash >= 570) & (cash < 960), 1.0, 1.5)              # 1 pt each side in cash hours, 1.5 outside
        C["_cost"] = pts_side / d.close.values
        allrows.append(C.reset_index(drop=True))
    M = pd.concat(allrows, ignore_index=True).fillna({c: False for c in allrows[0].columns if not c.startswith("_")})
    yr = pd.to_datetime(M._t, utc=True).dt.year.values; print("rows", len(M), "years", sorted(set(yr)), flush=True)
    base = {(ex, s): M[I.gcol(ex, s)][yr <= 2023].groupby(M._grp[yr <= 2023]).mean() for ex in I.EXITS for s in (1, -1)}
    names = [c for c in M.columns if not c.startswith("_")]; B = {k: M[k].fillna(False).values.astype(bool) for k in names}; grp = M._grp.values
    res = []
    for universe in ("cash", "allday"):
        TR = (grp == universe) & (yr <= 2023); TE = (grp == universe) & (yr >= 2024)
        cands = [(a,) for a in names] + list(itertools.combinations(names, 2))
        for cb in cands:
            mk = B[cb[0]].copy()
            for k in cb[1:]: mk = mk & B[k]
            if (mk & TR).sum() < 120: continue
            for ex in I.EXITS:
                for side in (1, -1):
                    e = I.evaluate(M, mk & TR, ex, side, base)
                    if e and e["t"] >= 3.0 and e["edge"] > 0 and e["net"] > 0:
                        t2 = I.evaluate(M, mk & TE, ex, side, base) or dict(edge=np.nan, t=np.nan, net=np.nan, n=0)
                        px = float(np.nanmedian(M.loc[TE, "_gH2"].abs())) if False else None
                        res.append(dict(universe=universe, combo=" + ".join(cb), exit=ex, side="long" if side == 1 else "short", tr_net=e["net"], tr_t=e["t"], tr_n=e["n"],
                                        te_net=t2["net"], te_t=t2["t"], te_n=t2["n"]))
        print(universe, "done", flush=True)
    R = pd.DataFrame(res).sort_values("tr_t", ascending=False); R.to_csv("runs/research/intraday_search_nq.csv", index=False)
    R["oos"] = (R.te_net > 0) & (R.te_t >= 2)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 55)
    print("train survivors:", len(R), "| out-of-sample (2024-26 t>=2, net>0):", int(R.oos.sum()))
    print(R.head(25).round(4).to_string(index=False)); print("\nOOS survivors:"); print(R[R.oos].sort_values("te_t", ascending=False).head(40).round(4).to_string(index=False))
    print("\n(net is % per trade; at NQ ~20,000, 0.01% = 2 points)")
