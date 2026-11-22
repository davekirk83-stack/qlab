"""DK 22 Nov 09:35: "Consider which aspects work, which don't, and what can be improved." Trendlines, BTC 1h and 4h, 2021-2026.
Variants: (1) trade only WITH the 4h trend; (2) confluence: line touch at a horizontal level (prior swing low/high within 0.3 ATR or a
round 1,000); (3) exits: 1R target / 1 ATR stop / 12-bar time exit; (4) line BREAK continuation after 3+ touches. Random control alongside."""
import sys; sys.path.insert(0, "src/research")
import numpy as np, pandas as pd
from channel_lines import bars, atr, pivots, sim
def events(tf, k):
    d = bars(tf); o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; A = atr(d); n = len(c)
    e50 = d.c.ewm(span=50, adjust=False).mean().values
    sl = pivots(l, k, True); sh = pivots(h, k, False)
    T, B = [], []
    for side in (1, -1):
        piv = sl if side > 0 else sh; src = l if side > 0 else h
        for a, b in zip(piv[:-1], piv[1:]):
            if b - a < 2*k or not ((src[b] > src[a]) if side > 0 else (src[b] < src[a])): continue
            slope = (src[b]-src[a])/(b-a); line = lambda t: src[a] + slope*(t-a); seg = np.arange(a, b+1)
            if side > 0 and (c[seg] < line(seg) - 0.1*A[seg]).any(): continue
            if side < 0 and (c[seg] > line(seg) + 0.1*A[seg]).any(): continue
            touch, t, last = 2, b + k + 1, b
            while t < n - 50 and t < b + 40*k:
                L, at = line(t), A[t]
                if not np.isfinite(at): break
                if (c[t] < L - 0.25*at) if side > 0 else (c[t] > L + 0.25*at):
                    B.append(dict(t=t, side=-side, touches=touch, L=L, a_=at)); break
                if ((l[t] <= L + 0.15*at) if side > 0 else (h[t] >= L - 0.15*at)) and t - last >= k:
                    touch += 1; last = t
                    if (c[t] > L) if side > 0 else (c[t] < L):
                        # confluence: a prior swing point within 0.3 ATR of the line value, or a round 1,000
                        prior = piv[(piv < t - 2*k) & (piv > t - 300)]
                        conf = bool((np.abs(src[prior] - L) < 0.3*at).any()) or abs(L - round(L/1000)*1000) < 0.2*at
                        T.append(dict(t=t, side=side, touch=touch, L=L, a_=at, trend=np.sign(c[t]-e50[t]) == side, conf=conf))
                t += 1
    return d, pd.DataFrame(T), pd.DataFrame(B)
out = []
for tf, k in (("1h", 5), ("4h", 3)):
    d, T, B = events(tf, k); o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values
    def res(df, stopx, tgtR, H, which="touch"):
        r = []
        for _, e in df.iterrows():
            i = int(e.t); s = int(e.side)
            stop = e.L - s*stopx*e.a_
            risk = abs(c[i]-stop)
            if risk <= 0: continue
            r.append(sim(o, h, l, c, i, s, stop, c[i] + s*tgtR*risk, H))
        return np.array(r)
    def line(name, r, df):
        if len(r) < 20: return f"  {name:60} n{len(r)}"
        yrs = pd.Series(r, index=d.index[df.t.astype(int).values[:len(r)]]).groupby(lambda x: x.year).mean()
        hf = len(r)//2
        return f"  {name:60} n{len(r):4} mean {100*r.mean():+.3f}% win {(r>0).mean():.0%} | halves {100*r[:hf].mean():+.3f}/{100*r[hf:].mean():+.3f} | yrs+ {(yrs>0).sum()}/{len(yrs)}"
    out.append(f"== BTC {tf}: {len(T)} touches, {len(B)} breaks")
    T34 = T[T.touch.isin([3, 4, 5])]
    for nm, df in (("touches #3-5, all", T34), ("  with the 4h... (price on the line's side of EMA50)", T34[T34.trend]),
                   ("  confluence with a prior swing level / round 1,000", T34[T34.conf]), ("  trend + confluence", T34[T34.trend & T34.conf])):
        for stopx, tgt, H, lab in ((0.5, 2, 48, "stop .5ATR, 2R"), (1.0, 1, 24, "stop 1ATR, 1R, 24 bars")):
            out.append(line(f"{nm} [{lab}]", res(df, stopx, tgt, H), df))
    B3 = B[B.touches >= 3]
    for stopx, tgt, H, lab in ((0.75, 2, 48, "stop back inside .75ATR, 2R"), (1.0, 1.5, 24, "stop 1ATR, 1.5R, 24 bars")):
        out.append(line(f"BREAK of a 3+ touch line, trade the break [{lab}]", res(B3, stopx, tgt, H, "break"), B3))
    # random control, same exits
    rng = np.random.default_rng(3); rr = []
    for i in rng.integers(300, len(c)-60, 1500):
        s = rng.choice([1, -1]); at = atr(d)[i]; stop = c[i]-s*1.0*at; rr.append(sim(o, h, l, c, i, s, stop, c[i]+s*1*at, 24))
    out.append(f"  random entries [stop 1ATR, 1R, 24 bars]: mean {100*np.mean(rr):+.3f}% win {np.mean(np.array(rr)>0):.0%}")
