"""Doc 224 — DK's TradingView indicator "Liquidations" (Mysterysauce, open source; DK 15:41–15:47: it called the 72,850 BTC tap exactly).
Rebuilt from its published method: pivots 5 bars left / 2 right; volume vs its 1000-bar average; leverage tier by how far volume exceeds the
average (100x > +20%, 50x > +10%, 25x > +5%, 10x > +2.5%, 5x > +1.25%); LONG liquidation level = pivot LOW x (1 - long%), SHORT level = pivot
HIGH x (1 + short%) with long% 0.49/1.47/3.38/4.67/6.115 and short% 0.51/1.55/3.70/5.11/6.705 (100x..5x). A level is live from the bar that
CONFIRMS the pivot (2 bars later) until price touches it.
Test (Binance BTC 1-minute 2020-26 -> 15-min bars): every first touch of a LONG level = buy with a limit AT the level (DK's fill). Result after
1h / 4h / 24h (to the bar close) and the worst drop within 4h, vs the same horizons from random bars. Costs: 0.04% round trip (limit + market exit).
Also the SHORT side: first touch of a short level = sell at the level. Halves 2020-22 / 2023-26."""
import warnings; warnings.filterwarnings("ignore")
import sys, numpy as np, pandas as pd
m = pd.read_parquet("data_long/btc_1m.parquet")
d = m.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()
H, L, C, V, IX = d.high.values, d.low.values, d.close.values, d.vol.values, d.index; N = len(d)
avg = pd.Series(V).rolling(1000).mean().values
TIERS = [(100, .20, .0049, .0051), (50, .10, .0147, .0155), (25, .05, .0338, .0370), (10, .025, .0467, .0511), (5, .0125, .06115, .06705)]
def pivots(arr, kind):
    s = pd.Series(arr); w = s.rolling(8, center=False)
    out = []
    for i in range(5, N - 2):
        x = arr[i]; win = arr[i - 5:i + 3]
        if (kind == "low" and x == win.min()) or (kind == "high" and x == win.max()): out.append(i)
    return out
def levels(kind):
    piv = pivots(L if kind == "long" else H, "low" if kind == "long" else "high"); lv = []
    for i in piv:
        if not np.isfinite(avg[i]): continue
        r = V[i] / avg[i] - 1
        for lev, thr, lp, sp in TIERS:
            if r > thr:
                lv.append((i + 2, (L[i] * (1 - lp)) if kind == "long" else (H[i] * (1 + sp)), lev)); break   # highest tier the volume qualifies for
    return lv
def first_touch(lv, kind, max_bars=4 * 24 * 30):
    ev = []
    for start, lvl, lev in lv:
        e = min(N, start + max_bars); seg = L[start:e] if kind == "long" else H[start:e]
        hit = np.nonzero(seg <= lvl)[0] if kind == "long" else np.nonzero(seg >= lvl)[0]
        if len(hit): ev.append((start + hit[0], lvl, lev))
    return ev
def fwd(ev, kind):
    rows = []; side = 1 if kind == "long" else -1
    for j, lvl, lev in ev:
        if j + 96 >= N: continue
        r = {h: side * (C[j + h] / lvl - 1) * 100 - 0.04 for h in (4, 16, 96)}
        mae = side * ((L[j:j + 17].min() if side == 1 else H[j:j + 17].max()) / lvl - 1) * 100
        rows.append((IX[j], lev, r[4], r[16], r[96], mae))
    return pd.DataFrame(rows, columns=["t", "lev", "h1", "h4", "h24", "mae4"])
