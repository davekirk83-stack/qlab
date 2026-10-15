"""
SMALL-TIMEFRAME RANGE TRADING, WITH THE FEE ASSUMPTION CORRECTED.

DK: "We also haven't found a way to range trade small timeframes."

Correct, and I think I reached that conclusion on a careless number.

WHAT I GOT WRONG. Finding 92 concluded that below the hourly bar fee drag
exceeds the gross information available, and I have been treating that as
settled all day. The drag was computed at 6bp per round trip. On Hyperliquid
the maker fee is 1.5bp, so a MAKER-ONLY round trip is about 3bp. Rerunning
the same arithmetic at 15 minutes: gross information 7.43 against a charge of
6.14 rather than 12.27. It flips positive. The whole "intraday is impossible"
finding rests on a fee I picked without checking.

AND RANGE TRADING IS EXACTLY THE STRATEGY THAT CAN BE MAKER-ONLY. You post a
limit bid at the bottom of the range and a limit offer at the top and wait.
You never cross the spread. The earlier intraday tests all entered at the
close of the trigger bar, which is a taker fill, so they were charged for an
execution style this strategy does not need.

THE BOOK
  range     over the last N bars the price has stayed inside a band and the
            Kaufman efficiency is low - it is going nowhere
  bid       resting limit buy at the band's lower edge
  fill      conservative: only filled if the bar's LOW goes strictly BELOW
            the limit, so a bar that merely touches it does not count
  exit      resting limit sell at the mid or the upper edge - also maker
  stop      a close beyond the band by more than S_ATR, taken as a TAKER exit
            with slippage, because a stop is never a maker order

Costs swept across the three realistic venues rather than assumed:
  3bp   maker-only round trip, Hyperliquid-class
  6bp   what I charged before
  12bp  retail taker, to show what crossing the spread costs
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd

TAKER_EXIT, SLIP = 4.5/10000, 5/10000


def load_1m():
    out = {}
    for folder in ("/home/claude/qlab/data_1m", "/home/claude/qlab/data_1m_oos"):
        for f in sorted(glob.glob(f"{folder}/*.csv")):
            s = os.path.basename(f)[:-4]
            if s in out: continue
            d = pd.read_csv(f)
            d.index = pd.to_datetime(d.t, unit="ms", utc=True)
            out[s] = d[["open", "high", "low", "close", "volume"]]
    return out


def bars(d, tf):
    return d.resample(tf).agg(open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), volume=("volume", "sum")).dropna()


def atr_np(H, L, C, n=14):
    pc = np.roll(C, 1); pc[0] = C[0]
    tr = np.maximum(H-L, np.maximum(np.abs(H-pc), np.abs(L-pc)))
    return pd.Series(tr).rolling(n).mean().bfill().values


def efficiency(C, w=100):
    net = np.abs(pd.Series(C).diff(w)).values
    gross = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(w).sum().values
    return net/np.where(gross > 0, gross, np.nan)


def run(data, tf, look, eff_cut, maker_bp, hold=48, exit_at="mid"):
    mk = maker_bp/2/10000           # per side
    real = []; ctrl = []; days = 0.0; used = 0
    rng = np.random.default_rng(11)
    for s, d in data.items():
        b = bars(d, tf)
        if len(b) < 800: continue
        used += 1
        C, H, L = b.close.values, b.high.values, b.low.values
        n = len(C); a = atr_np(H, L, C)
        hi = pd.Series(H).rolling(look).max().values
        lo = pd.Series(L).rolling(look).min().values
        eff = efficiency(C)
        days += (b.index[-1]-b.index[0]).total_seconds()/86400
        last = -10**9
        for i in range(look+120, n-hold-2):
            if not (eff[i] < eff_cut): continue
            if i - last < hold: continue
            width = hi[i]-lo[i]
            if not np.isfinite(width) or width <= 0 or not np.isfinite(a[i]): continue
            if width > 6*a[i]: continue          # not a range, a trend
            bid = lo[i]
            mid = (hi[i]+lo[i])/2
            tgt = mid if exit_at == "mid" else hi[i]
            stop = lo[i] - 1.5*a[i]
            fill = None
            for q in range(i+1, min(i+1+hold, n)):
                if L[q] < bid: fill = q; break
                if C[q] > hi[i]: break           # broke out upward, no fill
            if fill is None: continue
            last = fill
            e = bid*(1+mk)
            out = None
            for q in range(fill+1, min(fill+1+hold, n)):
                if C[q] < stop:
                    out = (C[q]*(1-SLIP-TAKER_EXIT))/e - 1; break
                if H[q] >= tgt:
                    out = (tgt*(1-mk))/e - 1; break
            if out is None:
                q = min(fill+hold, n-1); out = (C[q]*(1-TAKER_EXIT))/e - 1
            real.append(out)
            # same-regime control: a random eligible bar, same geometry
            pool = np.flatnonzero((eff < eff_cut) & np.isfinite(a))
            pool = pool[(pool > look+120) & (pool < n-hold-2)]
            if len(pool):
                qq = int(rng.choice(pool))
                ee = C[qq]*(1+mk)
                o2 = None
                for q in range(qq+1, min(qq+1+hold, n)):
                    if C[q] < C[qq]-(bid-stop): o2 = (C[q]*(1-SLIP-TAKER_EXIT))/ee-1; break
                    if H[q] >= C[qq]+(tgt-bid): o2 = ((C[qq]+(tgt-bid))*(1-mk))/ee-1; break
                if o2 is None:
                    q = min(qq+hold, n-1); o2 = (C[q]*(1-TAKER_EXIT))/ee-1
                ctrl.append(o2)
    if len(real) < 100: return None
    r = np.array(real); c = np.array(ctrl) if ctrl else np.array([0.0])
    mo = days/max(used, 1)/30.44
    return dict(n=len(r), mean=r.mean(), t=r.mean()/(r.std(ddof=1)/np.sqrt(len(r))),
                ctrl=c.mean(), edge=r.mean()-c.mean(), win=(r > 0).mean(),
                per_mo=len(r)/max(mo, .1))


if __name__ == "__main__":
    data = load_1m()
    print(f"{len(data)} symbols of 1-minute data\n")
    print("RANGE TRADING ON SMALL TIMEFRAMES, MAKER-ONLY ENTRY")
    print("Resting bid at the bottom of the range; filled only if the bar trades")
    print("strictly through it. Exit resting at the mid. Stop is a taker exit.\n")
    print(f"{'tf':>6}{'look':>6}{'eff':>6}{'fee bp':>8}{'n':>7}{'/mo':>7}"
          f"{'net':>9}{'t':>8}{'ctrl':>9}{'EDGE':>9}{'win':>6}")
    cells = []
    for tf in ("5min", "15min", "30min"):
        for look in (24, 48):
            for eff_cut in (0.20, 0.30):
                for fee in (3, 6, 12):
                    r = run(data, tf, look, eff_cut, fee)
                    if r is None: continue
                    r.update(tf=tf, look=look, eff=eff_cut, fee=fee)
                    cells.append(r)
                    print(f"{tf:>6}{look:>6}{eff_cut:>6.2f}{fee:>8}{r['n']:>7}"
                          f"{r['per_mo']:>7.0f}{r['mean']*100:>+8.3f}%{r['t']:>+8.2f}"
                          f"{r['ctrl']*100:>+8.3f}%{r['edge']*100:>+8.3f}%"
                          f"{r['win']*100:>5.0f}%")
        print()
    pos = [c for c in cells if c["mean"] > 0 and c["edge"] > 0]
    print(f"cells net positive AND beating their control: {len(pos)} of {len(cells)}")
    if pos:
        b = max(pos, key=lambda x: x["t"])
        print(f"\nBEST: {b['tf']} bars, {b['look']}-bar range, eff<{b['eff']}, "
              f"{b['fee']}bp round trip")
        print(f"  {b['mean']*100:+.3f}%/trade  t={b['t']:+.2f}  "
              f"edge over control {b['edge']*100:+.3f}%  win {b['win']*100:.0f}%  "
              f"{b['per_mo']:.0f} trades/month")
        at3 = [c for c in pos if c["fee"] == 3]
        at12 = [c for c in cells if c["fee"] == 12 and c["mean"] > 0]
        print(f"\n  positive cells at 3bp (maker-only): {len(at3)}")
        print(f"  positive cells at 12bp (taker):      {len(at12)}")
        print("  If the first number is much larger than the second, execution")
        print("  style is the whole story and the strategy lives or dies on")
        print("  getting passive fills.")
