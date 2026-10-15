"""
CASCADE -> BOUNCE -> BASE -> BREAKOUT.

DK: "Usually what happens in a cascade, when it comes to an end, is that it
reverses a bit, creates a few levels a bit higher, then goes up."

This is a materially different trade from the one tested in doc 33, and it fixes
the two things that broke that one:

    doc 33 version              this version
    buy the panic               wait for the panic to END
    no stop possible (price     stop goes under the BASE, which sits above the
    goes lower before bouncing) cascade low — so a real structural stop exists
    taker into a 7% spread      buy a breakout in calm conditions, not a flush

THE SEQUENCE, implemented literally
    1. cascade episode   consecutive hours of extreme OI destruction with price
                         falling (z > 4). Episodes are grouped, so ONE trade per
                         episode — the standing rule after doc 33's overlapping-
                         window error.
    2. the low           the lowest price in the window after the episode ends
    3. the base          a run of bars whose range is tight and whose low holds
                         ABOVE the cascade low — "a few levels a bit higher"
    4. the entry         close breaks above the base high
    5. the stop          under the base low (NOT under the cascade low)

NO LOOKAHEAD: the base is only confirmed using bars already closed, and the
breakout is only tradeable on the bar after it prints.

Everything is deduplicated, split-half tested, and power-checked before any
t-statistic is reported.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
PX = "/home/claude/qlab/data_1h_33"
EXCLUDE = {"BTCUSDT", "ETHUSDT"}      # effect absent in majors (doc 33)
Z = 4.0


def load(sym):
    d = pd.read_csv(f"{OI}/{sym}.csv", parse_dates=["create_time"]).set_index("create_time")
    d = d[~d.index.duplicated()].sort_index()
    oi = d.sum_open_interest.resample("1h").last()
    k = pd.read_csv(f"{PX}/{sym}.csv", parse_dates=["date"]).set_index("date").sort_index()
    k = k[~k.index.duplicated()]
    h = pd.DataFrame(dict(open=k.open, high=k.high, low=k.low, close=k.close,
                          volume=k.volume, oi=oi)).dropna()
    h["ret"] = h.close.pct_change()
    h["d_oi"] = h.oi.pct_change()
    return h.dropna()


def episodes(h, z=Z, gap=6):
    """Group consecutive cascade hours into EPISODES. Returns list of (start, end)."""
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


def find_base(h, end, max_wait=48, base_len=6, tight=0.6, min_bounce=0.005):
    """
    After the cascade ends, look for DK's structure:
      - a low is made
      - price bounces off it
      - a tight range forms whose LOW is above the cascade low
    Returns (entry_bar, base_high, base_low, cascade_low) or None.
    Uses only closed bars; the breakout is traded on the NEXT bar.
    """
    H, L, C = h.high.values, h.low.values, h.close.values
    n = len(h)
    stop_at = min(end + max_wait, n - 2)
    casc_low = L[max(0, end - 12):end + 1].min()
    # running low after the episode
    for j in range(end + base_len + 1, stop_at):
        win_lo = L[j - base_len:j].min()
        win_hi = H[j - base_len:j].max()
        ref = C[j - 1]
        if ref <= 0 or win_hi <= win_lo:
            continue
        # the base must sit ABOVE the cascade low — "levels a bit higher"
        if win_lo <= casc_low * (1 + min_bounce):
            continue
        # the base must be TIGHT relative to the cascade's own volatility
        casc_range = (H[max(0, end - 12):end + 1].max() -
                      L[max(0, end - 12):end + 1].min()) / ref
        if casc_range <= 0:
            continue
        if (win_hi - win_lo) / ref > tight * casc_range:
            continue
        # entry: this bar closes above the base high
        if C[j] > win_hi:
            return j, win_hi, win_lo, casc_low
    return None


def backtest(h, eps, slip_bp=25, max_bars=72, tp_r=None,
             base_len=6, tight=0.6, max_wait=48):
    H, L, C, O = h.high.values, h.low.values, h.close.values, h.open.values
    slip = slip_bp / 1e4
    out = []
    for (s, e) in eps:
        f = find_base(h, e, max_wait, base_len, tight)
        if f is None:
            continue
        j, bhi, blo, clow = f
        if j + 2 >= len(h):
            continue
        px = O[j + 1] * (1 + slip)           # trade the bar AFTER the breakout closes
        stop = blo * 0.995
        risk = px - stop
        if risk <= 0 or risk / px > 0.25:
            continue
        tp = px + tp_r * risk if tp_r else None
        ex, ret = None, None
        for k in range(j + 1, min(j + 1 + max_bars, len(h))):
            if L[k] <= stop:
                ret = (min(stop, O[k]) * (1 - slip)) / px - 1; ex = k; break
            if tp and H[k] >= tp:
                ret = (tp * (1 - slip)) / px - 1; ex = k; break
        if ex is None:
            k = min(j + max_bars, len(h) - 1)
            ret = (C[k] * (1 - slip)) / px - 1; ex = k
        out.append(dict(date=h.index[j], ret=ret, bars=ex - j,
                        risk_pct=risk / px, R=ret / (risk / px)))
    return out


def stats(rows):
    if len(rows) < 20:
        return None
    r = np.array([x["ret"] for x in rows])
    R = np.array([x["R"] for x in rows])
    se = r.std(ddof=1) / np.sqrt(len(r))
    return dict(n=len(r), mean=r.mean(), t=r.mean() / se if se > 0 else 0,
                med=np.median(r), win=(r > 0).mean(), R=R.mean(),
                bars=np.mean([x["bars"] for x in rows]))


def main():
    syms = [f[:-4] for f in sorted(os.listdir(OI)) if f.endswith(".csv")]
    syms = [s for s in syms if s not in EXCLUDE and os.path.exists(f"{PX}/{s}.csv")]
    frames, eps = {}, {}
    for s in syms:
        try:
            h = load(s)
            if len(h) > 2000:
                frames[s] = h
                eps[s] = episodes(h)
        except Exception:
            pass
    tot = sum(len(v) for v in eps.values())
    print("CASCADE -> BOUNCE -> BASE -> BREAKOUT  (DK's sequence, tested literally)\n")
    print(f"  {len(frames)} alt perps, {tot} distinct cascade EPISODES "
          f"(grouped from consecutive hours — one trade each)")
    print(f"  stop under the base, not under the cascade low. 25bp slippage.\n")

    print("=" * 100)
    print("  A. DOES THE BASE-BREAKOUT TRADE WORK?")
    print("=" * 100)
    print(f"  {'base len':9s} {'tight':>6} {'trades':>7} {'mean':>9} {'median':>9} "
          f"{'win':>7} {'meanR':>7} {'t':>7} {'risk%':>7}")
    best = None
    for bl in (4, 6, 8, 12):
        for tg in (0.4, 0.6, 0.8):
            rows = []
            for s, h in frames.items():
                rows += backtest(h, eps[s], base_len=bl, tight=tg)
            d = stats(rows)
            if not d:
                continue
            flag = ""
            if d["t"] > 2:
                flag = " <--"
                if best is None or d["t"] > best[1]["t"]:
                    best = ((bl, tg), d, rows)
            print(f"  {bl:9d} {tg:6.1f} {d['n']:7d} {d['mean']*100:+8.3f}% "
                  f"{d['med']*100:+8.3f}% {d['win']*100:6.1f}% {d['R']:+7.2f} "
                  f"{d['t']:+7.2f} {np.mean([x['risk_pct'] for x in rows])*100:6.2f}%{flag}")

    if not best:
        print("\n  Nothing reaches t>2. Reporting the strongest anyway for the split test.")
        rows = []
        for s, h in frames.items():
            rows += backtest(h, eps[s], base_len=6, tight=0.6)
        best = ((6, 0.6), stats(rows), rows)

    (bl, tg), d, rows = best
    print()
    print("=" * 100)
    print(f"  B. SPLIT-HALF ON THE BEST CONFIG (base {bl}, tight {tg})")
    print("=" * 100)
    t = pd.DataFrame(rows).sort_values("date")
    mid = t.date.quantile(0.5)
    for lab, g in (("all", t), ("first half", t[t.date < mid]),
                   ("second half", t[t.date >= mid])):
        r = g.ret.values
        if len(r) < 15:
            print(f"  {lab:14s} n={len(r)} too few"); continue
        se = r.std(ddof=1) / np.sqrt(len(r))
        print(f"  {lab:14s} n={len(r):4d}  mean {r.mean()*100:+7.3f}%  "
              f"median {np.median(r)*100:+7.3f}%  win {float((r>0).mean())*100:5.1f}%  "
              f"t={r.mean()/se:+5.2f}")

    print()
    print("  POWER CHECK: with n=%d and sd=%.2f%%, the minimum detectable effect at"
          % (len(t), t.ret.std() * 100))
    print("  two standard errors is %.2f%% — any null below that is about the sample."
          % (2 * t.ret.std() / np.sqrt(len(t)) * 100))

    print()
    print("=" * 100)
    print("  C. CONTROL — same base-breakout logic WITHOUT the cascade trigger")
    print("=" * 100)
    rng = np.random.default_rng(5)
    ctrl = []
    for s, h in frames.items():
        fake = [(i, i) for i in rng.choice(np.arange(50, len(h) - 100),
                                           size=max(len(eps[s]), 1), replace=False)]
        ctrl += backtest(h, fake, base_len=bl, tight=tg)
    c = stats(ctrl)
    if c:
        print(f"  random trigger  n={c['n']:4d}  mean {c['mean']*100:+7.3f}%  "
              f"win {c['win']*100:5.1f}%  t={c['t']:+5.2f}")
        print(f"  cascade trigger n={d['n']:4d}  mean {d['mean']*100:+7.3f}%  "
              f"win {d['win']*100:5.1f}%  t={d['t']:+5.2f}")
        print(f"\n  edge attributable to the CASCADE condition: "
              f"{(d['mean']-c['mean'])*100:+.3f}pp")


if __name__ == "__main__":
    main()
