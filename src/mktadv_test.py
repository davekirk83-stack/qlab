"""Market Advisory V19.1 (DK's Pine strategy) replicated and tested against a matched random control.
Faithful to the script: score components, gates, confirm=1 closed bar, stop = min(close-1.5 ATR, 8-bar swing low), target 2R,
no time exit (cap 500 bars), 0.02% commission each way. NWE boost: in the script it only exists on the last bar (never in history);
tested OFF (as the Strategy Tester sees it) and ON with a causal one-sided kernel. Leledc boost: as written (checks the OLDEST 5
levels) and fixed (newest 5)."""
import sys, numpy as np, pandas as pd
def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up/dn.replace(0, np.nan))
def dmi(h, l, c, n=14):
    up = h.diff(); dn = -l.diff(); plus = np.where((up > dn) & (up > 0), up, 0.0); minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    dip = 100*pd.Series(plus, index=h.index).ewm(alpha=1/n, adjust=False).mean()/atr; dim = 100*pd.Series(minus, index=h.index).ewm(alpha=1/n, adjust=False).mean()/atr
    dx = 100*(dip-dim).abs()/(dip+dim).replace(0, np.nan); adx = dx.ewm(alpha=1/n, adjust=False).mean()
    return dip, dim, adx, tr.rolling(n).mean()
def nw_causal(c, h=8.0, span=60):
    k = np.exp(-(np.arange(span)**2)/(2*h*h)); k /= k.sum(); x = c.values; out = np.full(len(x), np.nan)
    for i in range(span, len(x)): out[i] = np.dot(k, x[i-span+1:i+1][::-1])
    return pd.Series(out, index=c.index)
def features(d, nwe=False, lele_fixed=False):
    d = d.copy(); c, h, l, o, v = d.close, d.high, d.low, d.open, d.volume
    d["ema21"], d["ema50"], d["rsi"] = ema(c, 21), ema(c, 50), rsi(c)
    d["mhist"] = ema(c, 12) - ema(c, 26) - ema(ema(c, 12) - ema(c, 26), 9)
    d["dip"], d["dim"], d["adx"], d["atr"] = dmi(h, l, c)
    d["volstrong"] = v > v.rolling(20).mean()
    # HTF 60-min: previous completed hour's close vs its EMA50, lagged
    hc = c.resample("60min").last(); he = ema(hc, 50); hc, he = hc.shift(1), he.shift(1)
    d["htfL"] = (hc > he).reindex(d.index, method="ffill").fillna(False); d["htfS"] = (hc < he).reindex(d.index, method="ffill").fillna(False)
    rc, ro, rh1, rl1 = c.shift(1), o.shift(1), h.shift(2), l.shift(2)
    d["brkL"], d["brkS"], d["cdlL"], d["cdlS"] = rc > rh1, rc < rl1, rc > ro, rc < ro
    d["strL"], d["strS"] = (d.adx > 18) & (d.dip > d.dim), (d.adx > 18) & (d.dim > d.dip)
    st = (c - d.ema21).abs()/d.atr; d["stretchL"], d["stretchS"] = (c > d.ema21) & (st > 2.2), (c < d.ema21) & (st > 2.2)
    tsL, tsS = (d.ema21 > d.ema50) & (c > d.ema21), (d.ema21 < d.ema50) & (c < d.ema21)
    twL, twS = (d.ema21 > d.ema50) & ~tsL, (d.ema21 < d.ema50) & ~tsS
    momL, momS = (d.rsi > 55) & (d.mhist > 0), (d.rsi < 45) & (d.mhist < 0)
    dom = d.index.day; nxt = (d.index + pd.Timedelta(days=1)).day
    eom = (nxt == 1) | (dom <= 3)
    # Leledc levels
    bindex = np.zeros(len(d), int); sindex = np.zeros(len(d), int); cv = c.values
    for i in range(4, len(d)):
        bindex[i] = bindex[i-1]+1 if cv[i] > cv[i-4] else 0; sindex[i] = sindex[i-1]+1 if cv[i] < cv[i-4] else 0
    lowN, highN = l.rolling(30).min().values, h.rolling(30).max().values
    leleB = (sindex > 6) & (cv > o.values) & (l.values <= lowN); leleS = (bindex > 6) & (cv < o.values) & (h.values >= highN)
    bull_lv, bear_lv = [], []; nearB = np.zeros(len(d), bool); nearS = np.zeros(len(d), bool); a = d.atr.values; lv = l.values; hv = h.values
    for i in range(len(d)):
        if leleB[i]: bull_lv.append(lv[i]); bull_lv = bull_lv[-12:]
        if leleS[i]: bear_lv.append(hv[i]); bear_lv = bear_lv[-12:]
        chk = (lambda arr: arr[-5:]) if lele_fixed else (lambda arr: arr[:5])
        nearB[i] = any(abs(cv[i]-y) < 0.45*a[i] for y in chk(bull_lv)) if bull_lv else False
        nearS[i] = any(abs(cv[i]-y) < 0.45*a[i] for y in chk(bear_lv)) if bear_lv else False
    nweL = nweS = pd.Series(False, index=d.index)
    if nwe:
        fit = nw_causal(c); mae = (c - fit).abs().rolling(300, min_periods=50).mean()*3.0; up, dn = fit + mae, fit - mae
        nweL, nweS = (l <= dn) & (c > dn), (h >= up) & (c < up)
    d["scoreL"] = np.minimum(2*tsL + 1*twL + 2*momL + d.brkL.astype(int) + d.cdlL.astype(int) + d.htfL.astype(int) + (d.volstrong & d.cdlL).astype(int) + d.strL.astype(int) + nweL.astype(int) + nearB.astype(int) + eom.astype(int), 9)
    d["scoreS"] = np.minimum(2*tsS + 1*twS + 2*momS + d.brkS.astype(int) + d.cdlS.astype(int) + d.htfS.astype(int) + (d.volstrong & d.cdlS).astype(int) + d.strS.astype(int) + nweS.astype(int) + nearS.astype(int), 9)
    thin = (h - l) < 0.12*d.atr; wk = d.index.dayofweek >= 5
    d["gateL"] = (d.adx >= 18) & ~d.stretchL & ~thin & ~wk; d["gateS"] = (d.adx >= 18) & ~d.stretchS & ~thin & ~wk
    d["sigL"] = (d.scoreL >= 6) & (d.scoreL > d.scoreS) & d.gateL; d["sigS"] = (d.scoreS >= 6) & (d.scoreS > d.scoreL) & d.gateS
    # sweep-reclaim promotion (WATCH>=5 + London/Asia low swept and reclaimed) — sessions in UTC: Asia 00-08, London 07-15:30, NY 13:30-20
    hr = d.index.hour + d.index.minute/60; inA, inL, inN = (hr < 8), (hr >= 7) & (hr < 15.5), (hr >= 13.5) & (hr < 20)
    day = d.index.floor("D"); aL = l.where(inA).groupby(day).cummin().reindex(d.index); aH = h.where(inA).groupby(day).cummax()
    lL = l.where(inL).groupby(day).cummin(); lH = h.where(inL).groupby(day).cummax()
    swL = (inL & (l < aL.shift(1)) & (c > aL.shift(1))) | (inN & (l < lL.shift(1)) & (c > lL.shift(1)))
    swS = (inL & (h > aH.shift(1)) & (c < aH.shift(1))) | (inN & (h > lH.shift(1)) & (c < lH.shift(1)))
    d["promL"] = (d.scoreL >= 5) & (d.scoreL > d.scoreS) & swL & d.gateL & ~d.sigL; d["promS"] = (d.scoreS >= 5) & (d.scoreS > d.scoreL) & swS & d.gateS & ~d.sigS
    d["swL8"], d["swH8"] = l.rolling(8).min(), h.rolling(8).max()
    return d