if __name__ == "__main__" and "cleared" not in sys.argv:
    rng = np.random.default_rng(3); rb = rng.integers(1100, N - 100, 20000)
    base = {h: (C[rb + h] / C[rb] - 1).mean() * 100 for h in (4, 16, 96)}
    print(f"BTC 15-min bars {IX[0].date()}..{IX[-1].date()}; random-bar drift: 1h {base[4]:+.3f}%  4h {base[16]:+.3f}%  24h {base[96]:+.3f}%")
    for kind in ("long", "short"):
        t = fwd(first_touch(levels(kind), kind), kind)
        print(f"\n== {kind.upper()} liquidation levels tapped -> {'BUY' if kind == 'long' else 'SELL'} at the level (after 0.04% costs), n {len(t)}")
        for nm, g in [("all", t), ("2020-22", t[t.t.dt.year <= 2022]), ("2023-26", t[t.t.dt.year >= 2023])] + [(f"{lev}x", t[t.lev == lev]) for lev in (100, 50, 25, 10, 5)]:
            if len(g) < 20: continue
            tt = g.h4.mean() / g.h4.std() * np.sqrt(len(g))
            print(f"   {nm:8s} n{len(g):5d} | 1h {g.h1.mean():+.3f}% | 4h {g.h4.mean():+.3f}% (t {tt:+.2f}, win {100 * (g.h4 > 0).mean():.0f}%) | 24h {g.h24.mean():+.3f}% | worst drop within 4h: median {g.mae4.median():+.2f}%")

# ---- DK 15:52: "The strongest buy signal would be a hit of the lowest level of liquidations, suggesting that 'direction' had been cleared."
# For each tap of a LONG level, count the OTHER long levels still live (confirmed, not yet touched) BELOW the price at that moment.
# 'Cleared' = none left below within 10%. Compared with taps that still have levels below.
def cleared_test():
    lv = levels("long"); ft = first_touch(lv, "long", max_bars=N)
    touch_at = {}; 
    for (start, lvl, lev), ev in zip(lv, [None] * len(lv)): pass
    # map each level to its touch bar (or never)
    tb = []
    for start, lvl, lev in lv:
        seg = np.nonzero(L[start:] <= lvl)[0]; tb.append(start + seg[0] if len(seg) else N + 10)
    S = np.array([s for s, _, _ in lv]); LV = np.array([l for _, l, _ in lv]); TB = np.array(tb); LEV = np.array([v for _, _, v in lv])
    rows = []
    for k in range(len(lv)):
        j = TB[k]
        if j >= N - 100: continue
        live_below = ((S <= j) & (TB > j) & (LV < LV[k]) & (LV > LV[k] * 0.90)).sum()
        side = 1; lvl = LV[k]
        r = {h: (C[j + h] / lvl - 1) * 100 - 0.04 for h in (4, 16, 96)}; mae = (L[j:j + 17].min() / lvl - 1) * 100
        rows.append((IX[j], LEV[k], live_below, r[4], r[16], r[96], mae))
    t = pd.DataFrame(rows, columns=["t", "lev", "below", "h1", "h4", "h24", "mae4"]).drop_duplicates(subset=["t"])   # one event per bar
    print("\n== DK's 'cleared' test: taps of a long level, by how many live long levels remain below (within 10%); one event per 15-min bar")
    for nm, g in [("CLEARED: none left below", t[t.below == 0]), ("1-2 left below", t[t.below.between(1, 2)]), ("3+ left below", t[t.below >= 3]),
                  ("CLEARED, 2020-22", t[(t.below == 0) & (t.t.dt.year <= 2022)]), ("CLEARED, 2023-26", t[(t.below == 0) & (t.t.dt.year >= 2023)])]:
        if len(g) < 10: print(f"   {nm}: n{len(g)}"); continue
        tt = g.h4.mean() / g.h4.std() * np.sqrt(len(g))
        print(f"   {nm:24s} n{len(g):5d} | 1h {g.h1.mean():+.3f}% | 4h {g.h4.mean():+.3f}% (t {tt:+.2f}, win {100 * (g.h4 > 0).mean():.0f}%) | 24h {g.h24.mean():+.3f}% (win {100 * (g.h24 > 0).mean():.0f}%) | median worst dip 4h {g.mae4.median():+.2f}%")
if __name__ == "__main__" and "cleared" in sys.argv: cleared_test()
