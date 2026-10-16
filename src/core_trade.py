"""
TRADING AROUND A CORE — does trimming and rebuying beat simply holding?

DK: "Not just holding, but trying to gain profit / equity by also trimming on
     rips and rebuying (with profit) on dips over the longer term."

This is the technique sometimes called trading around a core position, and it
is the right question to ask after the last two tests. Trend following failed
at 15 minutes and at daily horizon, but both of those bought and sold the
WHOLE position on a signal. DK is describing something different: keep the
exposure, and harvest the volatility that the trend travels through.

THE TENSION, which is the whole point:
  trimming into strength banks profit and funds a cheaper re-entry, and the
  range book has already proved short-horizon mean reversion is real in crypto
  BUT
  if price runs away after a trim you have sold the compounder, and in a
  strategy whose return comes from a handful of enormous winners that is the
  one unforgivable error

Bitcoin is the hard case because it is both strongly trending and violently
volatile, so both effects are large and the answer is not obvious.

THE VARIANTS
  hold              100% invested throughout, never traded      (the benchmark)
  trim/rebuy        sell a slice when price stretches above its own average,
                    buy it back when it falls below. Swept across how far
                    price must stretch and how big a slice is sold.
  floor             the same, but never allowing the position below a minimum,
                    so the core is always there for the move that runs away

Every variant starts with the same capital on the same day and ends on the
same day. Trimmed cash earns nothing - no interest assumed - which is
conservative but honest. Costs 10bp a side.

JUDGED ON final equity AND drawdown, because the honest case for trimming is
usually not that it earns more but that it hurts less, and that trade can be
worth taking even when it costs return.
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


def simulate(px, ma_n=100, stretch=0.20, slice_frac=0.25, floor=0.0,
             rebuy=0.0):
    """Start fully invested. Trim a slice whenever price is `stretch` above
    its own moving average and we have not already trimmed at this level;
    rebuy when price falls back to `rebuy` above the average."""
    p = px.dropna()
    if len(p) < 300: return None
    ma = p.rolling(ma_n).mean()
    cash = 0.0
    units = 1.0/p.iloc[0]          # $1 invested at the start
    trimmed = False
    for i in range(ma_n, len(p)):
        price = p.iloc[i]; m = ma.iloc[i]
        if not np.isfinite(m) or m <= 0: continue
        dev = price/m - 1
        if (not trimmed) and dev > stretch and units > 0:
            sell = units*slice_frac
            if (units - sell)*price < floor*(units*price):
                sell = max(units - floor*units, 0.0)
            if sell > 0:
                cash += sell*price*(1-COST); units -= sell; trimmed = True
        elif trimmed and dev < rebuy and cash > 0:
            buy = cash/(price*(1+COST))
            units += buy; cash = 0.0; trimmed = False
    return units*p.iloc[-1] + cash


if __name__ == "__main__":
    data = load()
    print(f"{len(data)} products with 900+ daily bars.\n")
    print("Every variant starts with $1 on the same day and ends on the same")
    print("day. Trimmed cash earns nothing. Costs 10bp a side.\n")

    CFG = [("hold — never trade", None),
           ("trim 25% at +20% over 100d avg", (100, 0.20, 0.25, 0.0, 0.0)),
           ("trim 25% at +35% over 100d avg", (100, 0.35, 0.25, 0.0, 0.0)),
           ("trim 50% at +35% over 100d avg", (100, 0.35, 0.50, 0.0, 0.0)),
           ("trim 25% at +20%, floor 50%", (100, 0.20, 0.25, 0.50, 0.0)),
           ("trim 25% at +50% over 200d avg", (200, 0.50, 0.25, 0.0, 0.0)),
           ("trim 25% at +20%, rebuy at -10%", (100, 0.20, 0.25, 0.0, -0.10))]

    # headline: BTC alone, the case DK named
    btc = [k for k in data if k.startswith("BTC")]
    if btc:
        b = data[btc[0]]
        print(f"BITCOIN alone, {str(b.index[0])[:10]} -> {str(b.index[-1])[:10]}")
        print(f"  {'variant':<36}{'$1 becomes':>13}{'vs hold':>11}")
        base = None
        for lbl, cfg in CFG:
            v = (b.iloc[-1]/b.iloc[0]) if cfg is None else simulate(b, *cfg)
            if v is None: continue
            if base is None: base = v
            print(f"  {lbl:<36}{v:>12.2f}x{(v/base-1)*100:>+10.1f}%")

    print(f"\nACROSS ALL {len(data)} PRODUCTS (median outcome, so one lucky")
    print("coin cannot carry the result):")
    print(f"  {'variant':<36}{'median':>10}{'mean':>10}{'% beating hold':>17}")
    holds = {s: (p.dropna().iloc[-1]/p.dropna().iloc[0])
             for s, p in data.items() if len(p.dropna()) > 300}
    for lbl, cfg in CFG:
        if cfg is None:
            vals = np.array(list(holds.values()))
            print(f"  {lbl:<36}{np.median(vals):>10.2f}{vals.mean():>10.2f}"
                  f"{'—':>17}")
            continue
        vals, beat = [], []
        for s, p in data.items():
            if s not in holds: continue
            v = simulate(p, *cfg)
            if v is None or not np.isfinite(v): continue
            vals.append(v); beat.append(v > holds[s])
        if len(vals) < 30: continue
        vals = np.array(vals)
        print(f"  {lbl:<36}{np.median(vals):>10.2f}{vals.mean():>10.2f}"
              f"{np.mean(beat)*100:>16.0f}%")
    print("\n  'median' is what a typical coin returned; 'mean' is dragged up by")
    print("  the few that ran. If trimming raises the MEDIAN but lowers the MEAN,")
    print("  it is helping the typical case and costing the compounders — which")
    print("  is the trade-off DK's method has to be judged on.")
