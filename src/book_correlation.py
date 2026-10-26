"""How many independent bets do the books really make? (avenue 4, after the Goldman 'correlations jump' note, 26 Oct 2026)
Daily P&L series (by exit date) for each engine over the last year from its own backtest, then pairwise correlations and the
effective number of bets N_eff = N / (1 + (N-1) * mean rho), on ALL days and on the WORST 10% of days for the combined book."""
import sys, glob, os, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import paperbook6 as P6, paperbook7 as P7
T0 = pd.Timestamp("2025-10-20", tz="UTC"); out = {}
syms = sorted(os.path.basename(f)[:-4] for f in glob.glob("/home/claude/qlab/data_15m/*.csv"))
def load15(s):
    d = pd.read_csv(f"/home/claude/qlab/data_15m/{s}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    return d[d.index >= T0 - pd.Timedelta(days=60)][["open", "high", "low", "close"]]
med = json.load(open("/home/claude/qlab/runs/contain_median.json")) if os.path.exists("/home/claude/qlab/runs/contain_median.json") else {}
for name, hold in (("Range v3 (crypto)", False), ("Range v3.1", True)):
    rows = []
    for s in syms:
        if s in ("BTCUSD",) and False: continue
        d = load15(s); P6._MED = med if isinstance(med, dict) else {}
        try: closed, _ = P6.step(s, d, {}, str(d.index[250]), [10**6], hold_regime=hold)
        except Exception as e: continue
        rows += [(pd.Timestamp(c[3]).normalize(), c[4]/27) for c in closed]
    out[name] = pd.DataFrame(rows, columns=["d", "r"]).groupby("d").r.sum()
bars = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
tr, _, _ = P7.replay(P7.features(bars), str(T0.date()), 0, us_hours=True, v11=True)
out["Ignition v1.1 (NQ)"] = pd.DataFrame([(pd.Timestamp(t["closed"]).normalize(), t["pts"]/29000*10) for t in tr], columns=["d", "r"]).groupby("d").r.sum()
exec(open("/home/claude/qlab/src/cross_hold_test.py").read().split("btc = ind(")[0])
btc4 = four("/home/claude/qlab/data_15m/BTCUSD.csv"); btc = ind(btc4); dr, gr = [], []
for s in UNIV:
    if s in ("BTCUSD", "ETHUSD"): continue
    d = four(f"/home/claude/qlab/data_15m/{s}.csv"); C, H, L, a, ef, es, e200 = ind(d)
    for i in death(C, a, ef, es):
        if d.index[i] < T0: continue
        r, k, _ = exit_(C, H, L, a, i, -1, "trail", 3, 180); dr.append((d.index[min(i+k, len(d)-1)].normalize(), r/20))
    for i in golden(C, a, ef, es):
        if d.index[i] < T0: continue
        kb = btc4.index.searchsorted(d.index[i], side="right") - 1
        if kb < 0 or not btc[0][kb] > btc[6][kb]: continue
        r, k, _ = exit_(C, H, L, a, i, 1, "fixed", 3, 18); gr.append((d.index[min(i+k, len(d)-1)].normalize(), r/20))
out["Death-cross"] = pd.DataFrame(dr, columns=["d", "r"]).groupby("d").r.sum()
out["Golden-cross"] = pd.DataFrame(gr, columns=["d", "r"]).groupby("d").r.sum()
days = pd.date_range(T0, pd.Timestamp("2026-09-30", tz="UTC"), freq="D")
M = pd.DataFrame({k: v.reindex(days).fillna(0.0) for k, v in out.items()})
btcd = load15("BTCUSD").close.resample("1D").last().pct_change().reindex(days)
print(f"daily P&L, {days[0].date()} -> {days[-1].date()}, {len(days)} days; active days per book: " + ", ".join(f"{k} {int((M[k]!=0).sum())}" for k in M))
Z = M/M.std(); comb = Z.mean(axis=1); worst = comb.nsmallest(int(len(comb)*0.10)).index
def neff(C):
    n = C.shape[0]; rho = (C.values.sum() - n)/(n*(n-1)); return rho, n/(1 + (n-1)*rho)
Ca = M.corr(); Cw = M.loc[worst].corr()
pd.set_option("display.width", 200); print("\nall days:\n", Ca.round(2)); print("\nworst 10% of days for the combined book:\n", Cw.round(2))
ra, na = neff(Ca); rw, nw = neff(Cw); print(f"\nmean pairwise corr: all days {ra:+.2f} -> N_eff {na:.1f} of {len(M.columns)};  worst days {rw:+.2f} -> N_eff {nw:.1f}")
print("corr with BTC daily return:", {k: round(M[k].corr(btcd), 2) for k in M})
print("worst-day mean P&L by book (std units):", {k: round(float(Z.loc[worst, k].mean()), 2) for k in M})
# External stress (avoids the selection bias of conditioning on the books' own combined worst days): BTC's worst / best 10% of days.
bw = btcd.nsmallest(int(len(btcd.dropna())*0.10)).index; bb = btcd.nlargest(int(len(btcd.dropna())*0.10)).index
print(f"\nBTC worst 10pct of days (BTC mean {btcd.loc[bw].mean()*100:.2f}%): mean P&L per book (std units):", {k: round(float(Z.loc[bw, k].mean()), 2) for k in M})
print(f"BTC best 10pct of days (BTC mean {btcd.loc[bb].mean()*100:+.2f}%): mean P&L per book (std units):", {k: round(float(Z.loc[bb, k].mean()), 2) for k in M})
Cb = M.drop(columns=["Range v3.1"]).loc[bw].corr(); rb, nb = neff(Cb)
print(f"distinct books (v3.1 dropped as a variant): on BTC's worst days mean corr {rb:+.2f} -> N_eff {nb:.1f} of {Cb.shape[0]}")
