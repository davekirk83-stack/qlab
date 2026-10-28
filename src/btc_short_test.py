"""Doc 159 — BTC and ETH directional shorts, traded as intended (DK 28 Oct: "I'm still not convinced by the 'no bitcoin short' rule" -> "Yes").
Pre-registered 28 Oct 2026 before any result. Costs 0.10% per side; funding ignored (on perps, shorts usually RECEIVE funding on BTC —
doc 75: +6.2%/yr — so ignoring it is conservative for shorts).
 S1 DEATH-CROSS (book 4's exact rules, doc 82) on BTC/ETH 4h (Binance spot 2020-2026): EMA20 > EMA50, gap < 0.25 ATR14 and shrinking for
    3 bars -> short at the close; stop 3 x ATR(entry) above the lowest low since entry; 180-bar cap.
 S2 TREND-DOWN (daily, 2015/16-2026, Coinbase): short at the close when close < SMA200 AND close < close 60 days ago; cover at the close
    when either fails. Position held day to day.
 S3 BREAKDOWN (daily): while close < SMA200, short the close below the prior 20-day low; stop 2 x ATR14 above the lowest close since
    entry (trailing); exit also on a close above the prior 10-day high.
CONTROLS (200 draws): random short entries on days/bars in the SAME regime (S1: any 4h bar; S2/S3: close < SMA200) with identical
    holding/exit rules (S1, S3) or identical episode lengths (S2). Plus long-hold drift for scale.
Reported overall and by period: 2018, 2022, 2025-26, everything else. Trials 3 setups x 2 coins = 6."""
import numpy as np, pandas as pd
COST = 0.001
def daily(sym):
    d = pd.read_csv(f"data_daily/{sym}USD.csv"); d["t"] = pd.to_datetime(d.t, unit="ms")
    return d.set_index("t").sort_index()[["open", "high", "low", "close"]].astype(float)
