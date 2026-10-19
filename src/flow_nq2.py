"""
HOW MIGHT HIS ALGO BE DOING IT? — second pass on Nasdaq-100 overnight (DK, 19 Oct:
"Don't close this guy's tick book. I want you to figure out how his algo is or might be doing it.")

Docs 84/86 tested the literal reading (delta imbalance -> go with it, plus HTF trend) and it
equals random on both panels. This pass treats the edge as UNKNOWN and tests the readings
that fit his numbers better: 20-pt target vs 50-pt stop in a thin session is mean-reversion
geometry; "delta didn't go off balance" may mean "nobody pushing, so fade the extreme".

Same data (data_nq/nq_1m.csv), same management (stop 50, half at +20 -> BE, trail 30, 2h cap),
same 5 random controls per trade, same +-30 barrier race. Points per trade.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import flow_nq as FN
from flow_nq import manage, race, line, STOP, TP1, TRAIL, CAP
RNG = np.random.default_rng(11)


def prep():
    b = FN.features()
    # extra features
    b["ret1"] = b.close.diff()
    b["lo30"] = b.low.rolling(30).min().shift(1); b["hi30"] = b.high.rolling(30).max().shift(1)
    b["d15"] = b.delta.rolling(15).sum()
    b["d15_prev"] = b.d15.shift(15)
    b["cumd"] = b.delta.groupby(b.gday).cumsum()
    b["cumd_z"] = (b.cumd - b.cumd.rolling(240).mean())/b.cumd.rolling(240).std()
    b["px_z"] = (b.close - b.close.rolling(240).mean())/b.close.rolling(240).std()
    b["rng60"] = b.high.rolling(60).max() - b.low.rolling(60).min()
    b["atr"] = (b.high - b.low).rolling(60).mean()
    # Keltner-style containment: fraction of last 120 bars inside 20-bar EMA +- 1.5*ATR
    ema = b.close.ewm(span=20, adjust=False).mean()
    inside = ((b.close < ema + 1.5*b.atr) & (b.close > ema - 1.5*b.atr)).astype(float)
    b["contain"] = inside.rolling(120).mean()
    b["ema20"] = ema
    return b.dropna()


def run(b, sig_fn, gap=10, nctrl=5, entry="open"):
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    rows, ctrl = [], []
    for s in (1, -1):
        sig = sig_fn(b, s).values
        idx = np.where(sig)[0]; idx = idx[(idx > 1500) & (idx < len(C)-130)]; last = -10**9
        for i in idx:
            if i - last < gap: continue
            last = i
            r, k, how = manage(O, H, L, C, cost, i, s); rows.append((s, b.index[i], r, k, how, race(H, L, C, i, s)))
            for _ in range(nctrl):
                j = int(RNG.integers(1500, len(C)-130))
                r2, k2, _ = manage(O, H, L, C, cost, j, s); ctrl.append((s, b.index[j], r2, k2, "", race(H, L, C, j, s)))
    cols = ["side","ts","pts","bars","how","race"]
    return pd.DataFrame(rows, columns=cols), pd.DataFrame(ctrl, columns=cols)


def hdr():
    print(f"  {'variant':<34}{'n':>6}{'pts/tr':>8}{'t':>6}{'win':>6}{'PF':>6}{'hold':>5}{'ctrl':>8}{'edge':>7}{'race':>6}{'ctrl':>5}{'pts/month':>10}")


if __name__ == "__main__":
    b = prep()
    on = b.overnight
    print(f"NQ 1-minute {b.index.min().date()}..{b.index.max().date()}, {len(b):,} bars. Management: stop 50, half at +20 -> BE, trail 30, 2h cap.\n")

    # ---- 0. Does the market itself mean-revert overnight? Random entries with his management by hour block.
    print("0. RANDOM ENTRIES with his management, by hour block (UTC) — where does the geometry alone pay?")
    O, H, L, C, cost = b.open.values, b.high.values, b.low.values, b.close.values, b.cost.values
    hrs = b.index.hour.values
    blocks = [(22, 24), (0, 3), (3, 7), (7, 10), (10, 13.5), (13.5, 16), (16, 20), (20, 22)]
    for lo, hi in blocks:
        m = np.where((b.hour.values >= lo) & (b.hour.values < hi))[0]; m = m[(m > 1500) & (m < len(C)-130)]
        pick = RNG.choice(m, size=min(3000, len(m)), replace=False)
        res = [manage(O, H, L, C, cost, j, s)[0] for j in pick for s in (1, -1)]
        rc = [race(H, L, C, j, s) for j in pick[:1000] for s in (1, -1)]
        res = np.array(res); print(f"   {lo:>5}-{hi:<5} n={len(res):>5} {res.mean():>+6.2f} pts  win {(res>0).mean()*100:3.0f}%  race {np.nanmean(rc)*100:3.0f}%  1-min autocorr {pd.Series(b.ret1.values[m]).autocorr():+.3f}")

    print("\n1. FADE THE EXTREME (mean reversion) — overnight unless stated"); hdr()
    V = {
        "touch overnight high -> SHORT / low -> LONG": lambda b, s: on & ((b.low <= b.onl) if s == 1 else (b.high >= b.onh)),
        "touch prior-day H/L, fade": lambda b, s: on & ((b.low <= b.pdl) if s == 1 else (b.high >= b.pdh)),
        "fade + delta BALANCED (|dz|<0.5)": lambda b, s: on & (b.dz.abs() < 0.5) & ((b.low <= b.onl) if s == 1 else (b.high >= b.onh)),
        "fade + delta AGAINST the touch (absorption)": lambda b, s: on & ((b.low <= b.onl) & (b.dz < -1.0) if s == 1 else (b.high >= b.onh) & (b.dz > 1.0)),
        "fade + delta WITH the fade": lambda b, s: on & ((b.low <= b.onl) & (b.dz > 1.0) if s == 1 else (b.high >= b.onh) & (b.dz < -1.0)),
        "fade VWAP +-30pt stretch": lambda b, s: on & ((b.close < b.vwap - 30) if s == 1 else (b.close > b.vwap + 30)),
        "fade VWAP stretch, delta balanced": lambda b, s: on & (b.dz.abs() < 0.5) & ((b.close < b.vwap - 30) if s == 1 else (b.close > b.vwap + 30)),
        "fade 240-min z<-1.5 / >1.5": lambda b, s: on & ((b.px_z < -1.5) if s == 1 else (b.px_z > 1.5)),
        "fade overnight H/L, DAY session": lambda b, s: (~on) & ((b.low <= b.onl) if s == 1 else (b.high >= b.onh)),
        "first touch of ON H/L (gap 60)": lambda b, s: on & ((b.low <= b.onl) if s == 1 else (b.high >= b.onh)),
    }
    for name, fn in V.items():
        R, Cc = run(b, fn, gap=60 if "gap 60" in name else 10); line(name, R, Cc)

    print("\n2. DELTA DIVERGENCE / ABSORPTION — price pushes, delta does not confirm"); hdr()
    V = {
        "new 30m low, d15 > d15 30m ago (long)": lambda b, s: on & ((b.low <= b.lo30) & (b.d15 > b.d15_prev + 0) if s == 1 else (b.high >= b.hi30) & (b.d15 < b.d15_prev)),
        "new 30m low, delta z > 0 (long)": lambda b, s: on & ((b.low <= b.lo30) & (b.dz > 0) if s == 1 else (b.high >= b.hi30) & (b.dz < 0)),
        "cum delta z vs price z diverge >1": lambda b, s: on & ((b.cumd_z - b.px_z > 1.0) if s == 1 else (b.px_z - b.cumd_z > 1.0)),
        "cum delta z vs price z diverge >2": lambda b, s: on & ((b.cumd_z - b.px_z > 2.0) if s == 1 else (b.px_z - b.cumd_z > 2.0)),
        "heavy delta, price flat (abs, 15m)": lambda b, s: on & ((b.dz < -1.5) & (b.close - b.close.shift(15) > -5) if s == 1 else (b.dz > 1.5) & (b.close - b.close.shift(15) < 5)),
    }
    for name, fn in V.items():
        R, Cc = run(b, fn); line(name, R, Cc)

    print("\n3. OUR RANGE LOGIC on NQ overnight — containment switch + Keltner band touch, fade"); hdr()
    med = b.contain.median()
    V = {
        "Keltner lower touch (contain>median)": lambda b, s: on & (b.contain > med) & ((b.low <= b.ema20 - 1.5*b.atr) if s == 1 else (b.high >= b.ema20 + 1.5*b.atr)),
        "Keltner touch, contain<median": lambda b, s: on & (b.contain <= med) & ((b.low <= b.ema20 - 1.5*b.atr) if s == 1 else (b.high >= b.ema20 + 1.5*b.atr)),
        "Keltner touch, any session, contain>med": lambda b, s: (b.contain > med) & ((b.low <= b.ema20 - 1.5*b.atr) if s == 1 else (b.high >= b.ema20 + 1.5*b.atr)),
        "Keltner 2.5-ATR touch, overnight": lambda b, s: on & ((b.low <= b.ema20 - 2.5*b.atr) if s == 1 else (b.high >= b.ema20 + 2.5*b.atr)),
    }
    for name, fn in V.items():
        R, Cc = run(b, fn); line(name, R, Cc)
        if name.startswith("Keltner lower"):
            R["h"] = R.ts.dt.hour
            print("   by hour (pts/trade, n):", " ".join(f"{h}:{R[R.h==h].pts.mean():+.1f}({int((R.h==h).sum())})" for h in sorted(R.h.unique())))
            print("   exits:", R.how.value_counts().to_dict())
