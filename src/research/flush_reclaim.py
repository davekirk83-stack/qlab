"""Own idea 3: BTC flush-reclaim - buy the confirmation, not the falling knife. Doc 229: buying after a drop on the daily close earned ~+1%
in 7 days, the edge sat in bids AT the low; DK's own 21 Nov trigger was a reclaim after the sweep. Rule: after BTC falls >= D% from its
N-bar high, wait for the first bar that closes above the previous bar's high (the reclaim); buy at the next open; stop 0.5% under the
flush low; exits: target +T x risk, or the close back under the entry bar's low (failed reclaim), or a time limit. Daily (BTC 2015-26,
data_daily) and 4h (BTC 2021-26). Cost 0.2% round trip (Revolut X taker 0.09% x2 + slip). Results in R and in %."""
import warnings; warnings.filterwarnings("ignore")
import io, contextlib, os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src")
def daily():
    d = pd.read_csv("data_daily/BTC.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); return d[["open", "high", "low", "close"]].astype(float)
def h4():
    with contextlib.redirect_stdout(io.StringIO()): import liq_session_test as S
    d = pd.DataFrame({"open": S.O, "high": S.H, "low": S.L, "close": S.C}, index=pd.to_datetime(S.IX))
    return d.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def run(d, drop, look, tgt, tlimit, cost=0.002, ma=None):
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; n = len(C); out = []; i = look
    hh = pd.Series(H).rolling(look).max().values; m200 = pd.Series(C).rolling(ma).mean().values if ma else None
    while i < n - 2:
        if not (L[i] <= hh[i] * (1 - drop)): i += 1; continue
        # flush in progress: track the low; wait for the reclaim (close above the previous bar's high)
        lo = L[i]; j = i + 1; got = None
        while j < min(n - 1, i + look):
            lo = min(lo, L[j])
            if C[j] > H[j - 1] and (m200 is None or C[j] > m200[j] * 0 ): got = j; break
            j += 1
        if got is None: i = j; continue
        e = O[got + 1]; st = lo * 0.995; risk = e - st
        if risk <= e * 0.002: i = got + 1; continue
        x = None; fail = L[got]
        for q in range(got + 1, min(n, got + 1 + tlimit)):
            if L[q] <= st: x = st; break
            if H[q] >= e + tgt * risk: x = e + tgt * risk; break
            if q > got + 1 and C[q] < fail: x = C[q]; break
        if x is None: x = C[min(n - 1, got + tlimit)]
        out.append((d.index[got], (x - e) / risk - cost * e / risk, x / e - 1 - cost)); i = q + 1 if x is not None else got + 1
    return pd.DataFrame(out, columns=["t", "R", "pct"])
rows = []
for tf, d, looks, lims in (("daily", daily(), (10, 20), (10, 20)), ("4h", h4(), (18, 42), (18, 42))):
    for drop in (0.10, 0.15, 0.20):
        for look in looks:
            for tgt in (1.5, 2.0, 3.0):
                for lim in lims:
                    t = run(d, drop, look, tgt, lim)
                    if len(t) < 15: continue
                    h = len(t) // 2; y = t.groupby(t.t.dt.year).R.sum()
                    rows.append(dict(tf=tf, drop=drop, look=look, tgt_R=tgt, limit=lim, n=len(t), since=str(t.t.iloc[0].date()), win=round((t.R > 0).mean(), 2),
                                     meanR=round(t.R.mean(), 3), h1=round(t.R[:h].mean(), 3), h2=round(t.R[h:].mean(), 3), pct=round(100 * t.pct.mean(), 2),
                                     yrs_pos=f"{(y>0).sum()}/{len(y)}", last3y=round(t[t.t.dt.year >= 2024].R.mean(), 3)))
R = pd.DataFrame(rows); R.to_csv("runs/research/flush_reclaim.csv", index=False); pd.set_option("display.width", 250)
print(R.sort_values("meanR", ascending=False).head(14).to_string(index=False)); print("\nshare of variants with both halves > 0:", round(((R.h1 > 0) & (R.h2 > 0)).mean(), 2), "of", len(R))
print("median meanR by tf:", R.groupby("tf").meanR.median().to_dict())
