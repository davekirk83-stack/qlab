"""
EXITS AT THE OPPOSING SIDE'S PAIN — DK's reframing, applied to a live book.

DK, 2026-10-15:
  "Stop hunting is just 'our' trade taking profit at the point where the
   'other party' takes a loss at their liquidation or stop loss."
  "Moves always go for liquidity, otherwise they would just stay at
   equilibrium. When entering a trade you never want to market buy the
   equilibrium. You want to buy and sell the extremities when trading."

WHY THE FIRST FOUR TESTS KEPT FAILING
They all asked a forecasting question: does liquidity predict WHERE PRICE GOES?
That is not the claim. The claim is about WHERE YOU TRANSACT. Liquidity is not
a direction signal, it is a placement rule -- enter at an extremity, exit at the
opposite extremity, which is the point where the other side is forced out.

Cascade v3 (doc 56, registered) already obeys the entry half of this without
having been designed for it: it buys after a 3% flush, which is an extremity,
on a resting bid rather than a market order. DK's rule says so explicitly.

But its EXIT is a fixed +1.5%, a number with no relationship to anybody's pain.
Doc 44 found exits moved results more than entries did. So this is the test.

THE EXIT VARIANTS, all against the registered baseline
  fixed_1.5     the registered rule
  keltner_up    the upper Keltner band -- the statistical extremity, where
                short stops sit (doc 48: outer-band hits revert to mid 77-86%)
  prior_high    the swing high that the cascade broke -- where the trapped
                longs from before the flush are waiting to get out flat, and
                where the shorts who sold the break have their stops
  pocket        the nearest resting-size concentration above, from the real
                order book
  opp_extreme   the high of the bar that began the cascade -- full retrace

HONESTY
Same entries in every variant, so this is a PAIRED comparison -- the only thing
that changes is the exit. Same stop, same 60-bar cap, same costs (maker in,
maker out on target, taker + slippage on stop). Paired t on the per-trade
difference, not two independent means.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
DEPTH = "/home/claude/qlab/data_depth_full"
DROP, WIN = 0.03, 5
LIFT, HOLD, DEPTHB, MAXH = 0.008, 10, 0.004, 60
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def find_base(C, L, i, n, mw=60):
    lo = L[i]; k = i
    while k < min(i + mw, n - 1):
        if L[k] < lo: lo = L[k]
        if C[k] >= lo * (1 + LIFT): break
        k += 1
    if k >= min(i + mw, n - 1) or C[k] < lo * (1 + LIFT): return None
    j = k; h = 0
    while j < min(k + mw, n - 1):
        if L[j] < lo: return None
        h += 1
        if h >= HOLD: return j, lo
        j += 1
    return None


def run():
    rows = []
    for f in sorted(glob.glob(f"{M1}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        if len(d) < 50000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C)
        a = atr(H, L, C, 20)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        kelt_up = ema + 2 * a
        i = WIN
        while i < n - MAXH - 200:
            if C[i] / C[i - WIN] - 1 > -DROP:
                i += 1; continue
            casc_high = H[i - WIN:i + 1].max()
            prior_high = H[max(0, i - 600):i - WIN].max() if i > 600 else casc_high
            b = find_base(C, L, i, n)
            if b is None:
                i += WIN; continue
            j, lo = b
            bid = C[j] * (1 - DEPTHB)
            ent = None
            for k in range(j + 1, min(j + 30, n)):
                if L[k] <= bid: ent = k; break
            if ent is None or ent + MAXH >= n:
                i = j + 1; continue
            e = bid * (1 + MAKER)
            st = lo * 0.9995
            risk = e - st
            if risk <= 0:
                i = j + 1; continue
            tgts = dict(fixed_15=e * 1.015,
                        keltner_mid=max(ema[ent], e * 1.002),
                        keltner_1atr=max(ema[ent] + a[ent], e * 1.002),
                        keltner_up=max(kelt_up[ent], e * 1.002),
                        prior_high=max(prior_high, e * 1.002),
                        opp_extreme=max(casc_high, e * 1.002))
            out = {}
            for name, tg in tgts.items():
                r = None
                for k in range(ent + 1, ent + MAXH + 1):
                    if L[k] <= st:
                        r = -(1 + (TAKER + SLIP) * e / risk); break
                    if H[k] >= tg:
                        r = (tg * (1 - MAKER) - e) / risk; break
                if r is None:
                    r = (C[ent + MAXH] * (1 - TAKER) - e) / risk
                out[name] = r
            out.update(sym=s, ts=ent, rr=(tgts["fixed_15"] - e) / risk)
            rows.append(out)
            i = ent + MAXH
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("CASCADE v3 — same entries, different exits. DK's rule as a TP placement.\n")
    T = run()
    print(f"  {len(T)} trades, {T.sym.nunique()} symbols  (paired: identical entries)\n")
    base = T.fixed_15.values
    print(f"  {'exit rule':<16}{'mean R':>10}{'win':>8}{'t':>8}"
          f"{'vs registered':>16}{'paired t':>11}")
    for c in ("fixed_15", "keltner_mid", "keltner_1atr", "keltner_up", "prior_high", "opp_extreme"):
        v = T[c].values
        se = v.std(ddof=1) / np.sqrt(len(v))
        if c == "fixed_15":
            print(f"  {c:<16}{v.mean():>+10.3f}{(v>0).mean()*100:>7.1f}%"
                  f"{v.mean()/se:>+8.2f}{'— registered —':>16}")
            continue
        d = v - base
        sed = d.std(ddof=1) / np.sqrt(len(d))
        print(f"  {c:<16}{v.mean():>+10.3f}{(v>0).mean()*100:>7.1f}%"
              f"{v.mean()/se:>+8.2f}{d.mean():>+15.3f}R{d.mean()/sed:>+11.2f}")
    print(f"\n  median reward:risk of the registered 1.5% target: {T.rr.median():.2f}")
