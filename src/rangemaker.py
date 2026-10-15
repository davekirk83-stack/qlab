"""
WORKING THE RANGE — ladder in, ladder out, keep the remainder.

DK: "You can also ladder out etc. Sell some at the mid point and then more
     towards the extreme (or beyond). If it's truly ranging you can keep what
     remains if it all oscillated back unsold and try again."

That last sentence changes the object. Everything built so far is a TRADE: an
entry, an exit, a stop, done. What DK describes is INVENTORY in a range -
you buy in bites near the bottom, sell in bites near the top, and whatever
does not sell stays on the book for the next oscillation. There is no forced
exit while the range holds. That is market making, and nothing here models it.

THE MACHINE
  while the range holds (efficiency stays low, price stays inside the band):
    resting bids at and below the lower Keltner band, heavier further out
    resting offers at the mid and at and beyond the upper band
    anything filled on the bid adds to inventory; anything filled on the
    offer removes from it; unsold inventory simply waits
  the range BREAKS when efficiency rises above the cut or price closes beyond
    the band by more than BREAK_ATR - at that point remaining inventory is
    liquidated at market, and that liquidation is where the losses live
  inventory is capped, so a falling market cannot accumulate forever

MEASURED
  return on the capital committed, not per trade, because there is no longer
  a clean "trade"
  how long positions are held, how often the range breaks against us, and the
  worst single break - the tail that decides whether this is survivable
  versus the simple one-in-one-out book as the control
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

TF = "15min"
EFF_CUT, BREAK_ATR = 0.30, 1.5
MK, TAKER, SLIP = 1.5/10000, 4.5/10000, 5/10000


def load():
    out = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in out: continue
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            out[s] = d[["open", "high", "low", "close", "volume"]].resample(TF).agg(
                open=("open", "first"), high=("high", "max"), low=("low", "min"),
                close=("close", "last"), volume=("volume", "sum")).dropna()
    return out


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net/np.where(gross > 0, gross, np.nan)


def work_range(d, bid_rungs, ask_rungs, max_inv, hold_unsold):
    """Returns a list of (entry_ts, exit_ts, pnl_on_committed, bars_held, how)."""
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); a = atr_np(H, L, C)
    ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
    lo_b = ema - 2*a; hi_b = ema + 2*a
    eff = efficiency(C)
    out = []
    inv = []          # list of (price, size)
    opened = None
    sold_levels = set()
    for i in range(120, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        in_range = eff[i] < EFF_CUT
        broke = (C[i] < lo_b[i] - BREAK_ATR*a[i]) or (C[i] > hi_b[i] + BREAK_ATR*a[i])
        if inv and (broke or not in_range):
            # liquidate the book at market
            size = sum(s for _, s in inv)
            cost = sum(p*s for p, s in inv)/size
            px = C[i]*(1-SLIP-TAKER)
            out.append((opened, d.index[i], (px/(cost*(1+MK))-1),
                        i - opened_i, "break" if broke else "trend"))
            inv = []; opened = None; sold_levels = set()
            continue
        if not in_range: continue
        # offers: each ask level may fire ONCE per inventory episode.
        # The previous version re-sold at the same level on every subsequent
        # bar while price stayed above it, which booked one partial sale many
        # times over and produced t=+294 on 463,568 phantom trades.
        if inv:
            for k, (frac, lvl) in enumerate(ask_rungs):
                if k in sold_levels: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i] + lvl*a[i]
                if H[i] >= tgt and inv:
                    size = sum(s for _, s in inv)
                    sell = min(size*frac, size)
                    cost = sum(p*s for p, s in inv)/size
                    out.append((opened, d.index[i],
                                ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/size),
                                i - opened_i, "sold"))
                    sold_levels.add(k)
                    inv = [(p, s*(1-sell/size)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv:
                        opened = None; sold_levels = set()
        # bids
        held = sum(s for _, s in inv)
        if held < max_inv:
            for frac, off in bid_rungs:
                p = lo_b[i] + off*a[i]
                if L[i] < p and held + frac <= max_inv + 1e-9:
                    inv.append((p, frac)); held += frac
                    if opened is None:
                        opened = d.index[i]; opened_i = i
        if not inv:
            opened = None; sold_levels = set()
    return out


def summarise(res, tag):
    if len(res) < 50:
        print(f"  {tag:<34}too few"); return
    R = pd.DataFrame(res, columns=["open", "close", "ret", "bars", "how"])
    m = R.ret.mean(); t = m/(R.ret.std(ddof=1)/np.sqrt(len(R)))
    brk = R[R.how.isin(["break", "trend"])]
    print(f"  {tag:<34}n={len(R):>6}  {m*100:>+7.3f}%  t={t:>+6.2f}  "
          f"win {(R.ret>0).mean()*100:>3.0f}%  held {R.bars.median():>4.0f} bars  "
          f"breaks {len(brk)/len(R)*100:>3.0f}%  worst {R.ret.min()*100:>+7.1f}%")


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} symbols, {TF} bars\n")
    print("WORKING THE RANGE — ladder in, ladder out, hold the remainder\n")
    BIDS = {
        "1 bid":  [(1.0, 0.0)],
        "3 bids": [(0.25, 0.25), (0.35, 0.0), (0.40, -0.35)],
        "4 bids": [(0.15, 0.30), (0.25, 0.05), (0.30, -0.25), (0.30, -0.55)],
    }
    ASKS = {
        "all at mid":        [(1.0, "mid")],
        "half mid/half band":[(0.5, "mid"), (1.0, 0.0)],
        "DK: mid, band, beyond": [(0.4, "mid"), (0.4, 0.0), (1.0, 0.35)],
    }
    for bname, bid in BIDS.items():
        for aname, ask in ASKS.items():
            res = []
            for s, d in data.items():
                if len(d) < 800: continue
                res += work_range(d, bid, ask, max_inv=1.0, hold_unsold=True)
            summarise(res, f"{bname:<8} / {aname}")
        print()
