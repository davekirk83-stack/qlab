"""
DO CANDLESTICKS WORK? — direction-aware test with matched random controls.

DK: "Also candlestick types and patterns" / "Hanging man and shooting star may
be particularly useful."

THE THING MOST CANDLESTICK STUDIES GET WRONG
A bearish pattern tested as a long will look like it fails. Here each pattern
declares its direction and is scored in that direction: a bearish signal is
scored on the SHORT side, so a positive number always means "the pattern was
right". Neutral patterns (doji, spinning top) make no directional claim, so
they are tested for what they actually claim — a rise in the size of the next
move, regardless of sign.

CONTROLS, same as the level and pattern tests
  - matched random dates, same count per instrument, same eligible window
  - the barrier race, P(favourable 1 ATR before adverse 1 ATR) in 40 bars,
    which needs no exit rule and so cannot be contaminated by a tuned TP/SL
  - one signal per episode (10-bar gap), the standing anti-overlap rule

Costs are NOT netted here. These are entry-quality measurements, not strategies.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import candles as CD
from levels_general import load_universe

RNG = np.random.default_rng(404)
GAP, RACE_BARS, RACE_K = 10, 40, 1.0
FWD = (5, 10, 20)


def dedupe(idx, gap=GAP):
    out, last = [], -10**9
    for i in idx:
        if i - last >= gap:
            out.append(i); last = i
    return np.array(out, dtype=int)


def outcomes(df, idx, a, direction):
    """Signed by direction: positive always means the pattern was right.
    direction 0 -> measures absolute move size instead."""
    C, H, L = df.close.values, df.high.values, df.low.values
    n = len(C)
    rec = []
    for i in idx:
        if i + max(FWD) + RACE_BARS >= n or not np.isfinite(a[i]) or a[i] <= 0:
            continue
        s = direction if direction != 0 else 1
        r = {}
        for k in FWD:
            raw = C[i + k] / C[i] - 1
            r[f"f{k}"] = abs(raw) if direction == 0 else s * raw
        if direction == 0:
            # the claim is "indecision precedes a bigger move": measure range
            r["race"] = np.nan
            r["move"] = abs(C[i + 10] / C[i] - 1) / (a[i] / C[i])
        else:
            fav = C[i] + s * RACE_K * a[i]
            adv = C[i] - s * RACE_K * a[i]
            win = np.nan
            for j in range(i + 1, i + 1 + RACE_BARS):
                hu, hd = H[j] >= max(fav, adv), L[j] <= min(fav, adv)
                if hu and hd:
                    win = 0.5; break
                if (hu and s > 0) or (hd and s < 0):
                    win = 1.0; break
                if (hd and s > 0) or (hu and s < 0):
                    win = 0.0; break
            r["race"] = win
            r["move"] = np.nan
        rec.append(r)
    return rec


def scan(panel, fn, args, direction):
    real, ctrl = [], []
    for s, df in panel.items():
        if len(df) < 400:
            continue
        try:
            sig = fn(df, *args).fillna(0).values
        except Exception:
            continue
        a = CD.atr(df).values
        warm = 120
        hits = dedupe(np.flatnonzero((sig > 0) & (np.arange(len(sig)) > warm)))
        if len(hits) == 0:
            continue
        real += outcomes(df, hits, a, direction)
        lo, hi = warm, len(df) - max(FWD) - RACE_BARS - 1
        if hi > lo:
            fake = dedupe(np.sort(RNG.choice(np.arange(lo, hi),
                                             size=min(len(hits), hi - lo),
                                             replace=False)))
            ctrl += outcomes(df, fake, a, direction)
    return real, ctrl


def line(lab, rec, direction, pad=28):
    if len(rec) < 40:
        return None
    t = pd.DataFrame(rec)
    r = t.f10.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    if direction == 0:
        mv = t["move"].dropna()
        print(f"  {lab:{pad}s} n={len(r):5d}  |move| 10 bars {mv.mean():5.2f} ATR")
        return dict(n=len(r), f10=mv.mean(), race=np.nan)
    race = t.race.dropna()
    print(f"  {lab:{pad}s} n={len(r):5d}  f5 {t.f5.mean()*100:+6.2f}%  "
          f"f10 {r.mean()*100:+6.2f}%  f20 {t.f20.mean()*100:+6.2f}%  "
          f"t={r.mean()/se:+5.2f}  race {race.mean()*100:5.1f}%")
    return dict(n=len(r), f10=r.mean(), race=race.mean() if len(race) else np.nan)


def run(which):
    panel = load_universe(which)
    print(f"\n{'='*104}")
    print(f"  {which.upper()}  —  {len(panel)} instruments")
    print(f"  Signed by the pattern's OWN direction: + always means it was right.")
    print(f"  race = P(favourable 1 ATR before adverse 1 ATR in 40 bars). 50% is a coin.")
    print(f"{'='*104}")
    rows = []
    for name, (fn, argsets, d) in CD.CANDLES.items():
        for args in argsets:
            real, ctrl = scan(panel, fn, args, d)
            tag = f"{name}{list(args) if args else ''}"
            arrow = {1: "LONG ", -1: "SHORT", 0: "neutr"}[d]
            a = line(f"[{arrow}] {tag}", real, d)
            if a is None:
                continue
            b = line("        control", ctrl, d)
            if b:
                de = a["f10"] - b["f10"]
                dr = a["race"] - b["race"] if d != 0 else np.nan
                unit = "ATR" if d == 0 else "pp"
                extra = "" if d == 0 else f"   race {dr*100:+5.1f}pp"
                print(f"        {'EDGE vs control':20s} "
                      f"{'move' if d==0 else 'f10'} {de*100 if d else de:+6.2f}{unit}{extra}")
                rows.append(dict(universe=which, pattern=tag, dirn=arrow.strip(),
                                 n=a["n"], f10=a["f10"], race=a["race"],
                                 d_f10=de, d_race=dr))
            print()
    return rows


if __name__ == "__main__":
    print("DO CANDLESTICKS WORK? — direction-aware, vs matched random dates")
    allr = []
    for u in ("etf", "crypto_daily", "crypto_hourly"):
        allr += run(u)
    R = pd.DataFrame(allr)
    R.to_csv("/home/claude/qlab/runs/candles_general.csv", index=False)
    print(f"\n{'='*104}")
    print("  DK's TWO — hanging man and shooting star, every universe")
    print(f"{'='*104}")
    dk = R[R.pattern.str.startswith(("hanging_man", "shooting_star"))]
    for _, r in dk.iterrows():
        print(f"  {r.universe:14s} {r['pattern']:34s} n={r.n:5d}  "
              f"f10 {r.f10*100:+6.2f}%  edge {r.d_f10*100:+6.2f}pp  "
              f"race edge {r.d_race*100:+5.1f}pp")
    print(f"\n{'='*104}")
    print("  ALL — ranked by edge over control")
    print(f"{'='*104}")
    D = R[R.dirn != "neutr"].sort_values("d_f10", ascending=False)
    for _, r in D.head(16).iterrows():
        print(f"  {r.universe:14s} [{r.dirn:5s}] {r['pattern']:30s} n={r.n:5d}  "
              f"edge {r.d_f10*100:+6.2f}pp   race edge {r.d_race*100:+5.1f}pp")
    both = D[(D.d_f10 > 0) & (D.d_race > 0)]
    print(f"\n  beating control on BOTH measures: {len(both)} of {len(D)}  "
          f"(chance gives about {len(D)/4:.0f})")
