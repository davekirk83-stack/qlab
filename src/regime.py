"""
REGIME SEGMENTATION — the test that decides whether any of this is real.

DK, 14 Oct: "The only issue with Crypto (and S&P) is that it has been in a raging
bull the last two or more years, so historical 'normal' patterns may be misleading."

That is the single most dangerous confound in the whole project and it has been
carried as a written caveat rather than a measurement. This run measures it.

A long-only breakout system tested across a decade-long bull market will look
excellent for a reason that has nothing to do with the system: the tide was
rising. The only way to tell skill from tide is to cut the record by regime and
look at what happens when the tide is out.

Regimes are defined on a BENCHMARK, not on the instrument being traded, so the
classification cannot peek at the trade's own outcome:

    BULL   benchmark above its 200d MA and the 200d MA rising
    BEAR   benchmark below its 200d MA and the 200d MA falling
    FLAT   everything else (chop, transitions)

Benchmark is BTC for crypto names and SPY for everything else, each lagged one
bar so the label at bar i uses only information available at bar i-1.

Reported per regime:
    expectancy, win rate, annualised return on deployed capital, n
    and the matched buy-and-hold of the same benchmark over the same bars,
    because the question is not "did it make money" but "did it beat the tide".
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}
MGMT = dict(stop_atr=1.5, tp1_r=1.0, tp2_r=3.0, trail_atr=2.5,
            max_bars=10, be_offset_r=0.10)

CRYPTO_HINTS = ("BTC", "ETH", "SOL", "ADA", "XRP", "LTC", "DOGE", "AVAX", "LINK")


def is_crypto(sym, df):
    if any(h in sym.upper() for h in CRYPTO_HINTS):
        return True
    # altcoin panel is all crypto; majors are the named FX/metal/equity set
    return sym.upper() not in {"SPY", "GCUSD", "SIUSD", "EURUSD", "GBPUSD",
                               "USDJPY", "AUDUSD"}


def regime_series(bench):
    ma = bench.close.rolling(200).mean()
    slope = ma.diff(20)
    r = pd.Series("FLAT", index=bench.index)
    r[(bench.close > ma) & (slope > 0)] = "BULL"
    r[(bench.close < ma) & (slope < 0)] = "BEAR"
    return r.shift(1)          # label at bar i uses data to i-1


def trades_with_regime(entry_fn, label):
    btc = PANEL.get("BTCUSD"); spy = PANEL.get("SPY")
    rb = regime_series(btc) if btc is not None else None
    rs = regime_series(spy) if spy is not None else None
    rows = []
    for s, df in PANEL.items():
        try:
            e = entry_fn(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum() == 0:
            continue
        reg = (rb if is_crypto(s, df) else rs)
        if reg is None:
            continue
        reg = reg.reindex(df.index).ffill()
        A = atr(df).values
        H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
        SL = df.low.rolling(10).min().values
        cost = COSTS[s]
        idx = np.flatnonzero(e.values > 0)
        last = -1
        for i in idx:
            if i <= last or i + 1 >= len(df):
                continue
            a = A[i]
            if not (a == a) or a <= 0:
                continue
            px = O[i + 1]
            if not (px == px) or px <= 0:
                continue
            stop = max(px - MGMT["stop_atr"] * a, SL[i] * 0.995) if SL[i] == SL[i] \
                else px - MGMT["stop_atr"] * a
            if stop >= px:
                stop = px - MGMT["stop_atr"] * a
            risk = px - stop
            if risk <= 0:
                continue
            tp1, tp2 = px + risk, px + 3 * risk
            filled, pnl, peak, ex = 0.0, 0.0, px, None
            cur = stop
            for j in range(i + 1, min(i + 11, len(df))):
                if L[j] <= cur:
                    pnl += (1 - filled) * (cur / px - 1); ex = j; break
                if filled < 0.34 and H[j] >= tp1:
                    pnl += (1 / 3) * (tp1 / px - 1); filled = 1 / 3
                    cur = max(cur, px + 0.10 * risk + cost * px)
                if filled < 0.67 and H[j] >= tp2:
                    pnl += (1 / 3) * (tp2 / px - 1); filled = 2 / 3
                if filled >= 0.66:
                    tr = peak - 2.5 * a
                    if L[j] <= tr and tr > cur:
                        pnl += (1 - filled) * (tr / px - 1); ex = j; break
                peak = max(peak, H[j])
            if ex is None:
                j = min(i + 10, len(df) - 1)
                pnl += (1 - filled) * (Cl[j] / px - 1); ex = j
            rg = reg.iloc[i] if i < len(reg) else None
            if isinstance(rg, str):
                rows.append(dict(ret=pnl - cost, bars=max(ex - i, 1),
                                 regime=rg, date=df.index[i], sym=s,
                                 crypto=is_crypto(s, df)))
            last = ex
    return pd.DataFrame(rows), label


def report(t, label):
    print("=" * 94)
    print(f"  {label}   n={len(t):,}")
    print("=" * 94)
    print(f"  {'regime':8s} {'n':>7} {'share':>7} {'exp/trade':>11} {'win%':>7} "
          f"{'avg bars':>9} {'ANNUALISED':>12}")
    for rg in ("BULL", "FLAT", "BEAR"):
        g = t[t.regime == rg]
        if len(g) < 30:
            print(f"  {rg:8s} {len(g):7d}   (too few to report)")
            continue
        exp, mb = g.ret.mean(), g.bars.mean()
        ann = (1 + exp) ** (252 / mb) - 1 if exp > -1 else -1
        se = g.ret.std() / np.sqrt(len(g))
        print(f"  {rg:8s} {len(g):7d} {len(g)/len(t)*100:6.1f}% {exp*100:+10.3f}% "
              f"{float((g.ret>0).mean())*100:6.1f}% {mb:9.1f} {ann*100:+11.1f}%"
              f"   t={exp/se if se>0 else 0:+.2f}")
    print()


def benchmark_by_regime():
    """What did simply HOLDING do in each regime? The tide, measured."""
    print("=" * 94)
    print("  THE TIDE — buy-and-hold forward 10-bar return by regime")
    print("=" * 94)
    for name, sym in (("BTC (crypto benchmark)", "BTCUSD"), ("SPY (everything else)", "SPY")):
        b = PANEL.get(sym)
        if b is None:
            continue
        reg = regime_series(b)
        fwd = b.close.shift(-10) / b.close - 1
        print(f"  {name}")
        for rg in ("BULL", "FLAT", "BEAR"):
            m = reg == rg
            if m.sum() < 30:
                continue
            print(f"     {rg:6s} {int(m.sum()):6d} bars ({m.mean()*100:4.1f}% of history)  "
                  f"mean 10-bar hold {fwd[m].mean()*100:+7.2f}%")
        print()


def main():
    print("REGIME SEGMENTATION — does the system work when the tide is out?\n")
    print(f"  {len(PANEL)} instruments · spec v1.1 management · benchmark-defined regimes")
    print("  regime label is lagged one bar and taken from BTC/SPY, never the")
    print("  instrument being traded.\n")

    benchmark_by_regime()

    for fn, label in ((LV.l_break_prior_month_high, "month-high break (incumbent)"),
                      (lambda d: LV.l_swing_break(d, 20), "swing break"),
                      (lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
                       "donchian 20")):
        t, lab = trades_with_regime(fn, label)
        if len(t):
            report(t, lab)

    # the decisive cut: crypto in the recent bull vs everything before it
    t, _ = trades_with_regime(LV.l_break_prior_month_high, "x")
    if len(t):
        t["date"] = pd.to_datetime(t["date"])
        print("=" * 94)
        print("  THE SPECIFIC WORRY — crypto, recent bull vs everything before")
        print("=" * 94)
        c = t[t.crypto]
        for lab, part in (("crypto 2024-09 onward (the raging bull)", c[c.date >= "2024-09-01"]),
                          ("crypto before 2024-09", c[c.date < "2024-09-01"]),
                          ("NON-crypto, whole history", t[~t.crypto])):
            if len(part) < 30:
                print(f"  {lab:42s} n={len(part)} — too few")
                continue
            exp, mb = part.ret.mean(), part.bars.mean()
            ann = (1 + exp) ** (252 / mb) - 1 if exp > -1 else -1
            se = part.ret.std() / np.sqrt(len(part))
            print(f"  {lab:42s} n={len(part):6d}  exp {exp*100:+7.3f}%  "
                  f"ANN {ann*100:+9.1f}%  win {float((part.ret>0).mean())*100:5.1f}%  "
                  f"t={exp/se if se>0 else 0:+.2f}")

    C.ledger_bump(12, "regime segmentation")


if __name__ == "__main__":
    main()