def h4(sym):
    d = pd.read_csv(f"data_bnb/{sym}USDT_spot_15m.csv", parse_dates=["t"]).set_index("t")
    return d.resample("4h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def atr(d, n=14):
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().bfill().values
PER = lambda t: "2018" if t.year == 2018 else "2022" if t.year == 2022 else "2025-26" if t.year >= 2025 else "other"
def s1_trades(d, entries=None):
    C, H, L = d.close.values, d.high.values, d.low.values; a = atr(d); n = len(C)
    ef = d.close.ewm(span=20, adjust=False).mean().values; es = d.close.ewm(span=50, adjust=False).mean().values
    diff = ef - es; gap = np.abs(diff) / np.maximum(a, 1e-12)
    conv = (gap < np.roll(gap, 1)) & (np.roll(gap, 1) < np.roll(gap, 2))
    sig = (diff > 0) & (gap < 0.25) & conv & (np.roll(diff, 1) > 0); sig &= ~np.roll(sig, 1); sig[:60] = False
    idx = np.flatnonzero(sig[:-1]) if entries is None else entries
    out = []; busy = -1
    for i in idx:
        if i <= busy: continue
        e = C[i]; best = L[i]; at = a[i]; px = None
        for j in range(i + 1, min(i + 181, n)):
            best = min(best, L[j]); stop = best + 3 * at
            if H[j] >= stop: px = stop; break
        else: j = min(i + 180, n - 1); px = C[j]
        out.append((d.index[i], e * (1 - COST) / (px * (1 + COST)) - 1, j - i)); busy = j
    return out
def s3_trades(d, entries=None):
    C, H, L = d.close.values, d.high.values, d.low.values; a = atr(d); n = len(C)
    sma = d.close.rolling(200).mean().values; lo20 = d.low.rolling(20).min().shift(1).values; hi10 = d.high.rolling(10).max().shift(1).values
    sig = (C < sma) & (C < lo20)
    idx = np.flatnonzero(sig[:-1]) if entries is None else entries
    out = []; busy = -1
    for i in idx:
        if i <= busy or i < 200: continue
        e = C[i]; best = C[i]; px = None
        for j in range(i + 1, n):
            best = min(best, C[j]); stop = best + 2 * a[j]
            if H[j] >= stop: px = stop; break
            if C[j] > hi10[j]: px = C[j]; break
        else: j = n - 1; px = C[j]
        out.append((d.index[i], e * (1 - COST) / (px * (1 + COST)) - 1, j - i)); busy = j
    return out
def s2_episodes(d):
    c = d.close; sig = ((c < c.rolling(200).mean()) & (c < c.shift(60))).fillna(False).values
    r = c.pct_change().fillna(0).values; out = []; i = 200; n = len(c)
    while i < n - 1:
        if sig[i]:
            j = i
            while j < n - 1 and sig[j]: j += 1
            ret = np.prod(1 - r[i + 1:j + 1]) * (1 - COST) ** 2 - 1      # short from close i to close j
            out.append((d.index[i], ret, j - i)); i = j
        else: i += 1
    return out
def summary(tr):
    if not tr: return "n0"
    r = np.array([x[1] for x in tr]); by = {}
    for t, x, _ in tr: by.setdefault(PER(t), []).append(x)
    return (f"n{len(r)} win {100*(r>0).mean():.0f}% mean {100*r.mean():+.2f}% total {100*r.sum():+.0f}% | " +
            " ".join(f"{k}: {100*np.sum(v):+.0f}% (n{len(v)})" for k, v in sorted(by.items())))
lines = []
for sym in ("BTC", "ETH"):
    d4 = h4(sym); dd = daily(sym)
    for name, fn, d, regime in (("S1 death-cross 4h", s1_trades, d4, None), ("S3 breakdown daily", s3_trades, dd, "below")):
        real = fn(d); m = np.mean([x[1] for x in real]) if real else np.nan
        C = d.close.values; sma = d.close.rolling(200).mean().values
        pool = np.flatnonzero((C < sma) if regime == "below" else np.ones(len(C), bool))
        pool = pool[(pool > 200) & (pool < len(C) - 2)]
        ms = []
        for k in range(200):
            rng = np.random.default_rng(k); pick = np.sort(rng.choice(pool, min(len(real) * 2, len(pool)), replace=False))
            t = fn(d, pick)[:len(real)]; ms.append(np.mean([x[1] for x in t]) if t else np.nan)
        ms = np.array(ms)
        lines.append(f"{sym} {name}: {summary(real)}\n   random shorts same regime/exits: median {100*np.nanmedian(ms):+.2f}%/trade, setup beats {100*np.nanmean(ms < m):.0f}%")
        print(lines[-1], flush=True)
    ep = s2_episodes(dd); m = np.mean([x[1] for x in ep])
    C = dd.close.values; r = dd.close.pct_change().fillna(0).values; sma = dd.close.rolling(200).mean().values
    pool = np.flatnonzero(C < sma); pool = pool[(pool > 200)]
    ms = []
    for k in range(200):
        rng = np.random.default_rng(k); vals = []
        for _, _, L in ep:
            i = int(rng.choice(pool)); j = min(i + L, len(C) - 1); vals.append(np.prod(1 - r[i + 1:j + 1]) * (1 - COST) ** 2 - 1)
        ms.append(np.mean(vals))
    ms = np.array(ms)
    lines.append(f"{sym} S2 trend-down daily (episodes): {summary(ep)}\n   random same-length shorts while below SMA200: median {100*np.median(ms):+.2f}%/episode, setup beats {100*(ms < m).mean():.0f}%")
    print(lines[-1], flush=True)
    bh = {p: 100 * (dd.close[dd.index.map(PER) == p].iloc[-1] / dd.close[dd.index.map(PER) == p].iloc[0] - 1) for p in ("2018", "2022", "2025-26")}
    lines.append(f"{sym} price change for scale: " + " ".join(f"{k} {v:+.0f}%" for k, v in bh.items())); print(lines[-1], flush=True)
open("runs/btc_short_test.txt", "w").write("\n".join(lines) + "\n")
