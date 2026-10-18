"""
THE GOLDEN CROSS WITH SCALED EXITS — follow-up to doc 80 (finding 148).

Doc 80: on 4-hour bars the golden-cross ENTRY is as informative as the death
cross (barrier race 65-67% vs 58-62% random) but a k*ATR trailing stop gives
the move back and every long cell loses. The entry works; the exit was wrong.
Test the same entries with the exits this project has already validated:

  scaled   stop 1.5 ATR under entry; TP1 +1.5 ATR takes 1/3 and moves the stop
           to breakeven (+cost); TP2 +3 ATR takes 1/3; the runner trails 3 ATR
           from the best price. DK's scale-out design (spec v1.1).
  hold N   no stop, exit at the close N bars later (N = 6, 12, 24, 48 = 1-8 days)
  trail 3  the doc-80 exit, for reference

Both sides, pairs 20/50 and 9/21, cross and anticipated. Random entry with the
identical exit as the control. 27 registered coins, 4-hour bars, 9bp round trip,
one row per episode, X_MIN_GAP 2 bars.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X
X.CAP = 180; X.X_MIN_GAP = 2
COST = X.COST
RNG = np.random.default_rng(7)


def scaled(C, H, L, a, i, side):
    """Return per-episode return on full initial notional."""
    n = len(C); e = C[i]; atr = a[i]; s = side
    stop = e - s*1.5*atr; tp1 = e + s*1.5*atr; tp2 = e + s*3*atr
    best = e; rem = 1.0; pnl = 0.0; stage = 0
    def pr(px): return s*(px/e - 1) - COST
    for j in range(i+1, min(i+X.CAP+1, n)):
        hi, lo = (H[j], L[j]) if s == 1 else (-L[j], -H[j])   # 'favourable' coords
        best = max(best, s*H[j] if s == 1 else -L[j]) if False else best
        fav = H[j] if s == 1 else L[j]; adv = L[j] if s == 1 else H[j]
        # worst-first: stop checked before targets within the bar
        if (s == 1 and adv <= stop) or (s == -1 and adv >= stop):
            return pnl + rem*pr(stop), j-i, "stop" if stage == 0 else "be"
        if stage == 0 and ((s == 1 and fav >= tp1) or (s == -1 and fav <= tp1)):
            pnl += (1/3)*pr(tp1); rem -= 1/3; stage = 1; stop = e*(1 + s*2*COST)
        if stage == 1 and ((s == 1 and fav >= tp2) or (s == -1 and fav <= tp2)):
            pnl += (1/3)*pr(tp2); rem -= 1/3; stage = 2
        if stage >= 1:
            best = max(best, fav) if s == 1 else min(best, fav)
            trail = best - s*3*atr
            if (s == 1 and trail > stop) or (s == -1 and trail < stop): stop = trail
    j = min(i+X.CAP, n-1)
    return pnl + rem*pr(C[j]), j-i, "cap"


def hold(C, H, L, a, i, side, N):
    j = min(i+N, len(C)-1)
    return side*(C[j]/C[i] - 1) - COST, j-i, "hold"


def run(P, pair, which, side, exit_fn):
    rows, ctrl = [], []
    for s, (C, H, L, a, sig) in P.items():
        up, dn, au, ad = sig[pair]
        src = {("cross", 1): up, ("cross", -1): dn, ("ant", 1): au, ("ant", -1): ad}[(which, side)]
        idx = np.where(src)[0]; idx = idx[(idx > 250) & (idx < len(C)-2)]
        last = -10**9
        for i in idx:
            if i - last < X.X_MIN_GAP: continue
            last = i
            r, b, how = exit_fn(C, H, L, a, i, side); rows.append((s, r, b, how))
            j = int(RNG.integers(250, len(C)-2)); r2, b2, _ = exit_fn(C, H, L, a, j, side); ctrl.append((s, r2, b2, ""))
    return pd.DataFrame(rows, columns=["sym","ret","bars","how"]), pd.DataFrame(ctrl, columns=["sym","ret","bars","how"])


if __name__ == "__main__":
    data = X.load(); P = {}
    PAIRS = [(20, 50), (9, 21)]
    for s, d in data.items():
        d4 = d.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
        C, H, L, a = X.prep(d4)
        P[s] = (C, H, L, a, {p: X.signals(C, a, *p) for p in PAIRS})
    EXITS = [("scaled", scaled), ("trail 3", lambda C,H,L,a,i,s: X.trail(C,H,L,a,i,s,3)[:2] + ("trail",)),
             ("hold 6", lambda *q: hold(*q, 6)), ("hold 12", lambda *q: hold(*q, 12)),
             ("hold 24", lambda *q: hold(*q, 24)), ("hold 48", lambda *q: hold(*q, 48))]
    print(f"{len(P)} coins, 4-hour bars, 9bp round trip. Edge = real minus random with the SAME exit.\n")
    print(f"  {'entry':<18}{'side':<6}{'exit':<9}{'n':>7}{'per ep':>9}{'t':>7}{'win':>6}{'hold':>6}{'ctrl':>8}{'edge':>8}{'coins>ctrl':>11}")
    for side, sl in ((1, "LONG"), (-1, "SHORT")):
        for pair in PAIRS:
            for which, label in (("ant", "anticipated"), ("cross", "cross")):
                for ename, efn in EXITS:
                    R, Cc = run(P, pair, which, side, efn)
                    if len(R) < 100: continue
                    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
                    by = R.groupby("sym").ret.mean() - Cc.groupby("sym").ret.mean()
                    print(f"  {label+' '+str(pair[0])+'/'+str(pair[1]):<18}{sl:<6}{ename:<9}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+7.1f}"
                          f"{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>6.0f}{Cc.ret.mean()*100:>+7.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}"
                          f"{(by>0).mean()*100:>10.0f}%", flush=True)
                print()
