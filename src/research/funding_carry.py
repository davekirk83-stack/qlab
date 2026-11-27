"""Funding carry (DK 27 Nov 16:23 "Test all of these apart from 3 and 4", item 2): own BTC/ETH spot and short the same amount of the perpetual,
collecting funding when longs pay shorts (rate > 0) - no bet on direction. Binance USDT-M funding history 2020-26 (data.binance.vision,
8-hourly). Capital = 1.0 spot + 0.5 margin for the short (2x on the short leg, room for a 50% spike before liquidation) = 1.5 per unit.
Costs per round trip (open + close both legs): 0.30% (taker spot 0.1% x2 + perp 0.05% x2). Variants: always on; switched on when the
trailing 7-day average funding annualised > X% and off when it falls under Y%. Returns are % a year on the 1.5 capital."""
import glob, sys, numpy as np, pandas as pd
D = sys.argv[1] if len(sys.argv) > 1 else "."
def load(sym):
    fs = sorted(glob.glob(f"{D}/{sym}-fundingRate-*.csv"))
    x = pd.concat([pd.read_csv(f) for f in fs]); x["t"] = pd.to_datetime(x.calc_time, unit="ms", utc=True)
    return x.set_index("t").last_funding_rate.sort_index()
def run(f, on_x=None, off_y=None, rt_cost=0.003, cap=1.5):
    if on_x is None: inpos = pd.Series(True, index=f.index); switches = 1
    else:
        ann = f.rolling(21).mean() * 3 * 365; st = False; s = []
        for v in ann.values:
            if not st and np.isfinite(v) and v > on_x: st = True
            elif st and np.isfinite(v) and v < off_y: st = False
            s.append(st)
        inpos = pd.Series(s, index=f.index).shift(1).fillna(False)       # decide on the trailing average, earn from the next payment
        switches = int((inpos.astype(int).diff() == 1).sum())
    earn = (f * inpos)
    cost = pd.Series(0.0, index=f.index); starts = inpos & ~inpos.shift(1, fill_value=False); cost[starts] = rt_cost
    net = earn - cost
    yr = net.groupby(net.index.year).sum() / cap * 100; time_in = inpos.groupby(inpos.index.year).mean() * 100
    return yr, time_in, switches
if __name__ == "__main__":
    rows = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        f = load(sym)
        for lab, kw in (("always on", {}), ("on >10%/yr, off <0", dict(on_x=0.10, off_y=0.0)), ("on >15%, off <5%", dict(on_x=0.15, off_y=0.05)),
                        ("on >20%, off <5%", dict(on_x=0.20, off_y=0.05)), ("on >8%, off <3%", dict(on_x=0.08, off_y=0.03))):
            yr, ti, sw = run(f, **kw)
            rows.append(dict(sym=sym, rule=lab, switches=sw, **{f"{y}": round(v, 1) for y, v in yr.items()},
                             avg_yr=round(yr.mean(), 1), last12m=round(yr.iloc[-1], 1), time_in_2026=round(ti.iloc[-1])))
        r7 = f.iloc[-21:].mean() * 3 * 365 * 100; print(f"{sym}: last 7 days funding {r7:+.1f}%/yr, last payment {f.iloc[-1]*100:+.4f}% at {f.index[-1]}")
    R = pd.DataFrame(rows); R.to_csv("runs/research/funding_carry.csv", index=False); pd.set_option("display.width", 300); print(R.to_string(index=False))
