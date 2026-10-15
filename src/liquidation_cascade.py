"""
LIQUIDATION CASCADES — does forced selling exhaust and revert?

DK: "On a big correction people love to quote how many billion people lost money.
Like volume, does this tend to indicate a reversal, or at least a reversion to mean?"

MECHANISM — why this is a better question than "does big volume reverse"
A liquidated trader is a FORCED seller. They are price-insensitive: the engine
closes them at whatever bid exists. That is a real reason for an overshoot, and
a real reason for it to stop abruptly — once the leveraged positions in a price
band are gone, the forced supply simply ends. Ordinary volume has no such
mechanism, which is why the volume-reversal idea failed and this one might not.

MEASUREMENT — why not a liquidation feed
Binance removed liquidationSnapshot from its archive, and its live feed is
throttled to one order per second, so it UNDER-REPORTS exactly the cascades we
care about. A better measure is available from data we already hold:

    open interest FALLING  =  positions being closed
    price FALLING at the same time  =  those closers are LONGS
    notional flushed = -dOI x price

That is the forced-exit flow in dollars, measured directly rather than scraped.

THE CLAIM BEING TESTED, PRECISELY
Doc 23 already found that ordinary "long liquidation" hours CONTINUE down
(-0.478% over 72h). That is not DK's claim. His claim is about the EXTREME tail:
that a massive cascade exhausts the sellers and reverts. Small flush vs huge
flush is a different question, so it is bucketed by SIZE here, which doc 23
never did.

POWER CHECK FIRST (standing rule since 14 Oct): before any negative result is
reported, show the test could detect the effect if it existed.
"""
import warnings; warnings.filterwarnings("ignore")
import os
import numpy as np, pandas as pd

OI = "/home/claude/qlab/data_oi"
HOR = [4, 12, 24, 72]          # hours forward


def load(sym):
    d = pd.read_csv(f"{OI}/{sym}.csv", parse_dates=["create_time"]).set_index("create_time")
    d = d[~d.index.duplicated()].sort_index()
    # implied price from notional / contracts
    d["px"] = d.sum_open_interest_value / d.sum_open_interest.replace(0, np.nan)
    d = d[d.px > 0].dropna(subset=["px"])
    h = pd.DataFrame({
        "px": d.px.resample("1h").last(),
        "oi": d.sum_open_interest.resample("1h").last(),
        "oiv": d.sum_open_interest_value.resample("1h").last(),
        "taker": d.sum_taker_long_short_vol_ratio.resample("1h").mean(),
    }).dropna()
    h["ret"] = h.px.pct_change()
    h["d_oi"] = h.oi.pct_change()
    # dollars of open interest removed in the hour (positive = flushed out)
    h["flushed"] = -(h.oi.diff() * h.px)
    for k in HOR:
        h[f"f{k}"] = h.px.shift(-k) / h.px - 1
    return h.dropna()