def trade(O, H, L, C, i, s, stop, tgt, cap=500, comm=0.0002):
    e = O[i+1]; r = abs(e - stop) if abs(e-stop) > 0 else np.nan
    for j in range(i+1, min(i+cap, len(C))):
        if s == 1 and L[j] <= stop: return (stop/e - 1) - 2*comm, j-i
        if s == -1 and H[j] >= stop: return (1 - stop/e) - 2*comm, j-i
        if s == 1 and H[j] >= tgt: return (tgt/e - 1) - 2*comm, j-i
        if s == -1 and L[j] <= tgt: return (1 - tgt/e) - 2*comm, j-i
    j = min(i+cap, len(C)-1); return s*(C[j]/e - 1) - 2*comm, j-i
def run(d, label, use_prom=False, which="conf"):
    O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    sigL = (d.promL if which == "prom" else (d.sigL | d.promL if use_prom else d.sigL)).values; sigS = (d.promS if which == "prom" else (d.sigS | d.promS if use_prom else d.sigS)).values
    swl, swh = d.swL8.values, d.swH8.values; n = len(C); rng = np.random.default_rng(11)
    real, ctrl, in_pos_until = [], [], -1
    for i in range(300, n-2):
        if i < in_pos_until or np.isnan(A[i]): continue
        s = 1 if sigL[i] else (-1 if sigS[i] else 0)
        if s == 0: continue
        stop = min(C[i]-1.5*A[i], swl[i]) if s == 1 else max(C[i]+1.5*A[i], swh[i]); risk = abs(C[i]-stop); tgt = C[i] + s*2*risk
        r, k = trade(O, H, L, C, i, s, stop, tgt); real.append(r/(risk/C[i])); in_pos_until = i + k + 1
        for j in rng.choice(np.arange(max(300, i-30*96), i-1), size=3, replace=False):
            rk = risk/C[i]*C[j]; st2 = C[j] - s*rk; tg2 = C[j] + s*2*rk
            r2, _ = trade(O, H, L, C, int(j), s, st2, tg2); ctrl.append(r2/(rk/C[j]))
    real, ctrl = np.array(real), np.array(ctrl)
    print(f"{label:46s} n{len(real):5d}  real {real.mean():+.3f}R win {(real>0).mean():.0%}  control {ctrl.mean():+.3f}R win {(ctrl>0).mean():.0%}  edge {real.mean()-ctrl.mean():+.3f}R  t {real.mean()/real.std()*np.sqrt(len(real)):+.1f}")
    return real, ctrl
if __name__ == "__main__":
    for sym, path in (("BTC 15m 5y", "data_15m/BTCUSD.csv"), ("ETH 15m 5y", "data_15m/ETHUSD.csv")):
        df = pd.read_csv(path); df["ts"] = pd.to_datetime(df.iloc[:, 0], utc=True); df = df.set_index("ts")[["open", "high", "low", "close", "volume"]]
        print(f"\n== {sym}: {len(df)} bars")
        d = features(df); run(d, "as written (NWE off in history, Leledc oldest-5)")
        d2 = features(df, nwe=True, lele_fixed=True); run(d2, "NWE causal ON + Leledc fixed")
        run(d, "sweep-reclaim promotions only", which="prom")
        # half split
        half = d.index[len(d)//2]; run(d[d.index < half], "  as written, H1"); run(d[d.index >= half], "  as written, H2")
