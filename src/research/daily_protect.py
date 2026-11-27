"""DK 27 Nov: winning trades that ended as losses. Live TPS US500 18 Nov was up ~71 pts (about +1.1%) the next day, then hit the stop (-53);
RSI4L was up 24 pts then -341. Tests profit protection / loss avoidance on the daily dip books over 2000-2026, the six live markets
(US500, NQ, Wall St, DAX, FTSE, gold), same rules as the live books (src/ig_daily_books.py), close fills + IG costs (0.03%) + 6%/yr funding.
TPS: ladder 10/20/30/40% on lower closes; exit RSI(2) > 70, 30 days, or close 15% under the average. Measured as % of the ladder budget.
RSI4 (< 25) / RSI4L (< 35): above the 200-day; exit RSI(4) > 55 or 10 days; stop 3 ATR (intraday). Measured in ATR."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import market_search_2 as M2, market_search_4 as M4
MK = ("SPX", "NDX", "DJI", "DAX", "FTSE", "GOLD"); COST, FUND = 0.0003, 0.06

def rsi(c, n):
    d = c.diff(); u = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); v = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100 / (1 + u / v)

def tps(d, lock=None, tp=None, kill=0.15, giveback=None):
    """lock = once a close is >= avg*(1+lock), exit if a later close is back at/below the average (breakeven on close).
       tp = exit at the close once close >= avg*(1+tp). giveback = once up >= 1%, exit if the close gives back this share of the best close gain."""
    C = d.close.values; r = M4.rsi2(d.close).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 1:
        if not (C[i] > ma[i] and r[i] < 25 and r[i - 1] < 25): i += 1; continue
        qty = spent = 0.0; last = None; k = 0; j0 = i; j = i; locked = False; best = 0.0
        while j < n:
            if k < 4 and (last is None or C[j] < last):
                w = (0.1, 0.2, 0.3, 0.4)[k]; qty += w / (C[j] * (1 + COST)); spent += w; last = C[j]; k += 1
            avg = spent / qty; g = C[j] / avg - 1; best = max(best, g)
            if lock and g >= lock: locked = True
            done = r[j] > 70 or (j - j0) >= 30 or C[j] <= avg * (1 - kill)
            if tp and g >= tp: done = True
            if locked and g <= 0.0005: done = True
            if giveback and best >= 0.01 and g <= best * (1 - giveback): done = True
            if done and j > j0:
                val = qty * C[j] * (1 - COST) - spent * FUND / 365 * 1.4 * (j - j0) * 0.5
                out.append((d.index[j0], (val - spent) / spent)); break
            j += 1
        i = j + 1
    return out

def rsi4(d, th, be=None, tp=None, trail=None, tstop=None):
    """be = stop to entry once a close is >= entry + be ATR; tp = sell at entry + tp ATR (intraday high); trail = after +1 ATR close,
    stop trails `trail` ATR under the highest close; tstop = exit at the close after N days if still below entry."""
    C, H, L, O = d.close.values, d.high.values, d.low.values, d.open.values
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs())); A = tr.rolling(20).mean().values
    r = rsi(d.close, 4).values; ma = d.close.rolling(200).mean().values; out = []; i = 201; n = len(C)
    while i < n - 2:
        if not (C[i] > ma[i] and r[i] < th): i += 1; continue
        e = O[i + 1] * (1 + COST); a = A[i]; st = e - 3 * a; hc = e; x = None; j = i + 1
        while j < n:
            if L[j] <= st: x = min(st, O[j]) if j > i + 1 else st; break
            if tp and H[j] >= e + tp * a: x = max(e + tp * a, O[j]); break
            if r[j] > 55 or (j - i) >= 10: x = C[j]; break
            if tstop and (j - i) >= tstop and C[j] < e: x = C[j]; break
            hc = max(hc, C[j])
            if be and C[j] >= e + be * a: st = max(st, e)
            if trail and hc >= e + a: st = max(st, hc - trail * a)
            j += 1
        if x is None: break
        out.append((d.index[i], (x * (1 - COST) - e) / a)); i = j + 1
    return out

def rep(name, E):
    t = pd.DataFrame(E, columns=["t", "v"]).sort_values("t"); h = len(t) // 2; y = t.groupby(t.t.dt.year).v.sum()
    return dict(variant=name, n=len(t), win=(t.v > 0).mean(), mean=t.v.mean(), h1=t.v[:h].mean(), h2=t.v[h:].mean(),
                last5=t[t.t.dt.year >= 2022].v.mean(), yrs_pos=f"{(y>0).sum()}/{len(y)}", worst_yr=y.min(), total=t.v.sum())

if __name__ == "__main__":
    D = {k: M2.daily(k, COST, 0) for k in MK}; rows = []
    for name, kw in (("TPS live rule", {}), ("TPS lock at +1%", {"lock": 0.01}), ("TPS lock at +2%", {"lock": 0.02}),
                     ("TPS take profit +2%", {"tp": 0.02}), ("TPS take profit +3%", {"tp": 0.03}), ("TPS give back 50% of best", {"giveback": 0.5}),
                     ("TPS kill -10%", {"kill": 0.10}), ("TPS kill -8%", {"kill": 0.08})):
        E = []; [E.extend(tps(D[k], **kw)) for k in MK]; rows.append(rep(name, E)); print(rows[-1], flush=True)
    for book, th in (("RSI4", 25), ("RSI4L", 35)):
        for name, kw in (("live rule", {}), ("BE at +1 ATR", {"be": 1}), ("BE at +1.5 ATR", {"be": 1.5}), ("TP +1.5 ATR", {"tp": 1.5}),
                         ("TP +2 ATR", {"tp": 2}), ("trail 1.5 ATR", {"trail": 1.5}), ("trail 2 ATR", {"trail": 2}), ("time stop 3d", {"tstop": 3}),
                         ("time stop 5d", {"tstop": 5})):
            E = []; [E.extend(rsi4(D[k], th, **kw)) for k in MK]; rows.append(rep(f"{book} {name}", E)); print(rows[-1], flush=True)
    r = pd.DataFrame(rows); r.to_csv("runs/research/daily_protect.csv", index=False)
    pd.set_option("display.width", 250); print(r.round(4).to_string(index=False))
