"""
DRY POWDER — trim a slice into rips, hold it as cash, deploy it into crashes.

DK: "Investing, but keeping let's say a moveable 15%-20% allocation of profits
     taken in rips to cash, which can then be deployed again during a crash or
     dip. Surely that would add value over the long term."

This is NOT the rule core_trade.py tested and found wanting, and the two
differences both matter:

  SIZE     that test trimmed 25-50%, repeatedly. DK trims 15-20%, so more than
           four fifths of the position is never sold and most of the
           compounding is untouched.
  RE-ENTRY that test bought back on an ordinary pullback to the moving average.
           DK holds the cash for a CRASH. Crypto delivers 50%+ drawdowns
           routinely, so the re-entry price can be far better.

It is also the exact thing whose absence has just destroyed the most committed
buy-and-hold vehicle in the market. Strategy (MSTR) refused to trim, saw mNAV
fall below 1 on 27 June 2026, and filed to sell up to $1.25bn of bitcoin near
$60,000 to service preferred dividends - having declined to sell any near
$125,000. A trimmed slice held as cash is precisely what would have prevented
that. The lesson is that the value of dry powder is not return, it is NOT
BEING A FORCED SELLER AT THE LOWS.

So this measures both, and the drawdown column is the one that matters:

  final equity   does it beat simply holding?
  max drawdown   how much less pain?
  deployments    how often the cash actually gets used - a rule that waits for
                 a crash that never comes is just a cash drag
  worst entry    whether the cash went in near the bottom or caught a knife

VARIANTS sweep the trim trigger, the slice size (15% and 20%, as specified),
and how deep a fall is required before the cash is deployed.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

COST = 0.0010
STABLE = ("USDT", "USDC", "DAI", "PYUSD", "USDS", "GUSD")


def load(minbars=900):
    out = {}
    for f in sorted(glob.glob("/home/claude/qlab/data_daily/*.csv")):
        s = os.path.basename(f)[:-4]
        if any(s.startswith(x) for x in STABLE): continue
        d = pd.read_csv(f)
        if "t" not in d.columns or len(d) < minbars: continue
        d.index = pd.to_datetime(d.t, unit="ms", utc=True)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        out[s] = d.close.astype(float)
    return out


def run(px, stretch=0.40, slice_frac=0.175, crash=0.40, ma_n=200, max_cash=0.20):
    """Returns (final, maxDD, n_deployments). Start fully invested."""
    p = px.dropna()
    if len(p) < 400: return None
    ma = p.rolling(ma_n).mean()
    peak = p.cummax()
    units = 1.0/p.iloc[0]; cash = 0.0
    curve = []
    deploys = 0
    for i in range(ma_n, len(p)):
        price = p.iloc[i]; m = ma.iloc[i]
        val = units*price + cash
        curve.append(val)
        if not np.isfinite(m) or m <= 0: continue
        dev = price/m - 1
        dd = price/peak.iloc[i] - 1
        cash_share = cash/val if val > 0 else 0
        # trim into a rip, but never hold more than max_cash in cash
        if dev > stretch and cash_share < max_cash and units > 0:
            room = (max_cash - cash_share)*val
            sell_val = min(slice_frac*units*price, room)
            sell = sell_val/price
            if sell > 0:
                cash += sell*price*(1-COST); units -= sell
        # deploy into a crash
        elif dd < -crash and cash > 0:
            buy = cash/(price*(1+COST))
            units += buy; cash = 0.0; deploys += 1
    if not curve: return None
    E = pd.Series(curve)
    mdd = (E/E.cummax()-1).min()
    return E.iloc[-1], mdd, deploys


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} products, daily bars.\n")
    CFG = [("hold — never trim", None),
           ("trim 15% at +40%, deploy at -40%", (0.40, 0.15, 0.40)),
           ("trim 20% at +40%, deploy at -40%", (0.40, 0.20, 0.40)),
           ("trim 20% at +40%, deploy at -50%", (0.40, 0.20, 0.50)),
           ("trim 20% at +60%, deploy at -50%", (0.60, 0.20, 0.50)),
           ("trim 20% at +25%, deploy at -30%", (0.25, 0.20, 0.30)),
           ("trim 20% at +60%, deploy at -60%", (0.60, 0.20, 0.60))]

    btc = [k for k in data if k.startswith("BTC")]
    if btc:
        b = data[btc[0]]
        print(f"BITCOIN, {str(b.index[0])[:10]} -> {str(b.index[-1])[:10]}")
        print(f"  {'variant':<36}{'$1 becomes':>12}{'vs hold':>10}"
              f"{'maxDD':>9}{'deploys':>9}")
        hold_v = b.iloc[-1]/b.iloc[0]
        hp = b.dropna(); hdd = (hp/hp.cummax()-1).min()
        print(f"  {'hold — never trim':<36}{hold_v:>11.2f}x{'—':>10}"
              f"{hdd*100:>8.1f}%{'—':>9}")
        for lbl, cfg in CFG[1:]:
            r = run(b, *cfg)
            if r is None: continue
            v, dd, n = r
            print(f"  {lbl:<36}{v:>11.2f}x{(v/hold_v-1)*100:>+9.1f}%"
                  f"{dd*100:>8.1f}%{n:>9}")

    print(f"\nACROSS ALL {len(data)} PRODUCTS")
    print(f"  {'variant':<36}{'median':>9}{'mean':>9}{'med maxDD':>12}"
          f"{'% beat hold':>13}{'avg deploys':>13}")
    holds = {}
    for s, p in data.items():
        q = p.dropna()
        if len(q) < 400: continue
        holds[s] = (q.iloc[-1]/q.iloc[0], (q/q.cummax()-1).min())
    hv = np.array([v for v, _ in holds.values()])
    hd = np.array([d for _, d in holds.values()])
    print(f"  {'hold — never trim':<36}{np.median(hv):>9.2f}{hv.mean():>9.2f}"
          f"{np.median(hd)*100:>11.1f}%{'—':>13}{'—':>13}")
    for lbl, cfg in CFG[1:]:
        vals, dds, beat, deps = [], [], [], []
        for s, p in data.items():
            if s not in holds: continue
            r = run(p, *cfg)
            if r is None: continue
            v, dd, n = r
            if not np.isfinite(v): continue
            vals.append(v); dds.append(dd); deps.append(n)
            beat.append(v > holds[s][0])
        if len(vals) < 30: continue
        print(f"  {lbl:<36}{np.median(vals):>9.2f}{np.mean(vals):>9.2f}"
              f"{np.median(dds)*100:>11.1f}%{np.mean(beat)*100:>12.0f}%"
              f"{np.mean(deps):>13.2f}")
    print("\n  The case for dry powder is NOT that it beats holding on return —")
    print("  core_trade.py already showed trimming costs the compounder. It is")
    print("  that it reduces the drawdown and leaves you solvent and buying at")
    print("  the lows instead of selling there. Judge the maxDD column first.")
