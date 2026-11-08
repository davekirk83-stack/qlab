"""Doc 191 — SPIKE SHAPE on US Tech 100 (cash session 09:30-16:00 NY). An ABNORMAL 15-min bar = range >= 3x the mean 15-min range
of the prior 5 sessions. Period A (development): Jan 2020 - Aug 2021 (Dukascopy, includes the Covid crash). Period B (holdout): Nov 2025 - Nov 2026.
1) Shape: in the next 2 hours, how far does it EXTEND beyond the spike extreme (in spike ranges) vs how far does it SNAP BACK (retrace of the spike bar)?
2) What separates snap-backs from continuations: close position in the bar (wick vs full body), next-bar behaviour, VWAP distance, time of day.
3) ENGINES (1 pt cost, stops slip 0.5 pt):
   SNAP  fade after the climax signature: the next 15-min bar does NOT extend the extreme by more than 0.25 spike range and closes back inside
         the spike bar -> enter against the spike at that close; stop = spike extreme + 0.25 x spike range; target = 50% retrace of the spike bar;
         exit after 2h. Ladder variant: half at signal, half at a retest of the extreme (stop unchanged).
   CONT  follow when the spike closed in its last 20% and the next bar extends it -> enter that close; stop = spike midpoint; target 1x spike range; 2h.
"""
import numpy as np, pandas as pd
OUT = open("runs/spike_shape_test.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def load(f, start):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); d = d[~d.index.duplicated()].sort_index()
    return d[d.index >= start]
A = load("data_long/nq_5m_2020_21.csv", "2020-01-01"); B = load("data_nq_cache/nq_5m.csv", "2025-10-15")
COST = 1.0
def prep(d):
    lt = d.index.tz_convert("America/New_York"); mins = lt.hour * 60 + lt.minute
    d = d[(mins >= 570) & (mins < 960)].copy(); d["day"] = d.index.tz_convert("America/New_York").date
    q = d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    q["day"] = q.index.tz_convert("America/New_York").date; q["rng"] = q.high - q.low
    dm = q.groupby("day").rng.mean(); q["ref"] = q.day.map(dm.shift(1).rolling(5).mean())
    tp = (q.high + q.low + q.close) / 3; q["vwap"] = tp.groupby(q.day).cumsum() / q.groupby("day").cumcount().add(1)
    q["min"] = q.index.tz_convert("America/New_York").hour * 60 + q.index.tz_convert("America/New_York").minute - 570
    return q
def study(q, tag):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; day = q.day.values
    rows = []
    for i in range(len(q) - 9):
        r = q.rng.iloc[i]; ref = q.ref.iloc[i]
        if not (ref > 0 and r >= 3 * ref): continue
        s = 1 if C[i] > O[i] else -1          # spike direction
        j1 = [k for k in range(i + 1, i + 9) if day[k] == day[i]]
        if len(j1) < 2: continue
        ext = (max(H[j1]) - H[i]) / r if s == 1 else (L[i] - min(L[j1])) / r
        snap = (H[i] - min(L[j1])) / r if s == 1 else (max(H[j1]) - L[i]) / r
        cpos = (C[i] - L[i]) / r if s == 1 else (H[i] - C[i]) / r   # 1 = closed at the extreme in the spike's direction
        nx = j1[0]; next_ext = ((H[nx] - H[i]) if s == 1 else (L[i] - L[nx])) / r; next_inside = (C[nx] < H[i] - 0.0) if s == 1 else (C[nx] > L[i])
        nback = (s * (C[nx] - C[i])) < 0
        vd = s * (C[i] - q.vwap.iloc[i]) / r
        rows.append(dict(t=q.index[i], s=s, r=r, ext=max(ext, 0), snap=snap, cpos=cpos, next_ext=next_ext, nback=nback, vd=vd, mn=q["min"].iloc[i], i=i))
    S = pd.DataFrame(rows)
    log(f"\n[{tag}] abnormal 15-min bars: {len(S)} on {q.day.nunique()} sessions (up {int((S.s==1).sum())}, down {int((S.s==-1).sum())})")
    log(f"  next 2h: extends beyond the extreme median {S.ext.median():.2f} spike-ranges (>=0.5 in {100*(S.ext>=.5).mean():.0f}%); retraces >=50% of the spike bar in {100*(S.snap>=.5).mean():.0f}%, fully in {100*(S.snap>=1).mean():.0f}%")
    for lab, g in (("closed in its last 20% (no wick)", S[S.cpos >= .8]), ("closed with a wick (<60%)", S[S.cpos < .6]),
                   ("next bar pulls back", S[S.nback]), ("next bar extends >0.25", S[S.next_ext > .25]),
                   ("first hour", S[S.mn < 60]), ("after first hour", S[S.mn >= 60]),
                   ("far from VWAP (>1 range)", S[S.vd > 1]), ("near VWAP (<0.5)", S[S.vd < .5]), ("UP spikes", S[S.s == 1]), ("DOWN spikes", S[S.s == -1])):
        if len(g): log(f"    {lab:34} n{len(g):3}: snap>=50% {100*(g.snap>=.5).mean():3.0f}%  extends>=0.5 {100*(g.ext>=.5).mean():3.0f}%")
    return S
def engines(q, S, tag):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; day = q.day.values
    def walk(i0, side, entry, stop, tgt, n=8):
        for k in range(i0 + 1, min(i0 + 1 + n, len(q))):
            if day[k] != day[i0]: return side * (C[k - 1] - entry) - COST
            if (side == 1 and L[k] <= stop) or (side == -1 and H[k] >= stop): return side * (stop - entry) - COST - 0.5
            if (side == 1 and H[k] >= tgt) or (side == -1 and L[k] <= tgt): return side * (tgt - entry) - COST
        k = min(i0 + n, len(q) - 1); return side * (C[k] - entry) - COST
    snap, ladder, cont = [], [], []
    for row in S.itertuples():
        i, s, r = row.i, row.s, row.r; nx = i + 1
        if day[nx] != day[i]: continue
        ext_ok = row.next_ext <= 0.25; inside = (C[nx] < H[i]) if s == 1 else (C[nx] > L[i])
        if ext_ok and inside:
            side = -s; e = C[nx]; xt = max(H[i], H[nx]) if s == 1 else min(L[i], L[nx]); stop = xt + s * 0.25 * r
            tgt = (H[i] - 0.5 * r) if s == 1 else (L[i] + 0.5 * r)
            if side * (tgt - e) > 0:
                p1 = walk(nx, side, e, stop, tgt); snap.append((row.t, p1 / abs(stop - e)))
                # ladder: second half at a retest of the extreme within the 2h
                p2 = None
                for k in range(nx + 1, min(nx + 9, len(q))):
                    if day[k] != day[i]: break
                    if (s == 1 and H[k] >= xt) or (s == -1 and L[k] <= xt):
                        p2 = walk(k, side, xt, stop, tgt) if not ((s == 1 and H[k] >= stop) or (s == -1 and L[k] <= stop)) else (side * (stop - xt) - COST - .5)
                        break
                avg_risk = abs(stop - e) / 2 + (abs(stop - xt) / 2 if p2 is not None else 0)
                ladder.append((row.t, (p1 / 2 + (p2 / 2 if p2 is not None else 0)) / max(abs(stop - e), 1e-9)))
        if row.cpos >= .8 and row.next_ext > 0:
            side = s; e = C[nx]; stop = (H[i] + L[i]) / 2; tgt = e + s * r
            if side * (e - stop) > 0: cont.append((row.t, walk(nx, side, e, stop, tgt) / abs(e - stop)))
    for lab, X in (("SNAP fade after climax signature", snap), ("SNAP as a 2-rung ladder", ladder), ("CONT follow-through", cont)):
        X = pd.DataFrame(X, columns=["t", "R"])
        log(f"  {tag} {lab:34} n{len(X):3} mean {X.R.mean():+.2f}R win {100*(X.R>0).mean():.0f}% total {X.R.sum():+.1f}R" if len(X) else f"  {tag} {lab}: none")
log("SPIKE SHAPE — US Tech 100, abnormal 15-min bars (>= 3x the prior-5-session mean 15-min range), cash session")
qa, qb = prep(A), prep(B)
SA = study(qa, "A 2020-21 development"); SB = study(qb, "B 2025-26 holdout")
log("\nENGINES (R = multiples of the initial risk, after costs)")
engines(qa, SA, "A"); engines(qb, SB, "B")
