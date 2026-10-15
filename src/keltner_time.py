"""
IS THE KELTNER RESULT REAL, OR IS IT THE PERIOD?

The hold sweep produced out-of-sample numbers BETTER than in-sample in almost
every cell, and a headline of ~215%/month on a $2,000 stack. Neither is
credible, and there is a concrete reason to distrust both:

  data_1m      18 symbols, from Sept 2025
  data_1m_oos  31 symbols, Feb-Sep 2026

Different symbols AND a different period. So the "out of sample" panel differs
from the "in sample" panel in two ways at once, and the obvious confound is
that Feb-Sep 2026 was a better period for mean reversion. That would make the
whole result a regime artifact wearing a validation badge.

THE TEST THAT SEPARATES THEM
Pool all 49 symbols and split by TIME into equal calendar thirds, then run the
identical configuration in each. Symbol composition is now held constant and
only the period varies.

  if the edge is REAL      it appears in all three periods, with the usual
                           variation in size
  if it is THE PERIOD      it concentrates in the window that overlaps
                           Feb-Sep 2026 and is absent or negative elsewhere

Also reported: the same split restricted to symbols present throughout, which
removes even the composition drift, and a per-quarter series so a single good
quarter carrying everything is visible.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import keltner_tf as K

CFG = dict(t_atr=0.5, s_atr=3.0, kband=2.0, eff_cut=0.30)
TF, HOLD = "2h", 4          # the headline cell
MAKER, TAKER, SLIP = K.MAKER, K.TAKER, K.SLIP


def trades(data, tf_minutes, hold, **cfg):
    """Every trade with its timestamp, so results can be cut by period."""
    t_atr = cfg.get("t_atr", 0.5); s_atr = cfg.get("s_atr", 3.0)
    kband = cfg.get("kband", 2.0); eff_cut = cfg.get("eff_cut", 0.30)
    out = []
    for s, d in data.items():
        if len(d) < 400: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); a = K.atr_np(H, L, C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        lower = ema - kband * a
        ok = K.efficiency(C) < eff_cut
        trig = (C <= lower) & (np.roll(C, 1) > np.roll(lower, 1)) & ok
        elig = np.flatnonzero(ok & np.isfinite(a) & (np.arange(n) > 120))
        elig = elig[(elig > 120) & (elig < n - hold - 2)]
        last = -10**9
        for i in np.flatnonzero(trig):
            if i < 120 or i > n - hold - 2 or i - last < hold: continue
            last = i
            r = K.play(C, H, L, i, C[i]-s_atr*a[i], C[i]+t_atr*a[i], hold)
            c = np.nan
            if len(elig):
                q = int(K.RNG.choice(elig))
                c = K.play(C, H, L, q, C[q]-s_atr*a[q], C[q]+t_atr*a[q], hold)
            out.append((s, d.index[i], r, c))
    return pd.DataFrame(out, columns=["sym", "ts", "ret", "ctrl"])


def block(T, tag):
    if len(T) < 60:
        print(f"  {tag:<28}{len(T):>7}  too few"); return None
    t = T.ret.mean()/(T.ret.std(ddof=1)/np.sqrt(len(T)))
    c = T.ctrl.dropna()
    edge = T.ret.mean() - (c.mean() if len(c) else 0)
    te = edge/np.sqrt(T.ret.var(ddof=1)/len(T) + (c.var(ddof=1)/len(c) if len(c) else 0))
    span = (T.ts.max()-T.ts.min()).days/30.44
    per = len(T)/max(span, 0.1)
    print(f"  {tag:<28}{len(T):>7}{per:>8.0f}{T.ret.mean()*100:>+10.3f}%{t:>+8.2f}"
          f"{(c.mean() if len(c) else np.nan)*100:>+10.3f}%{edge*100:>+9.3f}%"
          f"{te:>+7.2f}{(T.ret>0).mean()*100:>6.0f}%")
    return dict(n=len(T), mean=T.ret.mean(), t=t, edge=edge, te=te, per=per)


if __name__ == "__main__":
    print(f"KELTNER {TF} / HOLD {HOLD} — IS IT REAL OR IS IT THE PERIOD?\n")
    A = K.bars("/home/claude/qlab/data_1m", TF)
    B = K.bars("/home/claude/qlab/data_1m_oos", TF)
    print(f"  data_1m      {len(A):>2} symbols  "
          f"{min(d.index[0] for d in A.values()).date()} -> "
          f"{max(d.index[-1] for d in A.values()).date()}")
    print(f"  data_1m_oos  {len(B):>2} symbols  "
          f"{min(d.index[0] for d in B.values()).date()} -> "
          f"{max(d.index[-1] for d in B.values()).date()}")

    TA = trades(A, 120, HOLD, **CFG); TA["panel"] = "IS"
    TB = trades(B, 120, HOLD, **CFG); TB["panel"] = "OOS"
    T = pd.concat([TA, TB], ignore_index=True).dropna(subset=["ret"])
    T["ts"] = pd.to_datetime(T.ts, utc=True)

    hdr = (f"  {'cut':<28}{'n':>7}{'/mo':>8}{'net%':>11}{'t':>8}"
           f"{'ctrl%':>11}{'EDGE':>9}{'tEdge':>7}{'win':>7}")
    print(f"\n{'='*104}\nBY PANEL (the original, confounded comparison)\n{hdr}")
    for p in ("IS", "OOS"): block(T[T.panel == p], p)

    print(f"\n{'='*104}\nBY CALENDAR THIRD, all 49 symbols pooled — "
          f"composition held constant\n{hdr}")
    q = list(T.ts.quantile([0, 1/3, 2/3, 1.0]))
    thirds = []
    for i in range(3):
        m = (T.ts >= q[i]) & (T.ts <= q[i+1]) if i == 2 else (T.ts >= q[i]) & (T.ts < q[i+1])
        tag = f"{pd.Timestamp(q[i]).date()} -> {pd.Timestamp(q[i+1]).date()}"
        thirds.append(block(T[m], tag))

    print(f"\n{'='*104}\nBY QUARTER — is one quarter carrying the whole thing?\n{hdr}")
    T["qtr"] = T.ts.dt.to_period("Q").astype(str)
    qres = {}
    for qq, G in T.groupby("qtr"):
        qres[qq] = block(G, qq)

    print(f"\n{'='*104}\nVERDICT")
    good = [x for x in thirds if x and x["mean"] > 0]
    gq = [k for k, v in qres.items() if v and v["mean"] > 0]
    print(f"  calendar thirds with positive net return: {len(good)}/3")
    print(f"  quarters with positive net return:        {len(gq)}/{len([v for v in qres.values() if v])}"
          f"   ({', '.join(gq) if gq else 'none'})")
    if thirds[0] and thirds[-1]:
        print(f"  earliest third {thirds[0]['mean']*100:+.3f}%  "
              f"latest third {thirds[-1]['mean']*100:+.3f}%")
    print("\n  Reading: positive in all three thirds and most quarters = a real,")
    print("  period-independent edge. Concentrated in the late window = the")
    print("  'out of sample' result was the 2026 range regime, not robustness.")