def main():
    syms = sorted(f[:-4] for f in os.listdir(OI) if f.endswith(".csv"))
    frames = {}
    for s in syms:
        try:
            frames[s] = load(s)
        except Exception:
            pass
    print("LIQUIDATION CASCADES — forced exits measured as open interest destroyed\n")
    print(f"  {len(frames)} perps, hourly, "
          f"{min(f.index.min() for f in frames.values()).date()} to "
          f"{max(f.index.max() for f in frames.values()).date()}")

    # long-liquidation events: price down AND open interest down
    rows = []
    for s, h in frames.items():
        m = (h.ret < 0) & (h.d_oi < 0)
        g = h[m].copy()
        g["sym"] = s
        # size of the flush, normalised per symbol so coins are comparable
        g["flush_pct"] = -g.d_oi                     # fraction of OI destroyed
        g["flush_z"] = (g.flush_pct - g.flush_pct.mean()) / g.flush_pct.std()
        g["base72"] = h.f72.mean()
        rows.append(g)
    D = pd.concat(rows)
    print(f"  {len(D):,} long-liquidation hours (price down + OI down)")
    print(f"  total notional destroyed in those hours: "
          f"${D.flushed.clip(lower=0).sum()/1e9:,.1f}bn\n")

    # ---------- POWER CHECK ----------
    print("=" * 96)
    print("  POWER CHECK — can this test detect an effect of the size we care about?")
    print("=" * 96)
    n_tail = int((D.flush_z > 3).sum())
    sd = D.f72.std()
    mde = 2 * sd / np.sqrt(max(n_tail, 1)) * 100
    print(f"  extreme bucket n={n_tail}, 72h return sd={sd*100:.2f}%")
    print(f"  minimum detectable effect at 2 s.e.: {mde:.2f}% over 72h")
    print(f"  -> a reversal smaller than {mde:.2f}% CANNOT be distinguished from noise here.")
    print(f"     Any null below that is a statement about the sample, not the market.\n")

    # ---------- the test, bucketed by SIZE ----------
    print("=" * 96)
    print("  DOES THE SIZE OF THE FLUSH CHANGE WHAT HAPPENS NEXT?")
    print("=" * 96)
    base = {k: np.mean([f[f"f{k}"].mean() for f in frames.values()]) for k in HOR}
    print("  baseline forward returns: " +
          "  ".join(f"{k}h {base[k]*100:+.3f}%" for k in HOR))
    print()
    print(f"  {'flush size (z of OI destroyed)':34s} {'n':>6} " +
          "".join(f"{k:>4}h fwd" for k in HOR) + f"{'coins +ve':>11}")
    buckets = [
        ("ordinary   z < 1", D.flush_z < 1),
        ("large      1 - 2", (D.flush_z >= 1) & (D.flush_z < 2)),
        ("very large 2 - 3", (D.flush_z >= 2) & (D.flush_z < 3)),
        ("CASCADE    z > 3", D.flush_z > 3),
        ("CASCADE    z > 4", D.flush_z > 4),
        ("CASCADE    z > 5", D.flush_z > 5),
    ]
    for name, m in buckets:
        g = D[m]
        if len(g) < 25:
            print(f"  {name:34s} {len(g):6d}   too few")
            continue
        line = f"  {name:34s} {len(g):6d} "
        for k in HOR:
            line += f"{g[f'f{k}'].mean()*100:+8.3f}%"
        per = [gg[f"f72"].mean() - frames[s].f72.mean()
               for s, gg in g.groupby("sym") if len(gg) >= 5]
        pos = sum(x > 0 for x in per)
        line += f"{pos:>6}/{len(per)}"
        print(line)

    # significance on the tail
    print()
    for z in (3, 4):
        g = D[D.flush_z > z]
        if len(g) < 25:
            continue
        se = g.f72.std() / np.sqrt(len(g))
        d = g.f72.mean() - base[72]
        print(f"  z>{z}: 72h {g.f72.mean()*100:+.3f}% vs baseline {base[72]*100:+.3f}% "
              f"-> {d*100:+.3f}pp, t={d/se:+.2f}  (n={len(g)})")

    # ---------- absolute dollar size, not z ----------
    print()
    print("=" * 96)
    print("  BY ABSOLUTE DOLLARS DESTROYED IN THE HOUR  (the 'billions wiped out' version)")
    print("=" * 96)
    print(f"  {'notional destroyed':24s} {'n':>6} {'4h':>9} {'24h':>9} {'72h':>9}")
    for lo, hi, lab in ((0, 10e6, "< $10m"), (10e6, 50e6, "$10-50m"),
                        (50e6, 200e6, "$50-200m"), (200e6, 1e12, "> $200m")):
        g = D[(D.flushed >= lo) & (D.flushed < hi)]
        if len(g) < 25:
            print(f"  {lab:24s} {len(g):6d}   too few"); continue
        print(f"  {lab:24s} {len(g):6d} {g.f4.mean()*100:+8.3f}% "
              f"{g.f24.mean()*100:+8.3f}% {g.f72.mean()*100:+8.3f}%")


if __name__ == "__main__":
    main()
