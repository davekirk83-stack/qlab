"""Doc 196 — every existing book through THE GATE (src/gate.py), same rules for all. Writes runs/gate/results.txt."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G

NY = "America/New_York"
def sigframe(idx, side, kind, price, stop, target, max_bars, valid=1, dist=False):
    return pd.DataFrame({"side": side, "kind": kind, "price": price, "stop": stop, "target": target, "max_bars": max_bars, "valid": valid, "dist": dist}, index=idx)

def load5(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    return d[~d.index.duplicated()].sort_index()

def session15(d, tz, o, c, cost):
    lt = d.index.tz_convert(tz); m = lt.hour * 60 + lt.minute; d = d[(m >= o) & (m < c)]
    q = d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    q["session"] = pd.Series(q.index.tz_convert(tz).date, index=q.index).astype(str); q["cost"] = cost; q["atr"] = G.atr(q).shift(1); q["eligible"] = True
    q["m"] = q.index.tz_convert(tz).hour * 60 + q.index.tz_convert(tz).minute - o
    return q

# ---------------- SPIKE CONT (doc 191) ----------------
def spike_signals(q):
    H, L, O, C = q.high.values, q.low.values, q.open.values, q.close.values; rng = H - L; day = q.session.values
    dm = pd.Series(rng, index=q.index).groupby(day).mean(); ref = q.session.map(dm.shift(1).rolling(5).mean()).values
    idx, side, stop, tgt = [], [], [], []
    for j in range(2, len(C)):
        i = j - 1
        if day[j] != day[i] or not (ref[i] > 0) or rng[i] < 3 * ref[i]: continue
        s = 1 if C[i] > O[i] else -1 if C[i] < O[i] else 0
        if s == 0: continue
        ext = (H[j] - H[i]) / rng[i] if s == 1 else (L[i] - L[j]) / rng[i]
        if not (ext > 0.25 and s * (C[j] - C[i]) > 0): continue
        st = L[j] if s == 1 else H[j]
        if s * (C[j] - st) <= 0: continue
        idx.append(q.index[j]); side.append(s); stop.append(st); tgt.append(C[j] + s * rng[i])
    return sigframe(pd.DatetimeIndex(idx), side, "close", np.nan, stop, tgt, 8)

# ---------------- ORB ----------------
def orb_signals(q):
    H, L, C = q.high.values, q.low.values, q.close.values; m = q.m.values; day = q.session.values
    idx, side, stop, tgt = [], [], [], []; d0 = None
    for i in range(len(C)):
        if day[i] != d0: d0 = day[i]; hi = lo = None; done = False
        if m[i] < 30: hi = H[i] if hi is None else max(hi, H[i]); lo = L[i] if lo is None else min(lo, L[i]); continue
        if done or hi is None or m[i] >= 180: continue
        s = 1 if C[i] > hi else -1 if C[i] < lo else 0
        if s == 0: continue
        st = lo if s == 1 else hi; risk = s * (C[i] - st)
        if risk <= 0: continue
        idx.append(q.index[i]); side.append(s); stop.append(st); tgt.append(C[i] + s * 2 * risk); done = True
    return sigframe(pd.DatetimeIndex(idx), side, "close", np.nan, stop, tgt, 10 ** 6)

# ---------------- IGNITION v1.1 (paperbook7) ----------------
import paperbook7 as P7
def ign_prep():
    b = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); b.index = pd.to_datetime(b.index, utc=True)
    d = P7.features(b); d["cost"] = d["spread"].fillna(d["spread"].median()); return d
def ign_eligible(d):
    lt = d.index.tz_convert(NY); m = lt.hour * 60 + lt.minute
    return (m >= P7.US_OPEN) & (m < P7.US_CLOSE) & ~np.isin(lt.hour, P7.V11_SKIP_HOURS)
def ign_signals(d):
    d = P7.features(d) if "sig" not in d else d
    el = ign_eligible(d); s = d.sig.values; a = d.atr.values; ok = el & (s != 0) & np.isfinite(a)
    ix = np.where(ok)[0]
    stopd = np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]); tgtd = P7.TGT_ATR * a[ix]
    return sigframe(d.index[ix], s[ix].astype(int), "market", np.nan, stopd, tgtd, P7.CAP, dist=True)
def ign_manage(df, k, st):
    s, e = st["s"], st["e"]; a = df["atr"].values[st["i"]]
    if not st.get("be") and s * (st["best"] - e) >= P7.BE: st["be"] = True; st["stop"] = e + s * st["cost"]
    if st.get("be"):
        t = st["best"] - s * P7.TRAIL_ATR * a
        if (s == 1 and t > st["stop"]) or (s == -1 and t < st["stop"]): st["stop"] = t

# ---------------- BOOK 15: BTC 1h trend-aligned sweep + FVG (paperbook15) ----------------
def b15_signals(q, R=3.0, ema=50, slope=6):
    O, H, L, C = q.open.values, q.high.values, q.low.values, q.close.values; n = len(q)
    tr = np.maximum(H - L, np.maximum(abs(H - np.roll(C, 1)), abs(L - np.roll(C, 1)))); atr = pd.Series(tr).rolling(14).mean().shift(1).values
    ll = pd.Series(L).rolling(16).min().shift(1).values; hh = pd.Series(H).rolling(16).max().shift(1).values
    h4 = q.close.resample("4h").last().dropna(); e = h4.ewm(span=ema, adjust=False).mean()
    up = ((h4 > e) & (e > e.shift(slope))).shift(1); dn = ((h4 < e) & (e < e.shift(slope))).shift(1)
    bU = up.reindex(q.index, method="ffill").fillna(False).values.astype(bool); bD = dn.reindex(q.index, method="ffill").fillna(False).values.astype(bool)
    idx, side, price, stop, tgt = [], [], [], [], []
    for i in range(20, n):
        s = 1 if L[i] <= ll[i] - 0.1 * atr[i] else -1 if H[i] >= hh[i] + 0.1 * atr[i] else 0
        if s == 0 or not (bU[i] if s == 1 else bD[i]): continue
        ext = L[i] if s == 1 else H[i]
        for k in range(i + 2, min(i + 6, n)):
            ext = min(ext, L[k]) if s == 1 else max(ext, H[k])
            if not ((L[k] > H[k - 2]) if s == 1 else (H[k] < L[k - 2])): continue
            en = L[k] if s == 1 else H[k]; st = ext - s * 0.1 * atr[i]; risk = abs(en - st)
            if risk > 0: idx.append(q.index[k]); side.append(s); price.append(en); stop.append(st); tgt.append(en + s * R * risk)
            break
    f = sigframe(pd.DatetimeIndex(idx), side, "limit", price, stop, tgt, 48, valid=12)
    return f[~f.index.duplicated()]

# ---------------- BOOK 16: OBV bullish double divergence (paperbook16) ----------------
def b16_signals(h, K=3):
    obv = (np.sign(h.close.diff()).fillna(0) * h.vol).cumsum().values; L, C = h.low.values, h.close.values; N = len(h)
    pl = [i for i in range(K, N - K) if L[i] == L[i - K:i + K + 1].min()]
    idx, stop = [], []
    for k in range(2, len(pl)):
        a, b, c = pl[k - 2], pl[k - 1], pl[k]; e = c + K
        if c - b <= 72 and b - a <= 72 and L[c] < L[b] < L[a] and obv[c] > obv[b] > obv[a]: idx.append(h.index[e]); stop.append(C[e] * 0.92)
    f = sigframe(pd.DatetimeIndex(idx), 1, "close", np.nan, stop, np.nan, 48)
    return f[~f.index.duplicated()]

# ---------------- KELTNER RANGE v1 (paperbook.py, daily) ----------------
def kel_signals(d, gate_on):
    C, H, L = d.close.values, d.high.values, d.low.values
    a = G.atr(d).values; ema = pd.Series(C).ewm(span=20, adjust=False).mean().values; lower = ema - 2.0 * a
    ch = np.abs(pd.Series(C).diff(100)).values; vol = pd.Series(np.abs(np.diff(C, prepend=C[0]))).rolling(100).sum().values; eff = ch / vol
    g = gate_on.reindex(d.index).fillna(False).values
    ok = np.zeros(len(C), bool); ok[1:] = (eff[1:] < 0.30) & (C[1:] <= lower[1:]) & (C[:-1] > lower[:-1]) & g[1:] & np.isfinite(a[1:])
    ix = np.where(ok)[0]
    return sigframe(d.index[ix], 1, "close", np.nan, C[ix] - 3.0 * a[ix], C[ix] + 0.5 * a[ix], 16)

def crypto15(sym):
    d = pd.read_csv(f"/home/claude/qlab/data_15m/{sym}.csv"); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601")
    return d[["open", "high", "low", "close", "volume"]].astype(float).rename(columns={"volume": "vol"})
def to_tf(d, tf):
    return d.resample(tf).agg({"open": "first", "high": "max", "low": "min", "close": "last", "vol": "sum"}).dropna()

if __name__ == "__main__":
    ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
    R = []
    def go(name, df, fn, **kw):
        if ONLY and ONLY not in name: return
        r = G.judge(name, df, fn, **kw); R.append(r); print(G.line(r), flush=True)
    # IG indices — spike, ORB
    for name, f, tz, o, c, cost in (("US Tech 100", "data_nq_cache/nq_5m.csv", NY, 570, 960, 1.0), ("US 500", "data_ig_cache/USA500IDXUSD_5m.csv", NY, 570, 960, 0.4),
                                    ("Wall Street", "data_ig_cache/USA30IDXUSD_5m.csv", NY, 570, 960, 2.4)):
        q = session15(load5(f), tz, o, c, cost)
        go(f"SPIKE {name}", q, spike_signals, flat_at_session_end=True)
    q = session15(load5("data_ig_cache/XAUUSD_5m.csv"), "Europe/London", 480, 990, 0.3); go("ORB Gold London", q, orb_signals, flat_at_session_end=True, max_bars_for_random=40)
    # Ignition v1.1
    d = ign_prep(); d["eligible"] = ign_eligible(d)
    go("IGNITION v1.1 US Tech 100", d, ign_signals, manage=ign_manage)
    # crypto: books 15 and 16 on 1h, costs ~0.1% of price round trip (Revolut X maker in / taker out)
    for sym in ("BTCUSD", "ETHUSD", "SOLUSD"):
        h = to_tf(crypto15(sym), "1h"); h["cost"] = h.close * 0.001; h["atr"] = G.atr(h).shift(1); h["eligible"] = True
        go(f"BOOK15 sweep {sym}", h, b15_signals)
        go(f"BOOK16 OBV div {sym}", h, b16_signals)
    # Keltner v1 daily on 10 coins with the equal-weight 200-day gate
    import json; U = json.load(open("runs/range_universe.json"))["registered_universe"]
    D = {s: to_tf(crypto15(s), "1D") for s in U if os.path.exists(f"/home/claude/qlab/data_15m/{s}.csv")}
    Cx = pd.DataFrame({s: d.close for s, d in D.items()}); idxv = (Cx / Cx.bfill().iloc[0]).mean(axis=1); gate_on = (idxv > idxv.rolling(200).mean()).shift(1)
    for s, d in D.items():
        d["cost"] = d.close * 0.002; d["atr"] = G.atr(d).shift(1); d["eligible"] = True
        go(f"KELTNER v1 {s}", d, lambda x, g=gate_on: kel_signals(x, g))
    open(f"{G.OUT}/results.txt", "w").write("THE GATE — doc 196\n" + "\n".join(G.line(r) for r in R) + "\n")
