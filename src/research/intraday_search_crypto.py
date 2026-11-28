"""Doc 283: day-trading search on crypto (24/7) - same conditions and per-trade method as intraday_search.py, Binance 15-min 2021-26,
sessions = UTC days. Costs Revolut X: entry as a resting maker bid at the next bar's open (0%, optimistic on fills), exit taker 0.09% +
0.05% slip = 0.14% per trade. Train BTC + ETH 2021-23 (t >= 3), test BTC + ETH 2024-26, confirm on the 8 other coins (all years)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I, dk_v2_all_charts as A
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")
if __name__ == "__main__":
    rows = []
    for s in COINS:
        x = A.coin(s); vol = []
        import glob
        for f in sorted(glob.glob(f"{A.CO}/{s}-15m-*.csv")):
            v = pd.read_csv(f, header=None, usecols=[0, 5]); v.columns = ["t", "vol"]; v["t"] = pd.to_datetime(v.t // 1000 if v.t.iloc[0] > 1e14 else v.t, unit="ms", utc=True); vol.append(v.set_index("t"))
        x["vol"] = pd.concat(vol).sort_index().vol.groupby(level=0).last().reindex(x.index).values
        x.index = x.index.tz_convert("UTC")
        d, C = I.features(x[["open", "high", "low", "close", "vol"]], pd.Series(dtype=float)); X = I.exits(d)
        C = C.drop(columns=["spy_day_up", "spy_day_dn", "first_hour", "midday", "last_hour", "bar0", "bar1"], errors="ignore")
        C["asia"] = (d.index.hour < 8); C["europe"] = (d.index.hour >= 8) & (d.index.hour < 13); C["us"] = (d.index.hour >= 13) & (d.index.hour < 21)
        C["_sym"] = s; C["_grp"] = "core" if s in ("BTCUSDT", "ETHUSDT") else "alts"; C["_t"] = d.index; C["_day"] = d["day"].values
        for k in X: C[f"_g{k}"] = X[k].values
        rows.append(C.reset_index(drop=True)); print(s, len(C), flush=True)
    M = pd.concat(rows, ignore_index=True); M["_cost"] = 0.0007          # 0 in + 0.14% out, split per side for the evaluator's 2 x cost
    yr = pd.to_datetime(M._t, utc=True).dt.year.values
    base = {(ex, s): M[I.gcol(ex, s)][yr <= 2023].groupby(M._grp[yr <= 2023]).mean() for ex in I.EXITS for s in (1, -1)}
    names = [c for c in M.columns if not c.startswith("_")]; B = {k: M[k].fillna(False).values.astype(bool) for k in names}; grp = M._grp.values
    TR = (grp == "core") & (yr <= 2023); TE = (grp == "core") & (yr >= 2024); AL = grp == "alts"
    res = []
    for cb in [(a,) for a in names] + list(itertools.combinations(names, 2)):
        mk = B[cb[0]].copy()
        for k in cb[1:]: mk = mk & B[k]
        if (mk & TR).sum() < 120: continue
        for ex in I.EXITS:
            for side in (1, -1):
                e = I.evaluate(M, mk & TR, ex, side, base)
                if e and e["t"] >= 3.0 and e["edge"] > 0 and e["net"] > 0:
                    t2 = I.evaluate(M, mk & TE, ex, side, base) or dict(net=np.nan, t=np.nan, n=0); a2 = I.evaluate(M, mk & AL, ex, side, base) or dict(net=np.nan, t=np.nan, n=0)
                    res.append(dict(combo=" + ".join(cb), exit=ex, side="long" if side == 1 else "short", tr_net=e["net"], tr_t=e["t"], tr_n=e["n"], te_net=t2["net"], te_t=t2["t"], te_n=t2["n"], alts_net=a2["net"], alts_t=a2["t"], alts_n=a2["n"]))
    if not res: print("no train survivors"); sys.exit(0)
    R = pd.DataFrame(res).sort_values("tr_t", ascending=False); R.to_csv("runs/research/intraday_search_crypto.csv", index=False)
    R["oos"] = (R.te_net > 0) & (R.te_t >= 2)
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 55)
    print("train survivors:", len(R), "| OOS (BTC+ETH 2024-26 t>=2, net>0):", int(R.oos.sum()), "| of which alts net>0:", int((R.oos & (R.alts_net > 0)).sum()))
    print(R.head(20).round(4).to_string(index=False)); print("\nOOS survivors:"); print(R[R.oos].sort_values("te_t", ascending=False).head(30).round(4).to_string(index=False))
