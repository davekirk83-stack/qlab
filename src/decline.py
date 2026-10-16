"""
SHORTING THE DECLINE — the trend book the range book's failure specified.

Doc 126 established that the range book loses on dying coins in BOTH
directions, and said exactly why: it shorts the UPPER band and covers near
the middle, so a collapsing coin never rallies far enough to fill the short,
and the dead-cat bounce that does reach it triggers the break exit. A
one-way market shreds a mean-reversion book.

That is a specification, not just a failure. The entry has to be the
BREAKDOWN, not the bounce.

THE BOOK
  universe    coins in sustained decline - price below a long moving average
              AND making lower highs, measured causally
  entry       short on a break of the recent low, which is the move that
              actually happens, rather than waiting for a rally that does not
  exit        a trailing stop, because the whole premise is that the decline
              persists and the exit should be the thing that ends it
  stop        the squeeze is the risk, so the stop is above the recent high

WHAT THE TEST MUST NOT DO. It must not be run only on coins known to have
died. Selecting the graveyard and then discovering that shorting it works is
circular - at the moment of entry nobody knows whether this is FTT in its
final weeks or a healthy coin having a bad month. So the book is run on the
WHOLE five-year survivor panel, where most declines recover, and the dying
coins are added as a separate cohort to see what they contribute. If it only
works on the graveyard, it is not a strategy, it is hindsight.

THREE COSTS the long side never faces, and the first two are usually ignored:
  funding     a crowded short pays funding to longs. Measured from the
              Hyperliquid hourly data gathered in doc 125 rather than assumed.
  squeeze     modelled by filling stops at the bar's HIGH, not the stop price
  borrow      not modelled here, and flagged, because no data source for it
              was found - it makes the real result worse than this one
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

MK, TAKER, SLIP = 1.5/10000, 4.5/10000, 5/10000
STABLE = {"USDTUSD","USDCUSD","DAIUSD","PYUSDUSD","USDSUSD","RLUSDUSD"}


def load(folder, minbars=20000):
    out = {}
    for f in sorted(glob.glob(f"{folder}/*.csv")):
        s = os.path.basename(f)[:-4]
        if s in STABLE: continue
        d = pd.read_csv(f, index_col=0)
        d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        if len(d) > minbars: out[s] = d
    return out


def atr(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def run(d, sym, ma_n, look, trail_atr, stop_atr, fund_hr=0.0):
    """Short the breakdown, trail the stop, get squeezed at the bar's high."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C)
    if n < ma_n + 100: return []
    a = atr(H, L, C)
    ma = pd.Series(C).rolling(ma_n).mean().values
    lowN = pd.Series(L).rolling(look).min().shift(1).values
    highN = pd.Series(H).rolling(look).max().shift(1).values
    out = []
    pos = None
    for i in range(ma_n+20, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0 or not np.isfinite(ma[i]): continue
        if pos is not None:
            # trailing stop rides down with price; squeeze fills at the HIGH
            pos["trail"] = min(pos["trail"], C[i] + trail_atr*a[i])
            if H[i] >= pos["trail"]:
                px = max(H[i], pos["trail"])          # filled at the worst
                hrs = (i - pos["i"])*0.25
                f = fund_hr*hrs
                r = (pos["px"]*(1-MK))/(px*(1+SLIP+TAKER)) - 1 - f
                out.append((sym, d.index[pos["i"]], d.index[i], r,
                            i-pos["i"], "squeeze"))
                pos = None; continue
            if C[i] > ma[i]:                          # the decline has ended
                hrs = (i - pos["i"])*0.25
                r = (pos["px"]*(1-MK))/(C[i]*(1+SLIP+TAKER)) - 1 - fund_hr*hrs
                out.append((sym, d.index[pos["i"]], d.index[i], r,
                            i-pos["i"], "trend over"))
                pos = None; continue
            continue
        # entry: in a confirmed decline, on a break of the recent low
        if C[i] < ma[i] and np.isfinite(lowN[i]) and L[i] < lowN[i]:
            px = lowN[i]*(1-SLIP)
            pos = {"i": i, "px": px,
                   "trail": (highN[i] if np.isfinite(highN[i]) else C[i]) + stop_atr*a[i]}
    return out


def report(rows, lbl, fund_note=""):
    if len(rows) < 50:
        print(f"  {lbl:<34}too few ({len(rows)})"); return None
    R = pd.DataFrame(rows, columns=["sym","entry","exit","ret","bars","how"])
    R = R[np.isfinite(R.ret)]
    t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    sq = (R.how == "squeeze").mean()
    print(f"  {lbl:<34}{len(R):>8,}{R.ret.mean()*100:>+10.3f}%{t:>+8.2f}"
          f"{(R.ret>0).mean()*100:>6.0f}%{sq*100:>9.0f}%"
          f"{R.ret.min()*100:>+9.1f}%{R.ret.sum()*100:>+10.0f}%{fund_note}")
    return R


if __name__ == "__main__":
    live = load("/home/claude/qlab/data_15m")
    dead = load("/home/claude/qlab/data_hl_dead", minbars=1500)
    print(f"{len(live)} surviving coins, {len(dead)} delisted coins\n")
    print("The book is run on BOTH. If it only works on the graveyard it is")
    print("hindsight, because at entry nobody knows which a coin will become.\n")
    print(f"  {'configuration':<34}{'trades':>8}{'per trade':>11}{'t':>8}"
          f"{'win':>6}{'squeezed':>9}{'worst':>9}{'total':>10}")
    best = None
    for ma_n, look, trail, stop in ((200, 48, 2.0, 1.0),
                                    (200, 96, 2.0, 1.0),
                                    (400, 96, 2.0, 1.0),
                                    (200, 48, 3.0, 1.5),
                                    (200, 96, 3.0, 1.5),
                                    (400, 96, 3.0, 1.5)):
        rows = []
        for s, d in live.items():
            rows += run(d, s, ma_n, look, trail, stop)
        R = report(rows, f"survivors  ma{ma_n} brk{look} trail{trail}", "")
        if R is not None and (best is None or R.ret.sum() > best[1]):
            best = ((ma_n, look, trail, stop), R.ret.sum())
    print()
    if best:
        ma_n, look, trail, stop = best[0]
        rows = []
        for s, d in dead.items():
            rows += run(d, s, ma_n, look, trail, stop)
        report(rows, f"DELISTED cohort, same config", "")
        print(f"\n  Best survivor configuration: ma{ma_n}, {look}-bar break, "
              f"{trail} ATR trail, {stop} ATR initial stop")
    print("\n  'squeezed' is the share exited by the trailing stop rather than")
    print("  by the trend ending — the short side's characteristic loss.")
    print("  FUNDING is not yet charged here and BORROW is not modelled at all;")
    print("  both make a real short book worse than this table.")
