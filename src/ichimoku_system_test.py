"""Doc 162 — the Ichimoku SYSTEM as practitioners trade it (rule 188; DK 29 Oct: "Yes, and find expert advice about it online").
Pre-registered before any result. Expert rules gathered (H Markets guide, TradingView crypto-settings note, standard Hosoda practice):
trade only with the cloud; a TK cross counts only on the cloud's side; Chikou must confirm; trail/exit on the Kijun (not Tenkan);
avoid signals inside the cloud, into a flat Senkou B, or with a thin cloud; weekly for bias; crypto uses doubled 20/60/120/30.
CLOUD (causal): the cloud at bar t is Span A/B computed at t-D (as plotted); "future cloud" = spans computed at t.
LONG systems (mirrored SHORT versions reported too, since the BTC short ban is lifted, doc 159):
 H1 STRONG TK: Tenkan crosses above Kijun while close > cloud top, Chikou (close) > close D bars ago, future cloud bullish (A > B).
 H2 KUMO BREAKOUT: close crosses above the cloud top, Chikou clear, future cloud bullish, cloud not thin (thickness >= 0.5 ATR).
 H3 BREAKOUT + RETEST: after an H2 breakout, the first bar within 10 that touches the cloud top and closes above it.
 Entry at the next open. Exit at the next open after a close below the Kijun. Variant W: daily trades only when the WEEKLY close is above
 the weekly cloud (bias filter).
MARKETS: BTC, ETH (Coinbase daily from 2015/16; settings 9/26/52/26 and 20/60/120/30), SPY (1993), QQQ (1999) daily (9/26/52/26),
 and the same on WEEKLY bars. Costs: crypto 0.10%/side, ETFs 0.05%/side. Dev: crypto to 2022, ETFs to 2018; holdout after.
CONTROLS: (a) random entries on days already above the cloud, same Kijun exit, same count (200 draws) - is the ENTRY worth anything?
 (b) buy-and-hold over the same period.  Trials: 3 systems x 2 sides x markets/settings - reported in full."""
import numpy as np, pandas as pd
def load(sym):
    if sym in ("BTC", "ETH"):
        d = pd.read_csv(f"data_daily/{sym}USD.csv"); d["t"] = pd.to_datetime(d.t, unit="ms"); d = d.set_index("t").sort_index()
        return d[["open", "high", "low", "close"]].astype(float)
    d = pd.read_csv(f"data_stk/{sym}.csv", parse_dates=["t"]).set_index("t").sort_index()
    return d[["open", "high", "low", "close"]].astype(float)
