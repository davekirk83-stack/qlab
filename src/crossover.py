"""
EMA CROSSOVERS, BOTH WAYS, WITH A TRAILING STOP — DK's Gooner-EMA idea.

DK, 18 Oct: "If we can see a major crossover like in the Gooner EMA coming
along would it be worth jumping in just before or as that happens? ... The
same would apply for impending downward crosses (death crosses) as shorts.
Study this system for potential, and stay optimistic until we reach a
conclusion."

Stance: give the idea every chance. Several EMA pairs, both directions, the
cross itself AND the anticipated cross, three trailing-stop widths, and the
exit-free barrier race so a wrong exit cannot hide a good entry. A random
entry with the identical trailing exit is the control. One row per episode.

ENTRIES (15-minute bars, 27 registered coins, five years)
  cross        fast EMA closes through slow EMA (up = long, down = short)
  anticipated  fast EMA within 0.25 ATR of slow, converging for 3 bars,
               not yet crossed - "jumping in just before"
  pairs        9/21, 20/50, 50/200 (DK's ribbon spans this range)
EXITS
  trailing stop k x ATR from the best price since entry, k in {2, 3, 4}
  cap 400 bars (~4 days)
  plus the exit-free barrier race: P(+2 ATR before -2 ATR)
COSTS 4.5bp taker in, 4.5bp taker out (a trailing stop is a market exit).
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os
import numpy as np, pandas as pd

COST = 9/10000; CAP = 400; X_MIN_GAP = 8
RNG = np.random.default_rng(21)
REG = json.load(open("/home/claude/qlab/runs/range_universe.json"))["registered_universe"]


def load():
    out = {}
    for s in REG:
        f = f"/home/claude/qlab/data_15m/{s}.csv"
        if not os.path.exists(f): continue
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        out[s] = d[~d.index.duplicated(keep="last")].sort_index()
    return out


def prep(d):
    C, H, L = d.close.values, d.high.values, d.low.values
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    a = pd.Series(tr).rolling(14).mean().bfill().values
    return C, H, L, a


def signals(C, a, fast, slow):
    ef = pd.Series(C).ewm(span=fast, adjust=False).mean().values
    es = pd.Series(C).ewm(span=slow, adjust=False).mean().values
    diff = ef - es
    up = (diff > 0) & (np.roll(diff, 1) <= 0); dn = (diff < 0) & (np.roll(diff, 1) >= 0)
    gap = np.abs(diff)/np.maximum(a, 1e-12)
    conv = (gap < np.roll(gap, 1)) & (np.roll(gap, 1) < np.roll(gap, 2))
    ant_up = (diff < 0) & (gap < 0.25) & conv & (np.roll(diff, 1) < 0)   # below, closing in from below
    ant_dn = (diff > 0) & (gap < 0.25) & conv & (np.roll(diff, 1) > 0)
    # one anticipated signal per approach: first bar it qualifies
    ant_up &= ~np.roll(ant_up, 1); ant_dn &= ~np.roll(ant_dn, 1)
    return up, dn, ant_up, ant_dn


def trail(C, H, L, a, i, side, k):
    """Enter at close i, trail k*ATR from the best price. Return (ret, bars, barrier)."""
    n = len(C); e = C[i]; best = e; atr = a[i]
    hit_up = hit_dn = None
    for j in range(i+1, min(i+CAP+1, n)):
        if side == 1:
            best = max(best, H[j]); stop = best - k*atr
            if hit_up is None and H[j] >= e + 2*atr: hit_up = j
            if hit_dn is None and L[j] <= e - 2*atr: hit_dn = j
            if L[j] <= stop:
                px = min(stop, C[j]) if j == i+1 else stop
                return (px*(1-COST))/(e*(1+COST)) - 1, j-i, _barrier(hit_up, hit_dn)
        else:
            best = min(best, L[j]); stop = best + k*atr
            if hit_up is None and L[j] <= e - 2*atr: hit_up = j
            if hit_dn is None and H[j] >= e + 2*atr: hit_dn = j
            if H[j] >= stop:
                px = max(stop, C[j]) if j == i+1 else stop
                return (e*(1-COST))/(px*(1+COST)) - 1, j-i, _barrier(hit_up, hit_dn)
    j = min(i+CAP, n-1)
    r = (C[j]*(1-COST))/(e*(1+COST)) - 1 if side == 1 else (e*(1-COST))/(C[j]*(1+COST)) - 1
    return r, j-i, _barrier(hit_up, hit_dn)


def _barrier(hu, hd):
    if hu is None and hd is None: return np.nan
    if hd is None: return 1.0
    if hu is None: return 0.0
    return 1.0 if hu < hd else 0.0


def run(P, pair, k, which, side):
    rows, ctrl = [], []
    for s, (C, H, L, a, sig) in P.items():
        up, dn, au, ad = sig[pair]
        src = {("cross", 1): up, ("cross", -1): dn, ("ant", 1): au, ("ant", -1): ad}[(which, side)]
        idx = np.where(src)[0]; idx = idx[(idx > 250) & (idx < len(C)-2)]
        last = -10**9
        for i in idx:
            if i - last < X_MIN_GAP: continue
            last = i
            r, b, br = trail(C, H, L, a, i, side, k); rows.append((s, r, b, br))
            j = int(RNG.integers(250, len(C)-2)); r2, b2, br2 = trail(C, H, L, a, j, side, k); ctrl.append((s, r2, b2, br2))
    R = pd.DataFrame(rows, columns=["sym","ret","bars","win2"]); Cc = pd.DataFrame(ctrl, columns=["sym","ret","bars","win2"])
    return R, Cc


if __name__ == "__main__":
    data = load(); P = {}
    PAIRS = [(9, 21), (20, 50), (50, 200)]
    for s, d in data.items():
        C, H, L, a = prep(d)
        P[s] = (C, H, L, a, {p: signals(C, a, *p) for p in PAIRS})
    print(f"{len(P)} coins, 15-minute bars, ~5 years. Trailing stop k x ATR, 400-bar cap, 9bp round trip.\n")
    print(f"  {'entry':<24}{'side':<6}{'k':>3}{'n':>8}{'per ep':>9}{'t':>7}{'win':>6}{'hold':>6}{'ctrl':>8}{'edge':>8}{'race':>7}{'ctrl race':>10}")
    for which, label in (("cross", "cross"), ("ant", "anticipated")):
        for pair in PAIRS:
            for side, sl in ((1, "LONG"), (-1, "SHORT")):
                for k in (2, 3, 4):
                    R, Cc = run(P, pair, k, which, side)
                    if len(R) < 100: continue
                    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
                    print(f"  {label+' '+str(pair[0])+'/'+str(pair[1]):<24}{sl:<6}{k:>3}{len(R):>8,}{R.ret.mean()*100:>+8.3f}%{t:>+7.1f}"
                          f"{(R.ret>0).mean()*100:>5.0f}%{R.bars.median():>6.0f}{Cc.ret.mean()*100:>+7.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}"
                          f"{R.win2.mean()*100:>6.0f}%{Cc.win2.mean()*100:>9.0f}%", flush=True)
            print()
    print("  'race' = share of episodes that reached +2 ATR before -2 ATR, exit-free. A real entry beats its control here.")
