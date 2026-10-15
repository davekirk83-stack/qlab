"""
DO WE ACTUALLY GET THE FILL? — the question that decides both open issues.

DK: "The likelihood of getting your perfect entry every time is near
     impossible. So laddering in or even just buying at predetermined
     intervals within an area to spread risk is better."

He is right that my test could not see this. In the intraday backtest a
resting bid fills whenever the bar's low trades through it - a perfect entry,
guaranteed, 17,474 times out of 17,474. The whole value of a ladder is
insurance against NOT being filled, and I was handing the single bid that
insurance free. The comparison was rigged before it ran.

THE QUEUE MODEL, from data_depth_full: cumulative resting bid depth at 0.2,
1, 2, 3, 4 and 5 percent below mid, every five minutes, 20 symbols, one year.

  1. my limit sits X% below the mid; interpolate the depth curve to get Q,
     the dollars of resting bids AHEAD of mine
  2. I join the back of that queue - the conservative assumption, and the
     right one for a retail account with no speed advantage
  3. each subsequent minute, the dollar volume that traded at or below my
     price eats the queue. I am filled only once cumulative traded volume
     exceeds Q, and partially filled in proportion before that
  4. if price rallies away before the queue clears, I am left with whatever
     partial fill I got - or nothing

THEN the two questions, both now answerable:
  A. how much of the intraday range book's Sharpe 3.61 survives real fills?
  B. does a ladder beat a single bid once neither gets a guaranteed entry?
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

PCTS = np.array([-5, -4, -3, -2, -1, -0.2])
COLS = ["d-5", "d-4", "d-3", "d-2", "d-1", "d-0.2"]
TF, LOOK, EFF, HOLD = "15min", 24, 0.30, 48
MK = 1.5/10000
TAKER_EXIT, SLIP = 4.5/10000, 5/10000


def load_pairs():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s = os.path.basename(p)[:-4]
        m1 = f"/home/claude/qlab/data_1m/{s}.csv"
        if not os.path.exists(m1):
            m1 = f"/home/claude/qlab/data_1m_oos/{s}.csv"
            if not os.path.exists(m1): continue
        D = pd.read_csv(p)
        D.index = pd.to_datetime(D.ts, utc=True)
        M = pd.read_csv(m1)
        M.index = pd.to_datetime(M.t, unit="ms", utc=True)
        out[s] = (M[["open", "high", "low", "close", "volume"]], D[COLS])
    return out


def depth_ahead(Drow, pct_below):
    """Dollars of resting bids between the mid and my price."""
    x = np.abs(PCTS)                      # 5,4,3,2,1,0.2 -> ascending below
    y = Drow.values.astype(float)
    order = np.argsort(x)
    xs, ys = x[order], y[order]           # 0.2 .. 5
    p = min(max(abs(pct_below), xs[0]), xs[-1])
    return float(np.interp(p, xs, ys))


def simulate_entry(M1, Drow, limit, mid, t0, max_min, my_size):
    """Queue-aware fill. Returns (filled_fraction, avg_price)."""
    pct = (limit/mid - 1)*100
    Q = depth_ahead(Drow, pct)
    eaten = 0.0; got = 0.0
    seg = M1.loc[t0:].iloc[1:max_min+1]
    for ts, r in seg.iterrows():
        if r.low <= limit:
            # dollar volume that traded at or below my price this minute,
            # apportioned by how much of the bar's range sat below the limit
            rng = max(r.high - r.low, 1e-12)
            frac = min(max((limit - r.low)/rng, 0.0), 1.0)
            vol_at = float(r.volume)*float(r.close)*frac
            eaten += vol_at
            if eaten > Q:
                avail = eaten - Q
                got = min(my_size, avail)
                if got >= my_size*0.999: return 1.0, limit
        if r.close > mid*1.004:           # price rallied away
            break
    return (got/my_size if my_size > 0 else 0.0), limit


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


def rungs(lo, a, style):
    """DK: 'aiming to fill towards or beyond the Keltner band'. So the rungs
    span from just short of the band to beyond it, heavier the further out."""
    if style == "single":  return np.array([lo]), np.array([1.0])
    if style == "ladder3": return lo - np.array([0., .25, .50])*a, np.array([1., 2., 3.])
    if style == "ladder4": return lo - np.array([0., .20, .40, .60])*a, np.array([1., 2., 3., 4.])
    if style == "dk3":     return lo + np.array([.20, -.15, -.50])*a, np.array([1., 2., 3.])
    if style == "dk4":     return lo + np.array([.25, 0., -.30, -.60])*a, np.array([1., 2., 3., 4.])
    raise ValueError(style)


def run(pairs, style, order_usd, optimistic=False, keltner=False, exit_far=False):
    rows = []
    for s, (M1, D) in pairs.items():
        b = bars(M1, TF)
        if len(b) < 400: continue
        C, H, L = b.close.values, b.high.values, b.low.values
        n = len(C); a = atr_np(H, L, C)
        if keltner:
            ema = pd.Series(C).ewm(span=20, adjust=False).mean().values
            lo = ema - 2*a; hi = ema + 2*a
        else:
            hi = pd.Series(H).rolling(LOOK).max().values
            lo = pd.Series(L).rolling(LOOK).min().values
        eff = efficiency(C); last = -10**9
        for i in range(LOOK+120, n-HOLD-2):
            if not (eff[i] < EFF) or i - last < HOLD: continue
            w = hi[i]-lo[i]
            if not np.isfinite(w) or w <= 0 or not np.isfinite(a[i]) or w > 6*a[i]: continue
            t0 = b.index[i]
            dsel = D.loc[:t0]
            if len(dsel) == 0: continue
            Drow = dsel.iloc[-1]
            mid = C[i]
            px, wt = rungs(lo[i], a[i], style)
            wt = wt/wt.sum()
            tgt = hi[i] if exit_far else (hi[i]+lo[i])/2
            stop = lo[i]-1.5*a[i]
            fills = []
            for k, p in enumerate(px):
                size = order_usd*wt[k]
                if optimistic:
                    seg = b.iloc[i+1:i+1+HOLD]
                    f = 1.0 if (seg.low < p).any() else 0.0
                else:
                    f, _ = simulate_entry(M1, Drow, p, mid, t0, HOLD*15, size)
                if f > 0: fills.append((p, wt[k]*f))
            dep = sum(x for _, x in fills)
            if dep <= 0.01:
                rows.append((s, t0, 0.0, 0.0)); continue
            e = (sum(p*x for p, x in fills)/dep)*(1+MK)
            out = None
            for q in range(i+1, min(i+1+HOLD, n)):
                if C[q] < stop: out = ((C[q]*(1-SLIP-TAKER_EXIT))/e-1)*dep; break
                if H[q] >= tgt: out = ((tgt*(1-MK))/e-1)*dep; break
            if out is None:
                q = min(i+HOLD, n-1); out = ((C[q]*(1-TAKER_EXIT))/e-1)*dep
            last = i
            rows.append((s, t0, out, dep))
    return pd.DataFrame(rows, columns=["sym", "ts", "ret", "dep"])


if __name__ == "__main__":
    pairs = load_pairs()
    print(f"{len(pairs)} symbols with both minute bars and order-book depth\n")
    print("DOES THE FILL SURVIVE A REAL QUEUE?")
    print("$50 order, the actual size this book would send on a $2,000 stack "
          "at 40 slots.\n")
    print(f"  {'entry':<12}{'signals':>9}{'filled%':>9}{'deploy':>9}"
          f"{'per trade':>12}{'t':>8}{'vs optimistic':>15}")
    CONFIGS = [("channel/mid  single","single",False,False),
               ("channel/mid  ladder3","ladder3",False,False),
               ("KELT/mid     single","single",True,False),
               ("KELT/far     single","single",True,True),
               ("KELT/far     dk3","dk3",True,True),
               ("KELT/far     dk4","dk4",True,True)]
    for style_label, style, kelt, far in CONFIGS:
        O = run(pairs, style, 50, optimistic=True, keltner=kelt, exit_far=far)
        R = run(pairs, style, 50, optimistic=False, keltner=kelt, exit_far=far)
        if len(R) < 50: print(f"  {style_label}: too few"); continue
        Rf = R[R.dep > 0.01]; Of = O[O.dep > 0.01]
        t = Rf.ret.mean()/(Rf.ret.std(ddof=1)/np.sqrt(len(Rf))) if len(Rf) > 2 else np.nan
        print(f"  {style_label:<22}{len(R):>9}{len(Rf)/max(len(R),1)*100:>8.0f}%"
              f"{Rf.dep.mean()*100:>8.0f}%{Rf.ret.mean()*100:>+11.4f}%{t:>+8.2f}"
              f"{Of.ret.mean()*100:>+14.4f}%")
    print("\n  'vs optimistic' is the same book with the old assume-it-fills rule.")
    print("  The gap between the two columns is how much of the result was")
    print("  never achievable.")