def weekly(d): return d.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def ichi(d, T, K, B, D):
    mid = lambda n: (d.high.rolling(n).max() + d.low.rolling(n).min()) / 2
    ten, kij = mid(T), mid(K); a_now = (ten + kij) / 2; b_now = mid(B)
    A, Bc = a_now.shift(D), b_now.shift(D)
    tr = pd.concat([d.high - d.low, (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    return dict(ten=ten.values, kij=kij.values, top=np.maximum(A, Bc).values, bot=np.minimum(A, Bc).values,
                fut_bull=(a_now > b_now).values, fut_bear=(a_now < b_now).values, chik_up=(d.close > d.close.shift(D)).values,
                chik_dn=(d.close < d.close.shift(D)).values, thick=((np.maximum(A, Bc) - np.minimum(A, Bc)) / tr.rolling(14).mean()).values)
def signals(d, I, side):
    C = d.close.values; n = len(C); s = side
    ten, kij, top, bot = I["ten"], I["kij"], I["top"], I["bot"]
    above = C > top if s == 1 else C < bot
    chik = I["chik_up"] if s == 1 else I["chik_dn"]; fut = I["fut_bull"] if s == 1 else I["fut_bear"]
    tk = (ten > kij) & (np.roll(ten, 1) <= np.roll(kij, 1)) if s == 1 else (ten < kij) & (np.roll(ten, 1) >= np.roll(kij, 1))
    edge = top if s == 1 else bot
    brk = (C > top) & (np.roll(C, 1) <= np.roll(top, 1)) if s == 1 else (C < bot) & (np.roll(C, 1) >= np.roll(bot, 1))
    h1 = tk & above & chik & fut
    h2 = brk & chik & fut & (I["thick"] >= 0.5)
    h3 = np.zeros(n, bool)
    for i in np.flatnonzero(h2):
        for j in range(i + 1, min(i + 11, n)):
            touch = d.low.values[j] <= edge[j] if s == 1 else d.high.values[j] >= edge[j]
            ok = C[j] > edge[j] if s == 1 else C[j] < edge[j]
            if touch and ok: h3[j] = True; break
            if not (C[j] > edge[j] if s == 1 else C[j] < edge[j]): break
    for x in (h1, h2, h3): x[:max(200, 1)] = False
    return dict(H1=h1, H2=h2, H3=h3), above
def trades(d, I, entries, side, cost):
    O, C, kij = d.open.values, d.close.values, I["kij"]; n = len(C); out = []; busy = -1
    for i in entries:
        if i <= busy or i + 1 >= n: continue
        e = O[i + 1]
        for j in range(i + 1, n - 1):
            if (side == 1 and C[j] < kij[j]) or (side == -1 and C[j] > kij[j]): x = O[j + 1]; break
        else: j = n - 1; x = C[j]
        r = (x / e - 1) * side - 2 * cost; out.append((d.index[i], r, j - i)); busy = j
    return out
def stats(tr, years):
    if not tr: return "n0"
    r = np.array([t[1] for t in tr]); eq = np.cumprod(1 + r); cagr = eq[-1] ** (1 / years) - 1
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return f"n{len(r):3} win {100*(r>0).mean():3.0f}% mean {100*r.mean():+5.1f}% CAGR {100*cagr:+5.1f}% (compounded per trade) maxDD {100*dd:.0f}% median hold {np.median([t[2] for t in tr]):.0f} bars"
lines = []
MK = [("BTC", "crypto", 0.001), ("ETH", "crypto", 0.001), ("SPY", "etf", 0.0005), ("QQQ", "etf", 0.0005)]
for sym, kind, cost in MK:
    dd0 = load(sym); split = pd.Timestamp("2023-01-01" if kind == "crypto" else "2019-01-01")
    for tfname, d in (("daily", dd0), ("weekly", weekly(dd0))):
        sets = [("9/26/52/26", (9, 26, 52, 26))] + ([("20/60/120/30", (20, 60, 120, 30))] if kind == "crypto" else [])
        for sname, (T, K, B, D) in sets:
            I = ichi(d, T, K, B, D)
            wk_ok = None
            if tfname == "daily":
                w = weekly(dd0); Iw = ichi(w, T, K, B, D)
                wk_up = pd.Series(w.close.values > Iw["top"], index=w.index).shift(1).reindex(d.index, method="ffill").fillna(False).values
                wk_dn = pd.Series(w.close.values < Iw["bot"], index=w.index).shift(1).reindex(d.index, method="ffill").fillna(False).values
            for side in (1, -1):
                sig, above = signals(d, I, side)
                for nm in ("H1", "H2", "H3"):
                    for filt in ([False, True] if tfname == "daily" else [False]):
                        m = sig[nm] & ((wk_up if side == 1 else wk_dn) if filt else True)
                        row = []
                        for seg, msk in (("dev", d.index < split), ("hold", d.index >= split)):
                            ent = np.flatnonzero(m & msk)[:-1] if (m & msk).any() else []
                            tr = trades(d, I, ent, side, cost)
                            yrs = max(msk.sum() / (365 if (kind == "crypto" and tfname == "daily") else 252 if tfname == "daily" else 52), 0.5)
                            # control: random entries on bars already on the cloud's side, same exit, same count
                            pool = np.flatnonzero(above & msk); pool = pool[pool > 200]
                            mr = np.mean([t[1] for t in tr]) if tr else np.nan; ctl = []
                            for k in range(200):
                                if not len(pool) or not tr: break
                                rng = np.random.default_rng(k); pick = np.sort(rng.choice(pool, min(len(tr) * 3, len(pool)), replace=False))
                                ct = trades(d, I, pick, side, cost)[:len(tr)]; ctl.append(np.mean([t[1] for t in ct]) if ct else np.nan)
                            ctl = np.array(ctl)
                            bh = (d.close[msk].iloc[-1] / d.close[msk].iloc[0]) ** (1 / yrs) - 1 if msk.sum() > 2 else np.nan
                            row.append(f"{seg}: {stats(tr, yrs)} | random-entry same regime {100*np.nanmedian(ctl):+.1f}% (beats {100*np.nanmean(ctl < mr):.0f}%) | B&H CAGR {100*bh:+.0f}%" if tr else f"{seg}: n0")
                        lab = f"{sym} {tfname} {sname} {'LONG ' if side == 1 else 'SHORT'} {nm}{'+W' if filt else '  '}"
                        lines.append(lab + "\n     " + "\n     ".join(row)); print(lines[-1], flush=True)
open("runs/ichimoku_system_test.txt", "w").write("\n".join(lines) + "\n")
