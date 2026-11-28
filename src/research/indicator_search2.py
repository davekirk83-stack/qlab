"""Indicator search, pass 3 (DK 28 Nov 08:05 "checking all indicators in novel combinations"). Passes 1-2 (indicator_search.py) used fixed
1/5/20-day holds and found nothing that survived out of sample - but fixed holds pay the full cost and ignore exits, so even the proven
RSI(2) pullback fails that test. Pass 3 gives every combination the exits real traders pair with each signal type:
  MR    mean-reversion exit: long sells the first close above the 5-day mean (short: below), 10-day limit
  TR    trend exit: long holds until the first close under the 20-day mean (short: above), 60-day limit
  H5, H20  fixed holds (kept for comparison)
Edge = net return after costs MINUS the market class's average daily drift (train years) x days held, i.e. it must beat simply holding
that market for the same time. Per-day averaging, month-clustered t. Select on US stocks 2005-15 (t >= 3), then: US stocks 2016-26
(unseen), and indices / commodities / FX / crypto (no survivorship bias). Then triples: each surviving pair + every third condition."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import cross_asset_s3 as X
PK = "/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/ind_M.pkl"

def first_true(cond, lim):
    """index offset (1..lim) of the first True in cond[i+1 .. i+lim] for each i; lim if none."""
    n = len(cond); W = np.zeros((n, lim), bool)
    for k in range(1, lim + 1): W[:n - k, k - 1] = cond[k:]
    has = W.any(1); off = np.where(has, W.argmax(1) + 1, lim); return off

def exits(D):
    c = D.c.values; n = len(c); ma5 = D.c.rolling(5).mean().values; ma20 = D.c.rolling(20).mean().values
    out = {}
    for lab, cond, lim in (("MR", c > ma5, 10), ("MRs", c < ma5, 10), ("TR", c < ma20, 60), ("TRs", c > ma20, 60)):
        off = first_true(cond, lim); j = np.minimum(np.arange(n) + off, n - 1)
        out[f"_g{lab}"] = c[j] / c - 1; out[f"_d{lab}"] = j - np.arange(n)
    for h in (5, 20):
        j = np.minimum(np.arange(n) + h, n - 1); out[f"_gH{h}"] = c[j] / c - 1; out[f"_dH{h}"] = j - np.arange(n)
    return pd.DataFrame(out, index=D.index)

def add_exits(M):
    U = X.load(); parts = []
    for (cls, s), x in U.items():
        if cls in ("UK stocks", "bonds"): continue
        D = x.copy()
        if cls == "US stocks": D = pd.read_csv(f"data_stocks/{s}.csv.gz", parse_dates=["Date"], index_col="Date").rename(columns={"Close": "c"})
        D = D[["c"]].astype(float).dropna(); D = D[D.c > 0]
        if len(D) < 400: continue
        E = exits(D); E["_sym"] = s; E["_t"] = E.index; parts.append(E.reset_index(drop=True))
    E = pd.concat(parts, ignore_index=True)
    return M.merge(E, on=["_sym", "_t"], how="left")

EXITS = {"MR": ("MR", "MRs"), "TR": ("TR", "TRs"), "H5": ("H5", "H5"), "H20": ("H20", "H20")}

def evaluate(M, mask, ex, side):
    g = M[f"_g{EXITS[ex][0 if side == 1 else 1]}"].values; dd = M[f"_d{EXITS[ex][0 if side == 1 else 1]}"].values
    m = mask & np.isfinite(g) & (dd > 0)
    if m.sum() < 30: return None
    c = M["_cost"].values[m]; drift = M["_drift"].values[m] * dd[m]
    net = side * g[m] - 2 * c; exr = net - side * drift
    t = M["_t"].values[m]; d = pd.DataFrame({"ex": exr, "net": net, "days": dd[m]}, index=t).groupby(level=0).mean()
    if len(d) < 20: return None
    mo = d.ex.groupby(d.index.to_period("M")).mean(); tt = mo.mean() / (mo.std() / np.sqrt(len(mo))) if len(mo) > 3 and mo.std() > 0 else 0
    return dict(edge=100 * d.ex.mean(), t=tt, net=100 * d.net.mean(), hold=d.days.mean(), days=len(d), n=int(m.sum()), win=float((net > 0).mean()))

if __name__ == "__main__":
    M = pd.read_pickle(PK); M = add_exits(M); print("rows", len(M), flush=True)
    M["_cost"] = M._cls.map({"FX": 0.0002, "crypto": 0.0014}).fillna(0.001)
    yr = pd.to_datetime(M._t).dt.year
    g1 = M._r1 + 2 * M._cost                                                       # 1-day gross return (stored net of a round trip)
    M["_drift"] = M._cls.map(g1[yr <= 2015].groupby(M._cls[yr <= 2015]).mean())   # average daily drift per class, train years
    names = [c for c in M.columns if not c.startswith("_")]
    B = {k: M[k].fillna(False).astype(bool).values for k in names}
    cls = M._cls.values; y = yr.values
    TRAIN = (cls == "US stocks") & (y <= 2015); TEST = (cls == "US stocks") & (y >= 2016); OTHER = {c: cls == c for c in ("indices", "commodities", "FX", "crypto")}
    def mask(combo):
        mk = B[combo[0]].copy()
        for k in combo[1:]: mk = mk & B[k]
        return mk
    def search(cands, thr):
        res = []
        for combo in cands:
            mk = mask(combo); mt = mk & TRAIN
            if mt.sum() < 200: continue
            for ex in EXITS:
                for side in (1, -1):
                    e = evaluate(M, mt, ex, side)
                    if e and e["t"] >= thr and e["edge"] > 0 and e["net"] > 0:
                        res.append(dict(combo=" + ".join(combo), k=len(combo), exit=ex, side="long" if side == 1 else "short", **{f"tr_{a}": b for a, b in e.items()}))
        return pd.DataFrame(res)
    cands = [(a,) for a in names] + list(itertools.combinations(names, 2))
    T = search(cands, 3.0).sort_values("tr_t", ascending=False); print("train survivors (singles+pairs, t>=3):", len(T), flush=True)
    top_pairs = T[T.k == 2].drop_duplicates("combo").head(25).combo.str.split(" \\+ ").tolist()
    trip = sorted({tuple(sorted(p + [c])) for p in top_pairs for c in names if c not in p})
    T3 = search(trip, 3.5); print("triples tested:", len(trip), "survivors (t>=3.5):", len(T3), flush=True)
    T = pd.concat([T, T3]).sort_values("tr_t", ascending=False)
    out = []
    for _, r in T.head(400).iterrows():
        mk = mask(r.combo.split(" + ")); side = 1 if r.side == "long" else -1; row = dict(r)
        e = evaluate(M, mk & TEST, r.exit, side) or dict(edge=np.nan, t=np.nan, net=np.nan, hold=np.nan, days=0, n=0, win=np.nan)
        row.update({f"te_{a}": b for a, b in e.items()})
        for c, om in OTHER.items():
            e = evaluate(M, mk & om, r.exit, side); row[f"{c}_edge"] = e["edge"] if e else np.nan; row[f"{c}_net"] = e["net"] if e else np.nan; row[f"{c}_n"] = e["n"] if e else 0
        out.append(row)
    O = pd.DataFrame(out)
    O["oos_ok"] = (O.te_edge > 0) & (O.te_t >= 2) & (O.te_net > 0)
    O["xasset_pos"] = sum((O[f"{c}_edge"] > 0).astype(int) for c in OTHER); O["xasset_have"] = sum((O[f"{c}_n"] >= 30).astype(int) for c in OTHER)
    O.to_csv("runs/research/indicator_search_exits.csv", index=False)
    pd.set_option("display.width", 320); pd.set_option("display.max_colwidth", 50)
    cols = ["combo", "exit", "side", "tr_edge", "tr_net", "tr_t", "tr_n", "te_edge", "te_net", "te_t", "te_n", "indices_edge", "commodities_edge", "crypto_edge", "FX_edge", "xasset_pos", "xasset_have"]
    print("\nTOP 30 by train t:"); print(O[cols].head(30).round(3).to_string(index=False))
    S = O[O.oos_ok].copy(); print(f"\nOUT-OF-SAMPLE SURVIVORS (US stocks 2016-26 t>=2, net > 0): {len(S)}")
    print(S.sort_values("te_t", ascending=False)[cols].head(40).round(3).to_string(index=False))
    print("\n... of which positive on >= half the other markets that had signals:")
    print(S[S.xasset_pos * 2 >= S.xasset_have.clip(lower=1)][cols].head(40).round(3).to_string(index=False))
