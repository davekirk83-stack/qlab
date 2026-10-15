"""
FILL REALISM — the study doc 52 demanded and nobody ran.

Doc 52, section 2: "The open question is FILL RATE: a resting limit order
during a cascade bounce is trying to buy while price runs away from it...
Action required (next session, before the tracker accrues further)."

It was not run. Two registered books (cascade v3 and v3-K) rest a limit bid
0.4% below price after the base forms, and both BOOK A FILL WHENEVER THE LOW
TOUCHES THAT PRICE. That is the optimistic bound and everyone knows it is
optimistic; nobody has priced how optimistic.

WHY A TOUCH IS NOT A FILL
A limit order at price P joins a queue. If the market trades down to exactly P
and bounces, the volume printed at P may be entirely consumed by orders that
were already ahead of you. You are filled only if enough volume trades AT or
BELOW your price to clear the queue in front of you. So:

    touch           L <= P                 optimistic bound (what we book now)
    through_1bp     L <= P*(1-0.0001)      price went past you at all
    through_5bp     L <= P*(1-0.0005)      clearly through
    through_10bp    L <= P*(1-0.0010)      no queue doubt
    next_bar        filled only if the NEXT bar also trades at or below P,
                    i.e. the level held long enough to work a queue

Each is a progressively more pessimistic queue assumption. The book's return
is recomputed under every one, on the SAME signals, so this is paired.

THE TRADE-OFF THAT MATTERS
A stricter fill rule does two opposing things:
  - it REMOVES trades (you miss the ones that bounced instantly)
  - it IMPROVES the fills you do get (you bought lower)
and the ones it removes are disproportionately the instant bounces, which are
the WINNERS. If the edge survives the strictest rule, the books are sound. If
it only exists under "touch", they are an artefact of an optimistic fill and
should be suspended.

Also measured: the DEPTH-INFORMED version. Using the real order book
(data_depth_full), how much resting size sits at the bid level when the order
is placed? If our order is small relative to the resting size at that price,
the queue argument is weak and "touch" is closer to fair.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
DROP, WIN = 0.03, 5
LIFT, HOLD, DEPTHB, TP, MAXH = 0.008, 10, 0.004, 0.015, 60
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000

RULES = {
    "touch (as booked)": 0.0,
    "through 1bp": 0.0001,
    "through 5bp": 0.0005,
    "through 10bp": 0.0010,
}


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


def resolve(C, H, L, fill, px, stop, tgt, n):
    for q in range(fill + 1, min(fill + 1 + MAXH, n)):
        if L[q] <= stop: return (stop * (1 - SLIP - TAKER)) / px - 1, "stop"
        if H[q] >= tgt: return (tgt * (1 - MAKER)) / px - 1, "target"
    q = min(fill + MAXH, n - 1)
    return (C[q] * (1 - MAKER)) / px - 1, "time"


def run():
    rows = []
    for f in sorted(glob.glob(f"{M1}/*.csv")):
        s = os.path.basename(f)[:-4]
        d = pd.read_csv(f)
        if len(d) < 50000: continue
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C)
        i = WIN
        while i < n - 2 * MAXH:
            if C[i] / C[i - WIN] - 1 > -DROP: i += 1; continue
            b = find_base(C, L, i, n)
            if b is None: i += WIN; continue
            j, lo = b
            bid = max(C[j] * (1 - DEPTHB), lo * 1.0002)
            rec = dict(sym=s, sid=f"{s}|{j}")
            any_fill = False
            for lab, marg in RULES.items():
                trig = bid * (1 - marg)
                fill = None
                for q in range(j + 1, min(j + 1 + MAXH, n)):
                    if L[q] < lo: break
                    if L[q] <= trig: fill = q; break
                if fill is None:
                    rec[lab] = np.nan; continue
                any_fill = True
                px = bid * (1 + MAKER)          # you still pay YOUR limit price
                stop = lo * (1 - 0.0005); tgt = px * (1 + TP)
                if stop >= px: rec[lab] = np.nan; continue
                rec[lab] = resolve(C, H, L, fill, px, stop, tgt, n)[0]
            # strictest: the level must still be offered on the NEXT bar
            fill = None
            for q in range(j + 1, min(j + 1 + MAXH, n)):
                if L[q] < lo: break
                if L[q] <= bid and q + 1 < n and L[q + 1] <= bid:
                    fill = q + 1; break
            if fill is not None:
                px = bid * (1 + MAKER); stop = lo * (1 - 0.0005); tgt = px * (1 + TP)
                rec["next bar still bid"] = (resolve(C, H, L, fill, px, stop, tgt, n)[0]
                                             if stop < px else np.nan)
            else:
                rec["next bar still bid"] = np.nan
            if any_fill: rows.append(rec)
            i = j + MAXH
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("FILL REALISM — cascade v3's resting bid under progressively stricter queues\n")
    T = run()
    cols = list(RULES.keys()) + ["next bar still bid"]
    base_n = len(T)
    print(f"  {base_n} base-and-bid setups across {T.sym.nunique()} symbols\n")
    print(f"  {'fill rule':<22}{'filled':>8}{'fill %':>9}{'mean':>10}"
          f"{'win':>8}{'t':>8}{'vs touch':>11}")
    ref = T["touch (as booked)"].values
    for c in cols:
        v = T[c].values; m = np.isfinite(v); vv = v[m]
        if len(vv) < 20:
            print(f"  {c:<22}{len(vv):>8}  too few"); continue
        se = vv.std(ddof=1) / np.sqrt(len(vv))
        # paired against touch on the overlap
        both = np.isfinite(v) & np.isfinite(ref)
        d = (v[both] - ref[both])
        dtxt = f"{d.mean()*100:>+10.3f}pp" if c != "touch (as booked)" else "   —"
        print(f"  {c:<22}{len(vv):>8}{len(vv)/base_n*100:>8.1f}%"
              f"{vv.mean()*100:>+9.3f}%{(vv>0).mean()*100:>7.1f}%"
              f"{vv.mean()/se:>+8.2f}{dtxt}")
    print("\n  The question is not whether the mean falls. It is whether the book")
    print("  still has an edge once the easy fills are removed.")
