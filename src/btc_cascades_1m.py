"""
THE 20 BIGGEST BTC CASCADES, MINUTE BY MINUTE.

DK: "I've made big money off these lows, I think your time frames are off. If it
can bounce after the cascade, hold for 5 or 10 minutes, it then bounces
significantly. The cascade might be 5-20 minutes even but it does eventually
bounce."

He is right that the timeframe was wrong. Every previous run used HOURLY bars
with 72-168 hour holds. A spike down and a snap-back inside 5-20 minutes is
entirely contained within one hourly candle — invisible by construction. The
clue was there: the cascade bar's high-low range averaged 7.27% of price, which
is exactly where a wick-and-recovery would hide.

So: 1-minute bars, and the cascade identified from 5-minute open-interest
destruction, which is the finest resolution the archive provides.

For each of the 20 largest BTC cascades this prints the actual path — how far
it fell, how long the fall lasted, where the low landed, and what happened in
the minutes after — rather than an average, because DK asked what it LOOKS like.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

OI5 = "/home/claude/qlab/data_oi/BTCUSDT.csv"
M1 = "/home/claude/qlab/data_1m/BTCUSDT.csv"


def load():
    oi = pd.read_csv(OI5, parse_dates=["create_time"]).set_index("create_time")
    oi = oi[~oi.index.duplicated()].sort_index()
    oi["d_oi"] = oi.sum_open_interest.pct_change()
    oi["px"] = oi.sum_open_interest_value / oi.sum_open_interest.replace(0, np.nan)
    oi["ret"] = oi.px.pct_change()

    m = pd.read_csv(M1)
    m["dt"] = pd.to_datetime(m.t, unit="ms")
    m = m.set_index("dt").sort_index()
    m = m[~m.index.duplicated()]
    return oi, m


def main():
    oi, m = load()
    print("THE 20 BIGGEST BTC LIQUIDATION CASCADES — 1-minute resolution\n")
    print(f"  open interest at 5-min, {oi.index.min().date()} to {oi.index.max().date()}")
    print(f"  {len(m):,} minute bars\n")

    # cascade = 5-min window with price down and heavy OI destruction
    c = oi[(oi.ret < 0) & (oi.d_oi < 0)].copy()
    c["flushed"] = -c.d_oi
    c = c.sort_values("flushed", ascending=False)

    # de-duplicate: keep the biggest per 6-hour window
    picked, used = [], []
    for ts, row in c.iterrows():
        if any(abs((ts - u).total_seconds()) < 6 * 3600 for u in used):
            continue
        picked.append((ts, row)); used.append(ts)
        if len(picked) >= 20:
            break

    print("=" * 108)
    print("  Each row: the 5-min window of peak liquidation (t0), then the minute path after it")
    print("=" * 108)
    print(f"  {'date / time (UTC)':18s} {'OI -%':>6} {'low after':>10} {'mins':>5} "
          f"{'+5m':>7} {'+10m':>7} {'+20m':>7} {'+60m':>7} {'bounce off low':>15}")

    rows = []
    for ts, row in sorted(picked, key=lambda x: x[0]):
        t0 = ts + pd.Timedelta(minutes=5)          # act AFTER the 5-min window closes
        win = m[(m.index >= t0) & (m.index < t0 + pd.Timedelta(minutes=240))]
        if len(win) < 120:
            continue
        ref = win.close.iloc[0]
        lo_i = int(np.argmin(win.low.values[:120]))
        lo = win.low.values[lo_i]
        def at(k):
            return win.close.iloc[k] / ref - 1 if k < len(win) else np.nan
        bounce = win.high.values[lo_i:lo_i + 30].max() / lo - 1
        rows.append(dict(ts=ts, oi=row.flushed, low=lo / ref - 1, mins=lo_i + 1,
                         m5=at(5), m10=at(10), m20=at(20), m60=at(60), bounce=bounce))
        print(f"  {str(ts)[:16]:18s} {row.flushed*100:5.2f}% {lo/ref-1:+9.2f}% "
              f"{lo_i+1:5d} {at(5)*100:+6.2f}% {at(10)*100:+6.2f}% {at(20)*100:+6.2f}% "
              f"{at(60)*100:+6.2f}% {bounce*100:+14.2f}%")

    R = pd.DataFrame(rows)
    print()
    print("=" * 108)
    print("  WHAT THE 20 HAVE IN COMMON")
    print("=" * 108)
    print(f"  median further fall after the flush window closes : {R.low.median()*100:+.2f}%")
    print(f"  median minutes from t0 to the low                 : {R.mins.median():.0f} min")
    print(f"     low within 5 min: {int((R.mins<=5).sum())}/20   "
          f"within 20 min: {int((R.mins<=20).sum())}/20   "
          f"within 60 min: {int((R.mins<=60).sum())}/20")
    print(f"  median BOUNCE off the low (next 30 min)           : {R.bounce.median()*100:+.2f}%")
    print(f"     bounce > 1%: {int((R.bounce>0.01).sum())}/20   "
          f"> 2%: {int((R.bounce>0.02).sum())}/20")
    print()
    for k, lab in (("m5", "+5 min"), ("m10", "+10 min"), ("m20", "+20 min"), ("m60", "+60 min")):
        v = R[k].dropna()
        print(f"  from t0, {lab:8s}: median {v.median()*100:+6.2f}%  "
              f"positive {int((v>0).sum())}/{len(v)}")


if __name__ == "__main__":
    main()
