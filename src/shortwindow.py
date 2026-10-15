"""
HOW SHORT A CHART CAN EACH ELEMENT READ, AND DOES IT TRAVEL OFF CRYPTO?

DK: "we need our strategy to be nimble enough to assess a chart on a much
     smaller chart window and still be effective ... And to apply it to any
     chart - not just BTC"

THE DISTINCTION THIS PROGRAMME HAS BEEN CONFLATING. The ESTIMATION window is
offline: years of history used once to learn which elements work and where the
regime sits. The DECISION window is online: what the live system has in front
of it to call a chart now. Only the second has to be short. Nothing stops us
calibrating on eleven years and deploying something that reads fifty bars -
but we have never checked whether the elements survive that.

FIRST ATTEMPT WAS WRONG AND IS RECORDED AS SUCH. I shrank every indicator's
LOOKBACK by monkey-patching rolling() and ewm(). That broke on the first
weighted-window element (a fixed 8-element weight vector against a 4-bar
window) and it was the wrong semantic regardless: a trader on a short chart
does not have shorter indicator periods, they have FEWER BARS. A 50-bar chart
simply cannot produce a 200-bar EMA, and the honest question is what it can
produce instead.

SO: the chart is truncated, not the indicators. Each symbol is cut into
non-overlapping blocks of K bars. The library is computed WITHIN each block,
so nothing can see data older than K bars, and only the LAST row of each block
is kept - that is the live decision point of a chart exactly K bars long.
Paired with the forward return, that gives the IC available to someone who has
only K bars of history.

Two things fall out per element: whether it produces a value at all at that K
(a 200-bar measure on a 50-bar chart is simply absent), and whether the value
it produces still predicts.

GENERALITY, DK's second point, in the same run: the identical measurement on
data_wide, 130 US equities with ten years of daily bars. A genuinely
independent market. An element that works on crypto AND equities is a property
of markets; one that works only on crypto is a property of crypto, which is
worth knowing before anything is sized on it.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd
from scipy import stats
import elements as EL
import elements_mktadv as MA

HORIZON = 20
BLOCKS = [400, 200, 100, 50]


def load_panel(which):
    out = {}
    src = ("/home/claude/qlab/data_1h_33/*.csv" if which == "crypto"
           else "/home/claude/qlab/data_wide/*.csv")
    need = 2000 if which == "crypto" else 1200
    for p in sorted(glob.glob(src)):
        d = pd.read_csv(p)
        d.index = pd.to_datetime(d.date, utc=True)
        if len(d) > need:
            out[os.path.basename(p)[:-4]] = d[["open", "high", "low", "close", "volume"]]
    return out


def decision_points(d, K):
    """Last row of each non-overlapping K-bar block: a chart exactly K long."""
    rows = []
    n = len(d)
    fwd_all = d.close.shift(-HORIZON) / d.close - 1
    for start in range(0, n - K - HORIZON, K):
        blk = d.iloc[start:start + K]
        try:
            f = EL.build(blk)
            f.update(MA.build(blk))
        except Exception:
            continue
        i = K - 1
        rec = {"ts": blk.index[i], "fwd": fwd_all.iloc[start + i]}
        for k, v in f.items():
            try:
                val = float(v[i])
            except Exception:
                val = np.nan
            rec[k] = val
        rows.append(rec)
    return pd.DataFrame(rows)


def measure(data, K, label):
    per = {}
    for i, (s, d) in enumerate(data.items(), 1):
        T = decision_points(d, K)
        if len(T) >= 4: per[s] = T
        if i % 25 == 0: print(f"    [{label} K={K}] {i}/{len(data)}", flush=True)
    if not per: return pd.DataFrame()
    # panel-demean the forward return by timestamp
    F = pd.concat([T.assign(sym=s)[["ts", "sym", "fwd"]] for s, T in per.items()])
    F["dm"] = F.fwd - F.groupby("ts").fwd.transform("mean")
    dm = {(r.sym, r.ts): r.dm for r in F.itertuples()}
    names = sorted(set().union(*[set(T.columns) for T in per.values()]) - {"ts", "fwd"})
    rows = []
    for n in names:
        ics = []; cov = []
        for s, T in per.items():
            if n not in T.columns: continue
            x = T[n].values
            y = np.array([dm.get((s, t), np.nan) for t in T.ts])
            m = np.isfinite(x) & np.isfinite(y)
            cov.append(np.isfinite(x).mean())
            if m.sum() < 4 or len(np.unique(x[m])) < 3: continue
            ics.append(stats.spearmanr(x[m], y[m]).statistic)
        if len(ics) < 8: continue
        a = np.array(ics, float)
        rows.append(dict(name=n, K=K, panel=label, ic=np.nanmean(a),
                         agree=int((np.sign(a) == np.sign(np.nanmean(a))).sum()),
                         total=len(a), coverage=float(np.nanmean(cov))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "crypto"
    data = load_panel(which)
    print(f"{which}: {len(data)} symbols, horizon {HORIZON} bars", flush=True)
    out = [measure(data, K, which) for K in BLOCKS]
    T = pd.concat([x for x in out if len(x)], ignore_index=True)
    T.to_csv(f"/home/claude/qlab/runs/shortwin_{which}.csv", index=False)

    piv = T.pivot_table(index="name", columns="K", values="ic")
    cov = T.pivot_table(index="name", columns="K", values="coverage")
    have = [k for k in BLOCKS if k in piv.columns]
    big = piv[piv[max(have)].abs() > 0.02] if max(have) in piv else piv
    print(f"\nIC AVAILABLE FROM A CHART OF ONLY K BARS — {which}")
    print(f"  {'element':<22}" + "".join(f"{'K='+str(k):>10}" for k in have)
          + f"{'cov@50':>9}")
    rows = []
    for n in big.index:
        r = [piv.loc[n, k] if k in piv.columns else np.nan for k in have]
        c50 = cov.loc[n, 50] if 50 in cov.columns else np.nan
        rows.append((n, r, c50))
    rows.sort(key=lambda z: -(abs(z[1][-1]) if np.isfinite(z[1][-1]) else 0))
    for n, r, c in rows[:26]:
        print(f"  {n:<22}" + "".join(f"{v:>+10.4f}" if np.isfinite(v) else f"{'-':>10}"
                                     for v in r) + f"{c*100:>8.0f}%")
    ok = [z for z in rows if np.isfinite(z[1][-1]) and np.isfinite(z[1][0])
          and abs(z[1][-1]) >= 0.7 * abs(z[1][0])
          and np.sign(z[1][-1]) == np.sign(z[1][0]) and z[2] > 0.9]
    print(f"\n  SHORT-CHART SURVIVORS — keep sign and >=70% of their K=400 IC "
          f"on a 50-bar chart, with >90% coverage: {len(ok)} of {len(rows)}")
    for n, r, c in ok[:22]:
        print(f"    {n:<24}K=400 {r[0]:+.4f}  ->  K=50 {r[-1]:+.4f}")
