"""Doc 205 — scheduled news through the standard test (DK 10 Nov 04:56: "you're not reacting to the news ... blind to the trading environment").
Events known in advance: scheduled FOMC decision days 2000-2026 (eco3min list; unscheduled meetings excluded) and US jobs reports (first Friday
of the month — an approximation; BLS occasionally moves it). Same honest daily simulator as docs 202-203.
1. Pre-FOMC drift (Lucca & Moench 2015): buy US indices at the close the day before a scheduled FOMC decision, sell at the FOMC-day close.
2. For each daily book: are trades whose holding window contains an FOMC day / jobs day better or worse? Then a walk-forward switch
   (skip entries with an event inside the hold; adopted per year only if it helped in earlier years) — same rule as doc 201."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
FOMC = pd.to_datetime([l.split()[0] for l in open("runs/fomc_dates.txt") if l.strip() and not l.startswith("#") and "(U)" not in l])
def nfp_days(idx):
    s = pd.Series(idx, index=idx); return pd.DatetimeIndex([g.iloc[0] for _, g in s[s.dt.dayofweek == 4].groupby([s.dt.year, s.dt.month])])

def run2(k, entry, side=1, exit_=None, maxd=10, stop=3.0, how="C"):
    """F.run with the exit date kept (same logic)."""
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = entry.reindex(d.index).fillna(False).values.astype(bool); X = exit_.reindex(d.index).fillna(False).values.astype(bool) if exit_ is not None else np.zeros(len(d), bool)
    cost = F.COST.get(k, .002); fy = 0.06 / 365 * 1.4; out = []; i = 0; n = len(C)
    while i < n - 1:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        s = side
        if how == "OC":
            e = O[i]; st = e - s * stop * A[i]; px = st if L[i] <= st else C[i]
            out.append((d.index[i], d.index[i], (s * (px - e) - cost * e * 2) / A[i])); i += 1; continue
        e = C[i]; st = e - s * stop * A[i]; j = i + 1; px = None
        while j < n:
            if L[j] <= st: px = min(st, O[j]); break
            if X[j] or (j - i) >= maxd: px = C[j]; break
            j += 1
        if px is None: break
        out.append((d.index[i], d.index[j], (s * (px - e) - cost * e * 2 - fy * e * (j - i)) / A[i])); i = j + 1
    return out

def stats(r):
    r = np.asarray(r); 
    if len(r) < 3: return f"n{len(r)}"
    return f"n{len(r):5d} mean {r.mean():+.3f} t {r.mean()/r.std(ddof=1)*np.sqrt(len(r)):+.2f}"

if __name__ == "__main__":
    print("== 1. Pre-FOMC drift: buy the close before a scheduled FOMC day, sell the FOMC-day close (stop 3 ATR)")
    for k in ("SPX", "NDX", "DJI", "RUT"):
        d = F.D[k]; nxt = pd.Series(d.index, index=d.index).shift(-1); sig = nxt.isin(FOMC)
        t = pd.DataFrame(run2(k, sig, 1, None, 1), columns=["t", "x", "R"]); y = t.groupby(t.t.dt.year).R.sum()
        print(f"  {k}: {stats(t.R)} | years + {(y>0).sum()}/{len(y)} | 2000-12 {t[t.t.dt.year<=2012].R.mean():+.3f} 2013-26 {t[t.t.dt.year>2012].R.mean():+.3f} | last 3y {t[t.t.dt.year>=2024].R.mean():+.3f}")
    pool = []
    for k in ("SPX", "NDX", "DJI", "RUT"):
        d = F.D[k]; nxt = pd.Series(d.index, index=d.index).shift(-1); pool += [x[2] for x in run2(k, nxt.isin(F.D[k].index[F.D[k].index.isin(FOMC)]) , 1, None, 1)]
    # random benchmark: any day -> next day, same markets
    rnd = []
    for k in ("SPX", "NDX", "DJI", "RUT"):
        d = F.D[k]; rnd += [x[2] for x in run2(k, pd.Series(True, index=d.index), 1, None, 1)]
    print(f"  pooled {stats(pool)} vs every day {stats(rnd)}")

    print("== 2. Daily books: trades with an event inside the hold vs without")
    up = lambda d: d.close > d.close.rolling(200).mean(); ma = lambda c, n: c.rolling(n).mean()
    BOOKS = {
      "RSI2 #51": (F.IXG, lambda d: (up(d) & (F.rsi(d.close, 2) < 5) & (d.close < ma(d.close, 5)), d.close > ma(d.close, 5), 10, 3.0, "C")),
      "Stoch #61": (F.IXG, lambda d: (lambda K: (up(d) & (K < 10), K > 50, 10, 3.0, "C"))(100 * (d.close - d.low.rolling(5).min()) / (d.high.rolling(5).max() - d.low.rolling(5).min()))),
      "Double 7s": (F.IXG, lambda d: (up(d) & (d.close <= d.close.rolling(7).min()), d.close >= d.close.rolling(7).max(), 15, 3.0, "C")),
      "Turn of quarter": (F.IX, lambda d: (pd.Series(d.index == (d.index + pd.offsets.BQuarterEnd(0)), index=d.index), None, 3, 5.0, "C")),
      "US close -> Europe": (["DAX", "FTSE"], lambda d: (((lambda s: ((s.close - s.low) / (s.high - s.low) > 0.9) & (s.close.pct_change() > 0.01))(F.D["SPX"])).shift(1).reindex(d.index).fillna(False), None, 1, 2.0, "OC")),
    }
    for name, (mk, fn) in BOOKS.items():
        rows = []
        for k in mk:
            d = F.D[k]; e, x, md, st, how = fn(d); nf = nfp_days(d.index)
            for t0, t1, R in run2(k, e, 1, x, md, st, how):
                lo = t0 + pd.Timedelta(days=1) if how == "C" else t0
                rows.append((t0, R, bool(((FOMC >= lo) & (FOMC <= t1)).any()), bool(((nf >= lo) & (nf <= t1)).any())))
        t = pd.DataFrame(rows, columns=["t", "R", "fomc", "nfp"]); t["ev"] = t.fomc | t.nfp
        print(f"  {name:20s} all {stats(t.R)}")
        for c in ("fomc", "nfp", "ev"):
            print(f"      {c:4s} inside: {stats(t[t[c]].R)} | none: {stats(t[~t[c]].R)}")
        # walk-forward switch: skip event trades in year Y only if event trades were worse than non-event trades in all earlier years (>= 8 years, >= 15 trades)
        t["y"] = t.t.dt.year; keep_tot = all_tot = 0.0
        for Y in sorted(t.y.unique()):
            past = t[t.y < Y]; cur = t[t.y == Y]; all_tot += cur.R.sum()
            skip = len(past.y.unique()) >= 8 and past.ev.sum() >= 15 and past[past.ev].R.mean() < 0 and past[past.ev].R.mean() < past[~past.ev].R.mean()
            keep_tot += cur[~cur.ev].R.sum() if skip else cur.R.sum()
        print(f"      walk-forward 'skip trades with an event inside': out-of-sample total {all_tot:+.1f} -> {keep_tot:+.1f}")

def exante(name, mk, fn, horizons=(1, 2, 3, 5)):
    """Known at entry: is a scheduled FOMC / jobs day within the next h trading days? (no duration bias)"""
    rows = []
    for k in mk:
        d = F.D[k]; e, x, md, st, how = fn(d); idx = d.index; nf = nfp_days(idx); pos = {t: i for i, t in enumerate(idx)}
        ev = idx.isin(FOMC) | idx.isin(nf); evi = np.where(ev)[0]
        for t0, t1, R in run2(k, e, 1, x, md, st, how):
            i = pos[t0]; first = i + (1 if how == "C" else 0); nxt = evi[evi >= first]; gap = (nxt[0] - first + 1) if len(nxt) else 999
            rows.append((t0, R, gap))
    t = pd.DataFrame(rows, columns=["t", "R", "gap"]); t["y"] = t.t.dt.year
    out = [f"  {name:20s} all {stats(t.R)}"]
    for h in horizons:
        a, b = t[t.gap <= h], t[t.gap > h]
        tot = all_ = 0.0
        for Y in sorted(t.y.unique()):
            past = t[t.y < Y]; cur = t[t.y == Y]; all_ += cur.R.sum(); pa = past[past.gap <= h]
            skip = past.y.nunique() >= 8 and len(pa) >= 15 and pa.R.mean() < 0 and pa.R.mean() < past[past.gap > h].R.mean()
            tot += cur[cur.gap > h].R.sum() if skip else cur.R.sum()
        out.append(f"      event within {h}d of entry: {stats(a.R)} | not: {stats(b.R)} | halves {a[a.y<=2012].R.mean():+.3f}/{a[a.y>2012].R.mean():+.3f} | WF skip: {all_:+.1f} -> {tot:+.1f}")
    print("\n".join(out), flush=True); return t

if __name__ == "__main__":
    print("== 3. Known at entry (no duration bias)")
    for name, (mk, fn) in BOOKS.items(): exante(name, mk, fn)
