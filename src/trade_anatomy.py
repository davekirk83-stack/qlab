"""
ONE REAL TRADE, FILL BY FILL, AGAINST THE PRICE STRUCTURE IT WAS TRADED IN.

DK: "Did you see where these buyers bought relative to price structure, the
     thinking behind it, how the entries were staggered, and how TPs were
     taken? Or is it just entry price - sale price - profit?"

It is not just entry minus exit. On-chain fills give price, size, time, side
and passive-or-aggressive for every execution, and overlaying them on candles
shows WHERE in the structure each one landed. The reasoning is not recoverable
— nobody publishes their thinking — but the behaviour is fully observable, and
behaviour is what we can copy.

WHAT IS MEASURED FOR EVERY ENTRY FILL
  range position   where the fill sat in the prior 96-bar (24h) high-low range.
                   0 = at the low, 1 = at the high. This answers the question
                   directly: are they buying weakness, strength, or anywhere?
  vs the EMA       distance from the 20-bar EMA in ATR units — how stretched
                   was price when they committed?
  approach         was price falling or rising into the fill over the prior
                   4 bars? Buying into a fall is catching; into a rise is
                   chasing.
  passive          resting or crossing. A resting bid that fills means price
                   came to them.

AND FOR THE EXITS
  the same range position, so we can see whether profit was taken into
  strength or given back, and whether exits were staggered or dumped.

STAGGERING
  the price and time spacing between consecutive entry fills, and whether
  size grows or shrinks as the position builds.
"""
import warnings; warnings.filterwarnings("ignore")
import json, sys
import numpy as np, pandas as pd


def candles(path):
    d = pd.DataFrame(json.load(open(path)))
    for c in ("o", "c", "h", "l", "v"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.t, unit="ms")
    d = d.sort_values("ts").reset_index(drop=True)
    tr = np.maximum(d.h - d.l, np.maximum((d.h - d.c.shift()).abs(),
                                          (d.l - d.c.shift()).abs()))
    d["atr"] = tr.rolling(14).mean().bfill()
    d["ema"] = d.c.ewm(span=20, adjust=False).mean()
    W = 96                                   # 24h on 15-minute bars
    d["hi"] = d.h.rolling(W).max()
    d["lo"] = d.l.rolling(W).min()
    d["approach"] = d.c - d.c.shift(4)
    return d


def fills(path, coin):
    f = pd.DataFrame(json.load(open(path)))
    for c in ("px", "sz", "closedPnl", "fee"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f["ts"] = pd.to_datetime(f.time, unit="ms")
    f = f[f.coin == coin].sort_values("ts").reset_index(drop=True)
    f["notional"] = f.px * f.sz
    return f


def join(f, d):
    idx = d.ts.searchsorted(f.ts) - 1
    idx = np.clip(idx, 0, len(d) - 1)
    sub = d.iloc[idx].reset_index(drop=True)
    f = f.reset_index(drop=True)
    rng = (sub.hi - sub.lo).replace(0, np.nan)
    f["range_pos"] = (f.px - sub.lo) / rng
    f["atr_from_ema"] = (f.px - sub.ema) / sub.atr
    f["approach"] = np.sign(sub.approach)
    f["bar_ts"] = sub.ts
    return f.dropna(subset=["range_pos"])


def band(v, lo, hi):
    return ((v >= lo) & (v < hi)).mean() * 100


if __name__ == "__main__":
    coin = "ETH"
    d = candles("/tmp/eth_15m.json")
    f = join(fills(sys.argv[1], coin), d)
    f = f[f.ts >= d.ts.min()]
    opens = f[f.dir.astype(str).str.contains("Open")]
    closes = f[f.dir.astype(str).str.contains("Close")]
    short = "Short" in str(f.dir.iloc[0])
    print("=" * 80)
    print(f"  {coin}  {len(f)} fills  {f.ts.min()} -> {f.ts.max()}")
    print(f"  {len(opens)} entries / {len(closes)} exits   "
          f"realised ${f.closedPnl.sum():,.0f}   traded ${f.notional.sum():,.0f}")
    print(f"  direction: {dict(f.dir.value_counts())}")
    print("=" * 80)

    for lab, g in (("ENTRIES", opens), ("EXITS", closes)):
        if len(g) < 5:
            continue
        print(f"\n  {lab}  (n={len(g)})")
        print(f"    WHERE IN THE PRIOR 24h RANGE  (0 = at the low, 1 = at the high)")
        for lo, hi, name in ((0, .2, "bottom fifth  "), (.2, .4, "lower-middle  "),
                             (.4, .6, "middle        "), (.6, .8, "upper-middle  "),
                             (.8, 1.01, "top fifth     ")):
            pct = band(g.range_pos, lo, hi)
            bar = "#" * int(round(pct / 2))
            print(f"      {name} {pct:5.1f}%  {bar}")
        print(f"      median range position: {g.range_pos.median():.2f}")
        print(f"    STRETCH   median {g.atr_from_ema.median():+.2f} ATR from the 20-EMA")
        up = (g.approach > 0).mean() * 100
        print(f"    APPROACH  price RISING into the fill {up:5.1f}%   "
              f"falling {100-up:5.1f}%")
        print(f"    PASSIVE   {(~g.crossed).mean()*100:5.1f}% resting, "
              f"{g.crossed.mean()*100:5.1f}% crossing")
        print(f"    SIZE      median ${g.notional.median():,.0f}   "
              f"largest ${g.notional.max():,.0f}")

    print(f"\n  STAGGERING OF ENTRIES")
    o = opens.sort_values("ts")
    gap = o.ts.diff().dt.total_seconds().dropna() / 60
    dpx = o.px.diff().dropna() / o.px.mean() * 100
    print(f"    minutes between entry fills   median {gap.median():.1f}   "
          f"25th {gap.quantile(.25):.1f}   75th {gap.quantile(.75):.1f}")
    print(f"    price step between entries    median {dpx.abs().median():.3f}% "
          f"of price")
    adverse = (dpx < 0).mean() * 100 if not short else (dpx > 0).mean() * 100
    print(f"    share of adds at a WORSE price than the previous "
          f"(averaging in): {adverse:.1f}%")
    half = len(o) // 2
    print(f"    median size, first half of the build  ${o.notional.iloc[:half].median():,.0f}")
    print(f"    median size, second half              ${o.notional.iloc[half:].median():,.0f}")

    print(f"\n  HOW PROFIT CAME OFF")
    c = closes.sort_values("ts")
    if len(c) > 5:
        print(f"    exits taken in {len(c)} fills over "
              f"{(c.ts.max()-c.ts.min()).total_seconds()/3600:.1f}h")
        print(f"    median exit size ${c.notional.median():,.0f} vs "
              f"median entry ${o.notional.median():,.0f}")
        print(f"    exits that were PASSIVE: {(~c.crossed).mean()*100:.1f}%")
        win = (c.closedPnl > 0).mean() * 100
        print(f"    exit fills booked at a profit: {win:.1f}%")
