"""Doc 191 — spike engines, iteration on development (A 2020-21) only, judged once on B (2025-26).
The study found the NEXT 15-min bar decides: pulls back -> 86% retrace >=50% of the spike (both periods); extends >0.25 -> 76-77% extend >=0.5.
SNAP: next bar closes back against the spike -> enter at its close against the spike. Grid: target retrace of spike bar {0.5,0.75,1.0},
      stop beyond the extreme + {0, 0.1, 0.25} x spike range. 2h time exit / session end.
CONT: next bar extends the extreme by > X x range and closes beyond the spike close -> enter at its close with the spike.
      Grid: X {0.1,0.25}, stop {spike midpoint, next bar's opposite extreme}, target {0.5,1.0} x range beyond entry."""
import itertools, numpy as np, pandas as pd
exec(open("src/spike_shape_test.py").read().split("log(\"SPIKE SHAPE")[0].replace("runs/spike_shape_test.txt", "runs/spike_engine_iter.txt"))
qa, qb = prep(A), prep(B)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    SA = study(qa, "A"); SB = study(qb, "B")
OUT.seek(0); OUT.truncate()
def run(q, S, kind, p):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; day = q.day.values; res = []
    def walk(i0, side, entry, stop, tgt, n=8):
        for k in range(i0 + 1, min(i0 + 1 + n, len(q))):
            if day[k] != day[i0]: return side * (C[k - 1] - entry) - COST
            if (side == 1 and L[k] <= stop) or (side == -1 and H[k] >= stop): return side * (stop - entry) - COST - 0.5
            if (side == 1 and H[k] >= tgt) or (side == -1 and L[k] <= tgt): return side * (tgt - entry) - COST
        k = min(i0 + n, len(q) - 1); return side * (C[k] - entry) - COST
    for row in S.itertuples():
        i, s, r = row.i, row.s, row.r; nx = i + 1
        if day[nx] != day[i]: continue
        if kind == "snap":
            tr, sb = p
            if not (s * (C[nx] - C[i]) < 0 and row.next_ext <= 0.25): continue
            side = -s; e = C[nx]; xt = max(H[i], H[nx]) if s == 1 else min(L[i], L[nx]); stop = xt + s * sb * r
            tgt = (H[i] - tr * r) if s == 1 else (L[i] + tr * r)
            if side * (tgt - e) <= 0 or abs(stop - e) <= 0: continue
            res.append((row.t, walk(nx, side, e, stop, tgt) / abs(stop - e), walk(nx, side, e, stop, tgt)))
        else:
            X, sm, tg = p
            if not (row.next_ext > X and s * (C[nx] - C[i]) > 0): continue
            side = s; e = C[nx]; stop = (H[i] + L[i]) / 2 if sm == "mid" else (L[nx] if s == 1 else H[nx]); tgt = e + s * tg * r
            if side * (e - stop) <= 0: continue
            res.append((row.t, walk(nx, side, e, stop, tgt) / abs(e - stop), walk(nx, side, e, stop, tgt)))
    return pd.DataFrame(res, columns=["t", "R", "pts"])
def fmt(X): return f"n{len(X):3} {X.R.mean():+.2f}R win {100*(X.R>0).mean():3.0f}% pts {X.pts.sum():+7.0f}" if len(X) else "none"
for kind, grid in (("snap", list(itertools.product((0.5, 0.75, 1.0), (0.0, 0.1, 0.25)))), ("cont", list(itertools.product((0.1, 0.25), ("mid", "nextbar"), (0.5, 1.0))))):
    log(f"\n{kind.upper()} — development grid (A), holdout (B) printed alongside but not used to choose")
    best = None
    for p in grid:
        XA = run(qa, SA, kind, p); XB = run(qb, SB, kind, p)
        log(f"  {str(p):22} A {fmt(XA)} || B {fmt(XB)}")
        if len(XA) >= 20 and (best is None or XA.R.mean() > best[1]): best = (p, XA.R.mean())
    XB = run(qb, SB, kind, best[0]); log(f"  CHOSEN on A: {best[0]} -> holdout B {fmt(XB)}")