open("runs/research/channel_lines_improve.txt", "w").write("\n".join(out)); print("\n".join(out))

# DK's actual use on 19 Nov: a sharp drop INTO a rising line (a flush into support), then the bounce. Context: the 6 bars before the touch
# moved >= 1.5 ATR toward the line.
out2 = []
for tf, k in (("1h", 5), ("4h", 3)):
    d, T, B = events(tf, k); o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values
    T = T[T.touch >= 3].copy()
    T["into"] = [(c[int(t)-6] - c[int(t)]) * s / a for t, s, a in zip(T.t, T.side, T.a_)]
    for thr in (0, 1.5, 3.0):
        g = T[T.into >= thr]
        for stopx, tgt, H, lab in ((1.0, 1, 24, "stop 1ATR, 1R"), (1.0, 2, 48, "stop 1ATR, 2R")):
            r = []
            for _, e in g.iterrows():
                i = int(e.t); s = int(e.side); stop = e.L - s*stopx*e.a_; risk = abs(c[i]-stop)
                if risk > 0: r.append(sim(o, h, l, c, i, s, stop, c[i]+s*tgt*risk, H))
            r = np.array(r); hf = len(r)//2
            if len(r) >= 15:
                out2.append(f"  {tf} touch #3+ after a move of >= {thr} ATR into the line [{lab}]: n{len(r)} mean {100*r.mean():+.3f}% win {(r>0).mean():.0%} | halves {100*r[:hf].mean():+.3f}/{100*r[hf:].mean():+.3f}")
open("runs/research/channel_lines_improve.txt", "a").write("\n\n== Flush INTO the line\n" + "\n".join(out2)); print("\n".join(out2))

# Turn it round: a hard move INTO a well-touched line tends to go THROUGH it. Trade WITH the move at the touch.
out3 = []
for tf, k in (("1h", 5), ("4h", 3)):
    d, T, B = events(tf, k); o, h, l, c = d.o.values, d.h.values, d.l.values, d.c.values; A_ = atr(d)
    T = T[T.touch >= 3].copy(); T["into"] = [(c[int(t)-6] - c[int(t)]) * s / a for t, s, a in zip(T.t, T.side, T.a_)]
    for thr in (1.5, 2.0, 3.0):
        g = T[T.into >= thr]
        for stopx, tgt, H, lab in ((1.0, 1, 24, "stop 1ATR, 1R"), (1.0, 2, 48, "stop 1ATR, 2R"), (1.5, 2, 48, "stop 1.5ATR, 2R")):
            r = []; ts = []
            for _, e in g.iterrows():
                i = int(e.t); s = -int(e.side); stop = c[i] - s*stopx*A_[i]; risk = abs(c[i]-stop)
                if risk > 0: r.append(sim(o, h, l, c, i, s, stop, c[i]+s*tgt*risk, H)); ts.append(d.index[i])
            r = np.array(r); hf = len(r)//2
            if len(r) >= 15:
                yrs = pd.Series(r, index=ts).groupby(lambda x: x.year).mean()
                out3.append(f"  {tf} move >= {thr} ATR into a 3+ touch line, trade WITH the move [{lab}]: n{len(r)} mean {100*r.mean():+.3f}% win {(r>0).mean():.0%} | halves {100*r[:hf].mean():+.3f}/{100*r[hf:].mean():+.3f} | yrs+ {(yrs>0).sum()}/{len(yrs)}")
open("runs/research/channel_lines_improve.txt", "a").write("\n\n== Trade WITH a hard move into the line\n" + "\n".join(out3)); print("\n".join(out3))
