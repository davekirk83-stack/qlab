"""Cross-sectional momentum (task 11, 24 Oct 2026). Rank the universe by trailing return (skip the last week), hold the top decile
(long) and bottom decile (short) equal-weight, rebalance weekly, costs per rebalance. Universes: crypto daily (Coinbase, 300 products,
only coins with data on the date) and ETFs (37, 20 years). Reported per week, deflated across the cuts tried (rule 179)."""
import glob, os, numpy as np, pandas as pd
from scipy.stats import norm

def load(folder, crypto):
    out = {}
    for f in glob.glob(f"{folder}/*.csv"):
        d = pd.read_csv(f, index_col=0)
        idx = pd.to_datetime(d.index, unit="ms", utc=True) if crypto else pd.to_datetime(d.index, utc=True)
        s = pd.Series(d.close.values, index=idx.normalize()).astype(float); s = s[~s.index.duplicated()]
        if len(s) >= 400: out[os.path.basename(f)[:-4]] = s
    return pd.DataFrame(out).sort_index()

def run(P, look, skip, hold_days, cost, top=0.1, min_names=20):
    """P: close panel. look: lookback days; skip: recent days excluded; hold_days: rebalance interval."""
    R = P.pct_change(); dates = P.index[look+skip::hold_days]
    rows = []
    for i in range(len(dates)-1):
        t0, t1 = dates[i], dates[i+1]
        px0 = P.loc[:t0].iloc[-1]; sig = (P.loc[:t0].iloc[-1-skip] / P.loc[:t0].iloc[-1-skip-look] - 1)
        ok = sig.dropna().index.intersection(px0.dropna().index)
        if len(ok) < min_names: continue
        sig = sig[ok].sort_values(); k = max(int(len(ok)*top), 2)
        lo, hi = sig.index[:k], sig.index[-k:]
        fwd = (P.loc[:t1].iloc[-1] / px0 - 1)
        rl, rs = fwd[hi].mean(), fwd[lo].mean(); mk = fwd[ok].mean()
        rows.append((t0, rl - cost, -rs - cost, rl - rs - 2*cost, mk))
    r = pd.DataFrame(rows, columns=["d", "long", "short", "ls", "mkt"]).set_index("d")
    return r

def summ(r, col):
    x = r[col]; t = x.mean()/x.std()*np.sqrt(len(x)); return x.mean()*100, t, (x > 0).mean()*100

if __name__ == "__main__":
    for name, folder, crypto, cost in (("crypto", "/home/claude/qlab/data_daily", True, 0.0012), ("etf", "/home/claude/qlab/data_etf20", False, 0.0004)):
        P = load(folder, crypto); print(f"\n== {name}: {P.shape[1]} names, {P.index[0].date()} -> {P.index[-1].date()}")
        tried = 0
        for look, skip in ((20, 5), (60, 5), (90, 7), (180, 7)):
            for hold in (7,):
                r = run(P, look, skip, hold, cost); tried += 1
                h = len(r)//2
                line = f"look {look:3d} skip {skip} hold {hold}: n {len(r):4d} | "
                for col in ("long", "short", "ls"):
                    m, t, w = summ(r, col); m1, _, _ = summ(r.iloc[:h], col); m2, _, _ = summ(r.iloc[h:], col)
                    line += f"{col} {m:+.2f}%/wk t {t:+.1f} win {w:.0f}% (H1 {m1:+.2f} H2 {m2:+.2f}) | "
                m, t, w = summ(r, "mkt"); line += f"mkt {m:+.2f}%/wk"
                print(line)
        # best long-only vs market, by year, for the 90/7 cut
        r = run(P, 90, 7, 7, cost); r["xsm"] = r.long - r.mkt
        print("  90/7 long minus market by year:", {y: round(float(v*100), 2) for y, v in r.xsm.groupby(r.index.year).mean().items() if y >= 2017})
        print(f"  deflated bar for {tried*3} cuts: t > {norm.ppf(1-0.05/(tried*3)):.2f}")
