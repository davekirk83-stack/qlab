"""
THE SHAPE OF A CASCADE — descriptive, not a trade.

DK asked for the anatomy rather than another backtest. Fair: four trade variants
have now failed, and the reason may be that I have been guessing at the structure
instead of measuring it.

Questions this answers, all of them about PATH rather than return:

  1. Where is the actual low relative to the end of the flush? Does price bottom
     when the liquidations stop, or keep sliding?
  2. How deep is the overshoot below the close of the last cascade bar?
  3. How big and how fast is the first bounce?
  4. Does it RETEST — come back down near the low — and how often?
  5. Does it make higher lows afterwards (DK's "creates a few levels a bit
     higher")?
  6. When, if ever, does the sustained move begin?

Medians throughout, because cascade returns are violently fat-tailed and means
describe a path nobody experiences. Percentile bands show the dispersion, which
matters more than the average here.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
PX = "/home/claude/qlab/data_1h_33"
EXCLUDE = {"BTCUSDT", "ETHUSDT"}
Z = 4.0
PRE, POST = 24, 168          # hours either side of the episode end


def load(sym):
    d = pd.read_csv(f"{OI}/{sym}.csv", parse_dates=["create_time"]).set_index("create_time")
    d = d[~d.index.duplicated()].sort_index()
    oi = d.sum_open_interest.resample("1h").last()
    k = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    k = k[~k.index.duplicated()]
    h = pd.DataFrame(dict(open=k.open, high=k.high, low=k.low, close=k.close,
                          oi=oi)).dropna()
    h["ret"] = h.close.pct_change()
    h["d_oi"] = h.oi.pct_change()
    return h.dropna()


def episodes(h, z=Z, gap=6):
    m = (h.ret < 0) & (h.d_oi < 0)
    flush = (-h.d_oi).where(m)
    zz = (flush - flush.mean()) / flush.std()
    idx = np.flatnonzero((zz > z).values)
    if len(idx) == 0:
        return []
    eps, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > gap:
            eps.append((s, prev)); s = i
        prev = i
    eps.append((s, prev))
    return eps


def main():
    syms = [f[:-4] for f in sorted(os.listdir(OI)) if f.endswith(".csv")]
    syms = [s for s in syms if s not in EXCLUDE and os.path.exists(f"{PX}/{s}.csv")]
    paths, facts = [], []
    for s in syms:
        try:
            h = load(s)
        except Exception:
            continue
        if len(h) < 2000:
            continue
        C, L, H = h.close.values, h.low.values, h.high.values
        for (a, e) in episodes(h):
            if e - PRE < 0 or e + POST >= len(h):
                continue
            ref = C[e]                      # close of the LAST cascade bar = time 0
            if ref <= 0:
                continue
            seg = C[e - PRE:e + POST + 1] / ref - 1
            paths.append(seg)
            fwd_lo = L[e + 1:e + POST + 1]
            fwd_hi = H[e + 1:e + POST + 1]
            lo_i = int(np.argmin(fwd_lo))
            low = fwd_lo[lo_i]
            # first bounce: highest point BEFORE the low is revisited
            after = fwd_hi[lo_i:]
            peak_i = int(np.argmax(after)) + lo_i
            # retest: does it come back within 2% of the low AFTER bouncing 3%+?
            bounced = (fwd_hi[lo_i:lo_i + 48].max() / low - 1) if lo_i + 1 < len(fwd_hi) else 0
            retest = False
            if bounced > 0.03:
                j0 = lo_i + int(np.argmax(fwd_hi[lo_i:lo_i + 48]))
                if j0 + 1 < len(fwd_lo):
                    retest = bool(fwd_lo[j0 + 1:].min() <= low * 1.02)
            facts.append(dict(
                sym=s,
                drop_in_flush=C[e] / C[a - 1] - 1 if a >= 1 else np.nan,
                extra_fall=low / ref - 1,          # overshoot below time 0
                hours_to_low=lo_i + 1,
                bounce_from_low=fwd_hi[lo_i:lo_i + 24].max() / low - 1 if lo_i < POST else np.nan,
                peak_hours=peak_i + 1,
                peak_vs_ref=fwd_hi[:].max() / ref - 1,
                retest=retest,
                r72=C[e + 72] / ref - 1,
                r168=C[e + POST] / ref - 1,
            ))
    P = np.vstack(paths)
    F = pd.DataFrame(facts)
    print("THE SHAPE OF A CASCADE\n")
    print(f"  {F.sym.nunique()} alt perps, {len(F)} episodes. Time 0 = close of the")
    print(f"  LAST hour of extreme liquidation. All figures are MEDIANS unless said.\n")

    print("=" * 92)
    print("  1. THE PATH  (median % from the close of the last cascade bar)")
    print("=" * 92)
    marks = [-24, -12, -6, -3, -1, 0, 1, 2, 3, 6, 12, 24, 36, 48, 72, 96, 120, 168]
    print(f"  {'hour':>6} {'median':>9} {'25th':>9} {'75th':>9}")
    for m in marks:
        col = P[:, PRE + m]
        print(f"  {m:+6d} {np.median(col)*100:+8.2f}% {np.percentile(col,25)*100:+8.2f}% "
              f"{np.percentile(col,75)*100:+8.2f}%")

    print()
    print("=" * 92)
    print("  2. THE ANATOMY")
    print("=" * 92)
    def q(c, lab, pct=True):
        v = F[c].dropna()
        u = 100 if pct else 1
        s = "%" if pct else "h"
        print(f"  {lab:46s} median {np.median(v)*u:+7.2f}{s}  "
              f"[25th {np.percentile(v,25)*u:+7.2f}{s}, 75th {np.percentile(v,75)*u:+7.2f}{s}]")
    q("drop_in_flush", "fall DURING the flush")
    q("extra_fall", "further fall AFTER the flush ends")
    print(f"  {'hours from flush end to the actual low':46s} median "
          f"{np.median(F.hours_to_low):5.0f}h   "
          f"[25th {np.percentile(F.hours_to_low,25):.0f}h, "
          f"75th {np.percentile(F.hours_to_low,75):.0f}h]")
    print(f"     low comes within 1h: {float((F.hours_to_low<=1).mean())*100:4.0f}%   "
          f"within 6h: {float((F.hours_to_low<=6).mean())*100:4.0f}%   "
          f"within 24h: {float((F.hours_to_low<=24).mean())*100:4.0f}%")
    q("bounce_from_low", "first bounce off the low (24h)")
    print(f"  {'hours to the highest point in the week':46s} median "
          f"{np.median(F.peak_hours):5.0f}h")
    q("peak_vs_ref", "best price reached vs time 0 (any time in 168h)")
    print(f"\n  RETEST: after a 3%+ bounce, price returns within 2% of the low "
          f"{float(F.retest.mean())*100:.0f}% of the time")

    print()
    print("=" * 92)
    print("  3. SHAPE BY SEVERITY OF THE FLUSH")
    print("=" * 92)
    F["sev"] = pd.qcut(F.drop_in_flush, 3, labels=["mild", "medium", "severe"])
    print(f"  {'severity':10s} {'n':>5} {'flush':>9} {'extra fall':>11} {'to low':>8} "
          f"{'bounce':>9} {'r72':>9} {'r168':>9}")
    for lab, g in F.groupby("sev"):
        print(f"  {str(lab):10s} {len(g):5d} {np.median(g.drop_in_flush)*100:+8.2f}% "
              f"{np.median(g.extra_fall)*100:+10.2f}% {np.median(g.hours_to_low):7.0f}h "
              f"{np.median(g.bounce_from_low)*100:+8.2f}% {np.median(g.r72)*100:+8.2f}% "
              f"{np.median(g.r168)*100:+8.2f}%")

    print()
    print("=" * 92)
    print("  4. WHAT DK DESCRIBED, CHECKED DIRECTLY")
    print("=" * 92)
    higher_low = []
    for p in P:
        post = p[PRE:]
        lo_i = int(np.argmin(post[1:49])) + 1
        if lo_i + 24 >= len(post):
            continue
        seg = post[lo_i:lo_i + 48]
        # does the second half of the window hold above the first-half low?
        higher_low.append(bool(seg[24:].min() > seg[:24].min()))
    print(f"  'creates a few levels a bit higher' — after the low, the next 24h low")
    print(f"  holds above the first 24h low in {np.mean(higher_low)*100:.0f}% of episodes")
    up72 = float((F.r72 > 0).mean()) * 100
    up168 = float((F.r168 > 0).mean()) * 100
    print(f"  'then goes up' — positive at 72h in {up72:.0f}% of episodes, "
          f"at 168h in {up168:.0f}%")
    print(f"  median 72h {np.median(F.r72)*100:+.2f}%, median 168h {np.median(F.r168)*100:+.2f}%")


if __name__ == "__main__":
    main()
