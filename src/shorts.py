"""
THE SHORT SIDE.

DK, 14 Oct: "I'm absolutely okay with you undertaking short trades, either scalp
or swing shorts."

This matters more than it sounds. The regime run found the system stays positive
in bear markets — but only 5-13% of its trades occur there. It is not surviving
falling markets, it is ABSTAINING from them. A long-only breakout system simply
does not fire when nothing is breaking out. All that "works in a bear market"
really meant was "is mostly in cash".

Shorts turn that dead time into trading time, if they work. Whether they do is
not obvious and must not be assumed:

  - markets fall faster than they rise, which helps a short
  - but they drift UP over time, which is a permanent headwind
  - short squeezes produce fat left tails that a 1.5 ATR stop will eat
  - borrow cost is real and is NOT in this backtest (noted in the output)

Mirror of the long spec: entry on a breakdown, stop ABOVE entry, targets below,
TP1 one third at 1R, stop to breakeven-minus after TP1, trail above, same time
stops. Everything is segmented by regime, because a short that only works in a
bear market is still useful but must be labelled as such.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import load_universe, atr, est_cost
from regime import regime_series, is_crypto

PANEL = load_universe()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}
STOP_ATR, TP1_R, TP2_R, TRAIL_ATR, MAX_BARS, BE_OFF = 1.5, 1.0, 3.0, 2.5, 10, 0.10


# ------------------------------------------------------------ short setups
def s_month_low(d):
    pm = d.low.groupby([d.index.year, d.index.month]).transform("min")
    prev = pm.shift(1).groupby([d.index.year, d.index.month]).transform("first")
    return ((d.close < prev) & (d.close.shift(1) >= prev)).astype(float)

def s_swing_low(d, n=20):
    lo = d.low.rolling(n).min().shift(1)
    return ((d.close < lo) & (d.close.shift(1) >= lo)).astype(float)

def s_donchian(d, n=20):
    lo = d.low.rolling(n).min().shift(1)
    return (d.close < lo).astype(float)

def s_bear_flag(d):
    """mirror of the bull flag: sharp drop, tight consolidation, break down."""
    drop = (d.close / d.close.shift(10) - 1) < -0.10
    rng = (d.high.rolling(5).max() - d.low.rolling(5).min()) / d.close
    tight = rng < rng.rolling(50).median() * 0.8
    brk = d.close < d.low.rolling(5).min().shift(1)
    return (drop.shift(5).fillna(False) & tight.shift(1).fillna(False) & brk).astype(float)

def s_pullback_downtrend(d):
    """rally into resistance inside a downtrend — the mirror of the long pullback."""
    down = d.close < d.close.rolling(200).mean()
    rsi = C.s_rsi(d, 2, 10)
    hot = (rsi == 0)          # s_rsi fires on oversold; invert via overbought proxy
    r = d.close.pct_change()
    up3 = (r.rolling(3).sum() > 0.05)
    return (down & up3 & (d.close < d.close.rolling(50).mean())).astype(float)

SHORTS = {
    "month-low breakdown": s_month_low,
    "swing-low breakdown": s_swing_low,
    "donchian 20 low": s_donchian,
    "bear flag": s_bear_flag,
    "rally into downtrend": s_pullback_downtrend,
}


def trade_short(df, entries, cost):
    """Short. Stop ABOVE entry, targets BELOW. Mirror of the long management."""
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    SH = df.high.rolling(10).max().values
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
    for i in idx:
        if i <= last or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        px = O[i + 1]
        if not (px == px) or px <= 0:
            continue
        atr_stop = px + STOP_ATR * a
        stop = min(atr_stop, SH[i] * 1.005) if SH[i] == SH[i] else atr_stop
        if stop <= px:
            stop = atr_stop
        risk = stop - px
        if risk <= 0:
            continue
        tp1, tp2 = px - TP1_R * risk, px - TP2_R * risk
        filled, pnl, trough, ex = 0.0, 0.0, px, None
        cur = stop
        for j in range(i + 1, min(i + 1 + MAX_BARS, len(df))):
            if H[j] >= cur:                       # stopped out
                pnl += (1 - filled) * (1 - cur / px); ex = j; break
            if filled < 0.34 and L[j] <= tp1:
                pnl += (1 / 3) * (1 - tp1 / px); filled = 1 / 3
                cur = min(cur, px - BE_OFF * risk - cost * px)
            if filled < 0.67 and L[j] <= tp2:
                pnl += (1 / 3) * (1 - tp2 / px); filled = 2 / 3
            if filled >= 0.66:
                tr = trough + TRAIL_ATR * a
                if H[j] >= tr and tr < cur:
                    pnl += (1 - filled) * (1 - tr / px); ex = j; break
            trough = min(trough, L[j])
        if ex is None:
            j = min(i + MAX_BARS, len(df) - 1)
            pnl += (1 - filled) * (1 - Cl[j] / px); ex = j
        out.append(dict(ret=pnl - cost, bars=max(ex - i, 1), i=i))
        last = ex
    return out


def summarise(rows, label):
    if len(rows) < 60:
        return None
    r = np.array([x["ret"] for x in rows]); b = np.array([x["bars"] for x in rows])
    exp, mb = float(r.mean()), float(b.mean())
    ann = (1 + exp) ** (252 / mb) - 1 if exp > -1 else -1
    se = r.std() / np.sqrt(len(r))
    return dict(label=label, n=len(r), exp=exp, bars=mb, ann=ann,
                win=float((r > 0).mean()), t=float(exp / se) if se > 0 else 0.0,
                worst=float(r.min()), p05=float(np.percentile(r, 5)))


def line(d):
    print(f"  {d['label']:24s} n={d['n']:5d} exp {d['exp']*100:+7.3f}% bars {d['bars']:4.1f} "
          f"ANN {d['ann']*100:+9.1f}% win {d['win']*100:5.1f}% t={d['t']:+5.2f} "
          f"worst {d['worst']*100:+7.1f}%")


def main():
    print("THE SHORT SIDE — mirror of spec v1.1\n")
    print("  NOTE: borrow/funding cost is NOT modelled. On crypto perps funding is")
    print("  usually paid BY longs TO shorts in a bull market, which would help a")
    print("  short; in equities borrow is a cost. Treat these as pre-borrow.\n")

    btc, spy = PANEL.get("BTCUSD"), PANEL.get("SPY")
    rb = regime_series(btc) if btc is not None else None
    rs = regime_series(spy) if spy is not None else None

    allrows = {}
    for s, df in PANEL.items():
        if len(df) < 300:
            continue
        reg = (rb if is_crypto(s, df) else rs)
        if reg is None:
            continue
        reg = reg.reindex(df.index).ffill()
        for name, fn in SHORTS.items():
            try:
                e = fn(df)
                e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
            except Exception:
                continue
            if e.sum() == 0:
                continue
            for r in trade_short(df, e, COSTS[s]):
                r["regime"] = reg.iloc[r["i"]] if r["i"] < len(reg) else None
                r["crypto"] = is_crypto(s, df)
                allrows.setdefault(name, []).append(r)

    print("=" * 104)
    print("A.  SHORT SETUPS, WHOLE SAMPLE")
    print("=" * 104)
    keep = []
    for name in SHORTS:
        d = summarise(allrows.get(name, []), name)
        if d:
            line(d); keep.append((name, d))

    print()
    print("=" * 104)
    print("B.  BY REGIME — the whole point. Does shorting pay when the tide is OUT?")
    print("=" * 104)
    for name, _ in keep:
        t = pd.DataFrame(allrows[name])
        print(f"\n  {name}")
        for rg in ("BULL", "FLAT", "BEAR"):
            g = t[t.regime == rg]
            d = summarise(g.to_dict("records"), f"    {rg}")
            if d:
                line(d)
            else:
                print(f"      {rg:6s} n={len(g)} — too few")

    print()
    print("=" * 104)
    print("C.  CRYPTO vs NON-CRYPTO")
    print("=" * 104)
    for name, _ in keep:
        t = pd.DataFrame(allrows[name])
        a = summarise(t[t.crypto].to_dict("records"), f"{name} / crypto")
        b = summarise(t[~t.crypto].to_dict("records"), f"{name} / non-crypto")
        if a:
            line(a)
        if b:
            line(b)

    C.ledger_bump(len(SHORTS) * 6, "short side, regime-segmented")


if __name__ == "__main__":
    main()
