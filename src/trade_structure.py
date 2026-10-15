"""
WHERE WINNERS ENTER, RELATIVE TO STRUCTURE — all episodes, not one.

DK: "I hope you can also see why they targeted a particular area based on the
     chart dynamics & levels etc."

Range position alone says high or low. It does not say WHY there. This adds
the structural context an actual trader would be looking at:

  prior swing high / low   distance in ATR to the nearest confirmed pivot
                           (5 bars either side) that existed BEFORE the fill
  previously-tested level  how many times price had already touched within
                           0.25 ATR of the fill price in the prior 500 bars.
                           A level tested three times is a level; a price
                           touched once is a coincidence
  prior-day extreme        distance to the previous 96-bar high and low
  round number             distance to the nearest 1-2-5 round increment,
                           scaled to price. Doc 62 found round numbers matter
                           only ~1.07x on BTC, so this is a control: if entries
                           cluster there we learned something, if not we have
                           confirmed our own earlier finding from the other side
  stretch                  ATR from the 20-EMA

Everything is computed from data available STRICTLY BEFORE the fill bar.

The comparison that makes it mean anything: the same measures taken at RANDOM
bars in the same instrument over the same window. Without that, "entries were
0.4 ATR from a swing high" is meaningless — they might all be.
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os
import numpy as np, pandas as pd

RNG = np.random.default_rng(7676)


def prep(path):
    d = pd.DataFrame(json.load(open(path)))
    for c in ("o", "c", "h", "l", "v"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.t, unit="ms")
    d = d.sort_values("ts").reset_index(drop=True)
    tr = np.maximum(d.h - d.l, np.maximum((d.h - d.c.shift()).abs(),
                                          (d.l - d.c.shift()).abs()))
    d["atr"] = tr.rolling(14).mean().bfill()
    d["ema"] = d.c.ewm(span=20, adjust=False).mean()
    d["hi96"] = d.h.rolling(96).max().shift(1)
    d["lo96"] = d.l.rolling(96).min().shift(1)
    # confirmed pivots, 5 bars either side -> known only 5 bars later
    H, L = d.h.values, d.l.values
    n = len(d)
    ph = np.zeros(n, bool); pl = np.zeros(n, bool)
    for i in range(5, n - 5):
        if H[i] == H[i-5:i+6].max(): ph[i] = True
        if L[i] == L[i-5:i+6].min(): pl[i] = True
    d["ph"], d["pl"] = ph, pl
    return d


def ctx(d, i, px):
    """Structural context of price px at bar i, using only data before i."""
    if i < 150 or not np.isfinite(px):
        return None
    a = d.atr.iloc[i]
    if not np.isfinite(a) or a <= 0:
        return None
    past = d.iloc[max(0, i - 500):i]
    sh = past.h[past.ph.values[:len(past)]] if past.ph.any() else pd.Series(dtype=float)
    sl = past.l[past.pl.values[:len(past)]] if past.pl.any() else pd.Series(dtype=float)
    d_sh = (sh - px).abs().min() / a if len(sh) else np.nan
    d_sl = (sl - px).abs().min() / a if len(sl) else np.nan
    # how often price has already traded within 0.25 ATR of here
    touches = int((((past.l <= px + 0.25 * a) & (past.h >= px - 0.25 * a))).sum())
    hi, lo = d.hi96.iloc[i], d.lo96.iloc[i]
    rngp = (px - lo) / (hi - lo) if np.isfinite(hi) and hi > lo else np.nan
    # nearest 1-2-5 round increment near 1% of price
    tgt = px * 0.01
    e = np.floor(np.log10(tgt)); m = tgt / 10 ** e
    step = (1 if m < 1.5 else 2 if m < 3.5 else 5 if m < 7.5 else 10) * 10 ** e
    d_round = min(px % step, step - (px % step)) / a
    return dict(range_pos=rngp, to_swing_hi=d_sh, to_swing_lo=d_sl,
                nearest_swing=np.nanmin([d_sh, d_sl]), touches=touches,
                to_hi96=abs(px - hi) / a if np.isfinite(hi) else np.nan,
                to_lo96=abs(px - lo) / a if np.isfinite(lo) else np.nan,
                to_round=d_round, stretch=(px - d.ema.iloc[i]) / a)


def run():
    real, ctrl = [], []
    for fp in sorted(glob.glob("/tmp/fills/win_*.json")):
        try:
            f = pd.DataFrame(json.load(open(fp)))
        except Exception:
            continue
        if not len(f) or "dir" not in f:
            continue
        for c in ("px", "sz", "closedPnl"):
            f[c] = pd.to_numeric(f[c], errors="coerce")
        f["ts"] = pd.to_datetime(f.time, unit="ms")
        for coin, g in f.groupby("coin"):
            cp = f"/tmp/cdl/{str(coin).replace(':','_')}.json"
            if not os.path.exists(cp):
                continue
            d = prep(cp)
            g = g[(g.ts >= d.ts.min()) & (g.ts <= d.ts.max())]
            if len(g) < 5:
                continue
            idx = np.clip(d.ts.searchsorted(g.ts) - 1, 0, len(d) - 1)
            for (_, r), i in zip(g.iterrows(), idx):
                o = "Open" in str(r.dir)
                short = "Short" in str(r.dir)
                c0 = ctx(d, int(i), r.px)
                if c0 is None:
                    continue
                c0.update(side="short" if short else "long",
                          kind="entry" if o else "exit", coin=coin)
                real.append(c0)
                j = int(RNG.integers(150, len(d) - 1))
                c1 = ctx(d, j, d.c.iloc[j])
                if c1:
                    c1.update(side=c0["side"], kind=c0["kind"], coin=coin)
                    ctrl.append(c1)
    return pd.DataFrame(real), pd.DataFrame(ctrl)


def show(R, C, kind, side):
    r = R[(R.kind == kind) & (R.side == side)]
    c = C[(C.kind == kind) & (C.side == side)]
    if len(r) < 100:
        return
    print(f"\n  {kind.upper()}S, {side.upper()}   n={len(r):,}   "
          f"(control = random bars, n={len(c):,})")
    print(f"    {'':<34}{'ACTUAL':>10}{'random':>10}{'ratio':>9}")
    for k, lab, inv in (("nearest_swing", "ATR to nearest prior pivot", True),
                        ("to_hi96", "ATR to the prior 24h HIGH", True),
                        ("to_lo96", "ATR to the prior 24h LOW", True),
                        ("to_round", "ATR to nearest round number", True),
                        ("touches", "times price already traded here", False),
                        ("stretch", "ATR from the 20-EMA", False),
                        ("range_pos", "position in prior 24h range", False)):
        a, b = r[k].median(), c[k].median()
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        ratio = (b / a) if (inv and a) else (a / b if b else np.nan)
        flag = ""
        if inv and np.isfinite(ratio) and ratio > 1.25: flag = "  <-- CLOSER than chance"
        if not inv and k == "touches" and a > b * 1.25: flag = "  <-- more tested"
        print(f"    {lab:<34}{a:>10.2f}{b:>10.2f}{ratio:>9.2f}{flag}")


if __name__ == "__main__":
    R, C = run()
    print("WHERE WINNERS ACTUALLY ENTER AND EXIT, vs RANDOM BARS IN THE SAME MARKETS")
    print(f"{len(R):,} fills with full structural context across "
          f"{R.coin.nunique()} instruments\n")
    for side in ("long", "short"):
        for kind in ("entry", "exit"):
            show(R, C, kind, side)
