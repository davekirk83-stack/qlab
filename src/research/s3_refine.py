"""DK 27 Nov 22:33: "Keep working on this to refine it. Ways to maximise wins and minimise losses etc".
S3 base (doc 279): RSI(2) < 10 in DK v2's context, buy the close, sell the first close above the 5-day mean, 10-day limit.
One change at a time, each with a reason. Judged per asset class (US stocks, indices, commodities, crypto) on: mean, both halves,
profit factor, worst trade and share of trades worse than -10% (the tail). A change is 'kept' only if it raises the mean (or holds it)
AND does not worsen the tail, in both halves, in most classes.
ENTRY
  ibs      close in the bottom 25% of the day's range (internal bar strength: selling exhausted into the close; long-documented on indices)
  crsi     cumulative RSI(2): 2-day sum < 35 instead of one day < 10 (Connors' own refinement - persistent selling)
  down3    at least 3 lower closes in a row (DK: "bid in small chunks over a period" - selling that has run its course)
  rsi5     RSI(2) < 5 (deeper)
  scale    DK's ladder: half at the signal close, the other half at the next close if it is lower ("add incrementally"); exits as base
EXIT
  rsi70    sell when RSI(2) > 70 (Connors alternative - lets the bounce run)
  upclose  sell on the first up close (bank the first bounce: DK "should have taken profit on the bounce")
  ma10     sell the first close above the 10-day mean (longer bounce)
  t5       5-day limit instead of 10 (dead trades cost time)
  part     sell half at the first up close, the rest at close > 5-day mean (DK's "took about a third off" style)
LOSS
  stop3    stop 3 daily sigmas under the entry (helped indices in doc 279)
  mkt      US stocks only when the S&P 500 itself is above its 200-day (avoid single-name buying in a bear market)
  nogap    skip if the signal day itself fell > 3 sigma (news/earnings shock, not a pullback - the -78% losers)
SIZE
  volsz    size each trade to equal risk (0.02 / daily sigma of the market, capped 1x) - reported as return on capital at risk"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import cross_asset_s3 as X

def prep2(D):
    D = X.prep(D); rng = (D.h - D.l).replace(0, np.nan); D["ibs"] = (D.c - D.l) / rng
    D["crsi"] = D.rsi2 + D.rsi2.shift(1); D["dn"] = (D.c < D.c.shift(1)).astype(int)
    D["dn3"] = (D.dn + D.dn.shift(1) + D.dn.shift(2)) == 3; D["ma10"] = D.c.rolling(10).mean()
    D["dret"] = D.c.pct_change(); D["sig_now"] = D.c.pct_change().rolling(14).std().shift(1); return D

def trades(D, cost, o, mkt=None):
    c, o_, l, h = D.c.values, D.o.values, D.l.values, D.h.values; ma5, ma10, r2 = D.ma5.values, D.ma10.values, D.rsi2.values
    ctx, sig, ibs, crsi, dn3, dret = D.ctx.values, D.sig.values, D.ibs.values, D.crsi.values, D.dn3.values, D.dret.values
    M = mkt.reindex(D.index).ffill().values if mkt is not None else None
    out = []; i = 210; n = len(D); lim = 5 if o.get("t5") else 10
    while i < n - 3:
        sigi = sig[i]
        ok = ctx[i] and np.isfinite(sigi) and sigi > 0
        if o.get("crsi"): ok = ok and crsi[i] < 35
        else: ok = ok and r2[i] < (5 if o.get("rsi5") else 10)
        if ok and o.get("ibs"): ok = ibs[i] < 0.25
        if ok and o.get("down3"): ok = bool(dn3[i])
        if ok and o.get("nogap"): ok = dret[i] > -3 * sigi
        if ok and M is not None: ok = bool(M[i])
        if not ok: i += 1; continue
        legs = [(c[i], 0.5 if o.get("scale") else 1.0)]; j = i + 1
        if o.get("scale") and c[j] < c[i]: legs.append((c[j], 0.5))
        st = c[i] * (1 - 3 * sigi) if o.get("stop3") else -1; pnl = 0.0; w_left = sum(w for _, w in legs); done = False; half_done = False
        while not done:
            if l[j] <= st:
                px = min(o_[j], st); pnl += sum(w * (px * (1 - cost) / (e * (1 + cost)) - 1) for e, w in legs) * (w_left / sum(w for _, w in legs)); done = True; break
            if o.get("part") and not half_done and c[j] > c[j - 1]:
                pnl += sum(w * (c[j] * (1 - cost) / (e * (1 + cost)) - 1) for e, w in legs) * 0.5 * (w_left / sum(w for _, w in legs)); w_left *= 0.5; half_done = True
            if o.get("rsi70"): ex = r2[j] > 70
            elif o.get("upclose"): ex = c[j] > c[j - 1]
            elif o.get("ma10"): ex = c[j] > ma10[j]
            else: ex = c[j] > ma5[j]
            if ex or j >= min(n - 1, i + lim):
                pnl += sum(w * (c[j] * (1 - cost) / (e * (1 + cost)) - 1) for e, w in legs) * (w_left / sum(w for _, w in legs)); done = True; break
            j += 1
            if o.get("scale") and j == i + 1 and c[j] < c[i]: pass
        r = pnl
        if o.get("volsz"): r = pnl * min(1.0, 0.02 / sigi)
        out.append((D.index[i], r)); i = j + 1
    return out

def stats(T):
    T = T.sort_values("t"); r = 100 * T.r; h = len(r) // 2; g, b = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=round((r > 0).mean(), 3), mean=round(r.mean(), 3), h1=round(r[:h].mean(), 3), h2=round(r[h:].mean(), 3), pf=round(g / b, 2) if b else np.nan,
                worst=round(r.min(), 1), tail10=round(100 * (r < -10).mean(), 2), p5=round(np.percentile(r, 5), 2))

if __name__ == "__main__":
    U = X.load(); spx = X.prep(U[("indices", "SPX")]); SPXUP = (spx.c > spx.c.rolling(200).mean())
    P = {k: prep2(v) for k, v in U.items() if k[0] in ("US stocks", "indices", "commodities", "crypto")}
    V = ["base", "ibs", "crsi", "down3", "rsi5", "scale", "rsi70", "upclose", "ma10", "t5", "part", "stop3", "mkt", "nogap", "volsz"]
    rows = []
    for v in V:
        o = {} if v in ("base", "mkt") else {v: True}; tt = []
        for (cls, s), D in P.items():
            cost = 0.0014 if cls == "crypto" else 0.001
            tt += [(cls, t, r) for t, r in trades(D, cost, o, SPXUP if (v == "mkt" and cls == "US stocks") else None)]
        T = pd.DataFrame(tt, columns=["cls", "t", "r"]); T["t"] = pd.to_datetime(T.t)
        for cls, g in T.groupby("cls"): rows.append(dict(change=v, cls=cls, **stats(g)))
        print(v, "done", flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/s3_refine.csv", index=False)
    pd.set_option("display.width", 250)
    for cls, g in R.groupby("cls"): print("\n==", cls); print(g.drop(columns="cls").to_string(index=False))
