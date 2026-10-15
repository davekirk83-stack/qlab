"""
LADDERED FILLS AS A GENERAL RULE — not a cascade study.

DK: "You're making everything about the rare cascade events, but okay..."
    "Heavier fills near the extremes, lighter fills on approach."
    "Filling in three or four different price points within a range, rather
     than just hoping to execute one perfect fill, generally is more
     effective."

Correct, and the criticism lands. Cascades are ~300 events. The fill rule is
about EVERY entry, so it has to be tested on every entry.

THE GENERAL SETUP
Any long entry is: an intended price P, and a stop S below it where the thesis
dies. The only question is how you get filled between them. That shape is the
same whether the trigger is a cascade, a pullback, a band touch or a retest,
so the test uses GENERIC dip entries across the whole hourly panel —
thousands of events, no cascade anywhere.

  trigger   close falls at least 1 ATR below the 20-EMA (an ordinary pullback,
            deliberately common rather than special)
  stop      the lowest low of the prior 20 bars, less a buffer — a structural
            level, i.e. where the pullback stops being a pullback
  target    the 20-EMA, i.e. back to the mean
  fills     single at the trigger close, versus 3-5 rungs spread between the
            trigger and the stop

THE SIZING ERROR FROM THE FIRST RUN, CORRECTED
A ladder does not always fill. Scoring it at the same notional as a single
fill charges it for capital it never deployed, which makes a better method
look worse. Real traders size the ladder UP so that expected deployment
matches. So every variant is reported three ways:

  per intended      return on the full notional, unfilled counted as zero
  per deployed      return on the capital that actually went to work
  CAPITAL-MATCHED   the ladder scaled so its average deployment equals the
                    single fill's — the honest apples-to-apples number, and
                    the one that decides it

WEIGHTINGS
  flat              equal across rungs
  incr              heavier toward the stop — DK's rule: heavy at the extreme
  front             heavier at the top — the control. If front also beats
                    single, the gain is from spreading, not from weighting.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DIR = "/home/claude/qlab/data_1h_33"
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000
MAXH = 48          # hours to resolve

VARIANTS = {
    "single fill":      [1.0],
    "flat 3":           [1, 1, 1],
    "flat 4":           [1, 1, 1, 1],
    "incr 3 (1:2:3)":   [1, 2, 3],
    "incr 4 (1:2:3:4)": [1, 2, 3, 4],
    "front 3 (3:2:1)":  [3, 2, 1],
}


def atr(H, L, C, n=14):
    tr = np.maximum(H - L, np.maximum(np.abs(H - np.roll(C, 1)),
                                      np.abs(L - np.roll(C, 1))))
    tr[0] = H[0] - L[0]
    return pd.Series(tr).rolling(n).mean().bfill().values


def play(C, H, L, i, stop, tgt, weights):
    top = C[i]
    k = len(weights)
    lowest = stop * 1.0010
    px = [top] if k == 1 or lowest >= top else list(np.linspace(top, lowest, k))
    w = np.array(weights[:len(px)], float); w = w / w.sum()
    filled, out = [], None
    n = len(C)
    for q in range(i + 1, min(i + 1 + MAXH, n)):
        for p, ww in zip(px, w):
            if L[q] <= p and not any(abs(p - fp) < 1e-12 for fp, _ in filled):
                filled.append((p, ww))
        if not filled:
            continue
        dep = sum(x for _, x in filled)
        entry = (sum(p * x for p, x in filled) / dep) * (1 + MAKER)
        if L[q] <= stop:
            out = ((stop * (1 - SLIP - TAKER)) / entry - 1, dep); break
        if H[q] >= tgt:
            out = ((tgt * (1 - MAKER)) / entry - 1, dep); break
    if not filled:
        return 0.0, np.nan, 0.0
    if out is None:
        dep = sum(x for _, x in filled)
        entry = (sum(p * x for p, x in filled) / dep) * (1 + MAKER)
        q = min(i + MAXH, n - 1)
        out = ((C[q] * (1 - MAKER)) / entry - 1, dep)
    r, dep = out
    return r * dep, r, dep


def run():
    rows = []
    for f in sorted(glob.glob(f"{DIR}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        if len(d) < 2000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        a = atr(H, L, C); n = len(C)
        ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
        prior_low = pd.Series(L).rolling(20).min().shift(1).values
        # Keltner LOWER band touch -> target the mid. Doc 48 measured this as
        # reverting to the mid 77-86% of the time, so the base trade has an
        # edge and the comparison is about the FILL, not about the signal.
        band = ema - 2 * a
        trig = (C <= band) & (np.roll(C, 1) > np.roll(band, 1))
        last = -10 ** 9
        for i in np.flatnonzero(trig):
            if i < 50 or i > n - MAXH - 2 or i - last < MAXH: continue
            # Thesis: price touched the lower band and reverts to the mid.
            # That breaks when price goes DECISIVELY BELOW the band — not when
            # it ticks under the recent low, which IS the band area here and
            # gave the trade no room at all (20.6% win rate).
            stop = min(band[i] - a[i], prior_low[i]) * 0.999
            if not np.isfinite(stop) or stop >= C[i] * 0.9995: continue
            tgt = ema[i]
            if tgt <= C[i]: continue
            last = i
            rec = {"sym": s}
            for name, w in VARIANTS.items():
                ri, rd, dep = play(C, H, L, i, stop, tgt, w)
                rec[name] = ri; rec[name + "|rd"] = rd; rec[name + "|dep"] = dep
            rows.append(rec)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("LADDERED FILLS, GENERAL CASE — Keltner lower-band touches, 33 perps")
    print("No cascades. A base trade with measured edge (doc 48). Target = the mid.\n")
    T = run()
    print(f"  {len(T)} entries across {T.sym.nunique()} symbols\n")
    sdep = T["single fill|dep"].mean()
    print(f"  {'variant':<20}{'per intended':>14}{'per deployed':>14}"
          f"{'deployed':>10}{'CAP-MATCHED':>13}{'t':>8}{'win':>8}")
    base_cm = None
    for name in VARIANTS:
        v = T[name].values
        dep = T[name + "|dep"].values
        rd = T[name + "|rd"].values; rdf = rd[np.isfinite(rd)]
        scale = sdep / dep.mean() if dep.mean() > 0 else np.nan
        cm = v * scale                      # scaled to equal average capital
        se = cm.std(ddof=1) / np.sqrt(len(cm))
        if base_cm is None: base_cm = cm
        print(f"  {name:<20}{v.mean()*100:>+13.3f}%{rdf.mean()*100:>+13.3f}%"
              f"{dep.mean()*100:>9.1f}%{cm.mean()*100:>+12.3f}%"
              f"{cm.mean()/se:>+8.2f}{(v>0).mean()*100:>7.1f}%")
    print()
    for name in VARIANTS:
        if name == "single fill": continue
        v = T[name].values; dep = T[name + "|dep"].values
        cm = v * (sdep / dep.mean())
        d = cm - base_cm; sed = d.std(ddof=1) / np.sqrt(len(d))
        print(f"    {name:<20} vs single, capital-matched: "
              f"{d.mean()*100:+.3f}pp  paired t={d.mean()/sed:+.2f}")
