"""
IS THE CASCADE A SWING TRADE? — horizon reclassification.

DK: "Other than knowing the market itself and the bias on any given day, we
     need to categorise clearly between day trading and swing trading too."
    "I feel like the cascade is clearly a swing trade."
    "And keltner type trading is day trading etc."

He is pointing at something our implementations have BACKWARDS:

    cascade v3   MAXH = 60 bars on ONE-MINUTE data = a 60-minute cap.
                 That is a scalp. It was never chosen as a horizon; it was
                 inherited from the first version and never revisited.
    keltner      120 bars on HOURLY data = five days. That is a swing trade,
                 and it is the one DK calls day trading.

If the cascade bounce is really a multi-day recovery, a 60-minute cap is
cutting winners off at the knees — doc 44's finding that tight exits degrade
a trade MONOTONICALLY, applied to the horizon instead of the target.

THE TEST
Same entries, same stop, same target. Only the time cap moves: 60 minutes
through 10 days. If returns rise with the cap, the trade is a swing trade
being run as a scalp. If they fall, the current cap is right and the bounce
really is a one-hour event.

Also reported: how long the WINNERS actually take to reach target, which
answers the classification question directly rather than by inference.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

M1 = "/home/claude/qlab/data_1m"
DROP, WIN = 0.03, 5
LIFT, HOLD, DEPTHB, TP = 0.008, 10, 0.004, 0.015
MAKER, TAKER, SLIP = 2 / 10000, 5 / 10000, 10 / 10000
CAPS = [60, 120, 240, 480, 1440, 2880, 5760, 10080, 14400]   # minutes


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
        n = len(C); i = WIN
        while i < n - max(CAPS) - 10:
            if C[i] / C[i - WIN] - 1 > -DROP: i += 1; continue
            b = find_base(C, L, i, n)
            if b is None: i += WIN; continue
            j, lo = b
            bid = max(C[j] * (1 - DEPTHB), lo * 1.0002)
            fill = None
            for q in range(j + 1, min(j + 61, n)):
                if L[q] < lo: break
                if L[q] <= bid: fill = q; break
            if fill is None: i = j + 1; continue
            px = bid * (1 + MAKER); stop = lo * (1 - 0.0005); tgt = px * (1 + TP)
            if stop >= px: i = j + 1; continue
            rec = {"sym": s}
            # resolve once, out to the longest cap, then read off each cap
            hit_stop = hit_tgt = None
            for q in range(fill + 1, min(fill + max(CAPS) + 1, n)):
                if hit_stop is None and L[q] <= stop: hit_stop = q - fill
                if hit_tgt is None and H[q] >= tgt: hit_tgt = q - fill
                if hit_stop is not None or hit_tgt is not None:
                    if hit_stop is not None and hit_tgt is not None: break
                    if hit_stop is not None and hit_tgt is None: break
                    if hit_tgt is not None: break
            for cap in CAPS:
                st = hit_stop if (hit_stop is not None and hit_stop <= cap) else None
                tg = hit_tgt if (hit_tgt is not None and hit_tgt <= cap) else None
                if st is not None and (tg is None or st < tg):
                    r = (stop * (1 - SLIP - TAKER)) / px - 1
                elif tg is not None:
                    r = (tgt * (1 - MAKER)) / px - 1
                else:
                    q = min(fill + cap, n - 1)
                    r = (C[q] * (1 - MAKER)) / px - 1
                rec[cap] = r
            rec["t_target"] = hit_tgt
            rec["t_stop"] = hit_stop
            rows.append(rec)
            i = fill + 60
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("CASCADE HORIZON — is it a scalp or a swing trade?\n")
    T = run()
    print(f"  {len(T)} trades, {T.sym.nunique()} symbols\n")
    print(f"  {'time cap':>12}{'mean':>10}{'t':>8}{'win':>8}{'still open':>12}")
    for cap in CAPS:
        v = T[cap].values
        se = v.std(ddof=1) / np.sqrt(len(v))
        openish = ((T.t_target.isna() | (T.t_target > cap)) &
                   (T.t_stop.isna() | (T.t_stop > cap))).mean()
        lab = (f"{cap}m" if cap < 1440 else f"{cap//1440}d")
        print(f"  {lab:>12}{v.mean()*100:>+9.3f}%{v.mean()/se:>+8.2f}"
              f"{(v>0).mean()*100:>7.1f}%{openish*100:>11.1f}%")
    tt = T.t_target.dropna()
    ts = T.t_stop.dropna()
    print(f"\n  WINNERS reach the +1.5% target after: median {tt.median():.0f} min"
          f"  ({tt.median()/60:.1f}h), 75th pct {tt.quantile(.75):.0f} min")
    print(f"  LOSERS hit the stop after:            median {ts.median():.0f} min"
          f"  ({ts.median()/60:.1f}h)")
    for c in (60, 240, 1440, 10080):
        print(f"    reached target within {c if c<1440 else str(c//1440)+'d':>5}: "
              f"{(tt <= c).mean()*100:5.1f}% of eventual winners")
