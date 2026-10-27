"""Doc 145d: three pre-registered refinements to the AO saucer trend system (doc 145c), tested 27 Oct 2026.
Fixed BEFORE any result was seen:
  BASE   the 145c system unchanged (3h bars, close>EMA100, Alligator/fractal trend, saucer buy stop, pyramid 5, exit on trend flip)
  STOP   + each entry has a protective stop at the signal bar's low (Williams' own rule); stop checked from the entry bar on
         (conservative: a same-bar touch counts); fill at min(stop, bar open) less costs
  DAILY  + entries only while the last COMPLETED daily close is above the daily Alligator jaw (SMMA13 of median, shifted 8)
  BOTH   STOP + DAILY
Universes: the 2 registered coins (BTC, ETH) and 10 large coins (BTC ETH SOL XRP DOGE ADA LINK AVAX LTC DOT), pooled.
Development = data to 2025-03-31; SEALED HOLDOUT = 2025-04-01 onward, scored once. 0.15% per side.
Control per arm: identical filters and exits (incl. stop, at the low of the bar before entry) with entries at random eligible
bars, same entry count per coin, 100 draws. Trials: 4 arms x 2 universes = 8 (deflation, rule 179)."""
import pandas as pd, numpy as np
COST = 0.0015; HOLD = pd.Timestamp("2025-04-01", tz="UTC")
TEN = ["BTCUSD","ETHUSD","SOLUSD","XRPUSD","DOGEUSD","ADAUSD","LINKUSD","AVAXUSD","LTCUSD","DOTUSD"]

def load(f):
    d = pd.read_csv(f"data_15m/{f}.csv"); d["t"] = pd.to_datetime(d.t, utc=True)
    d = d.set_index("t")[["open","high","low","close"]].astype(float)
    agg = {"open":"first","high":"max","low":"min","close":"last"}
    h3 = d.resample("3h").agg(agg).dropna(); dy = d.resample("1D").agg(agg).dropna()
    mp = (dy.high + dy.low) / 2; jaw = mp.ewm(alpha=1/13, adjust=False).mean().shift(8)
    ok = (dy.close > jaw).shift(1)                        # yesterday's completed day, known at today's open
    h3["dailyok"] = ok.reindex(h3.index.floor("1D")).fillna(False).values.astype(bool)
    return h3

def build(d):
    mp = (d.high + d.low) / 2; ao = (mp.rolling(5).mean() - mp.rolling(34).mean()).values
    teeth = mp.ewm(alpha=1/8, adjust=False).mean().shift(5).values; ema = d.close.ewm(span=100, adjust=False).mean().values
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; n = len(C)
    upf = np.full(n, np.nan); dnf = np.full(n, np.nan); lu = ld = np.nan
    for i in range(4, n):
        k = i - 2
        if H[k] == max(H[k-2:k+3]): lu = H[k]
        if L[k] == min(L[k-2:k+3]): ld = L[k]
        upf[i] = lu; dnf[i] = ld
    state = np.zeros(n, int); s = 0
    for i in range(1, n):
        if np.isfinite(upf[i-1]) and C[i] > upf[i-1] and upf[i-1] > teeth[i]: s = 1
        elif np.isfinite(dnf[i-1]) and C[i] < dnf[i-1] and dnf[i-1] < teeth[i]: s = -1
        state[i] = s
    return ao, ema, state, O, H, L, C

def run(d, B, stop=False, daily=False, rnd=None):
    ao, ema, state, O, H, L, C = B; dok = d.dailyok.values; idx = d.index; n = len(C)
    pos = []; tr = []; pend = None; plow = None
    def close(p, px, i): tr.append((idx[p[2]], px * (1 - COST) / p[0] - 1))
    for i in range(40, n):
        if pos and stop:
            keep = []
            for p in pos:
                if L[i] <= p[1]: close(p, min(p[1], O[i]) if p[2] < i else p[1], i)
                else: keep.append(p)
            pos = keep
        if state[i] == -1 and pos:
            for p in pos: close(p, C[i], i)
            pos = []; pend = None
        elig = state[i] == 1 and C[i] > ema[i] and (dok[i] or not daily)
        if rnd is None:
            if pend is not None and state[i] == 1:
                if H[i] > pend and len(pos) < 5:
                    pos.append((max(pend, C[i-1]) * (1 + COST), plow if stop else -np.inf, i)); pend = None
                    if stop and L[i] <= pos[-1][1]: p = pos.pop(); close(p, p[1], i)
                elif ao[i] < ao[i-1]: pend = None
                elif H[i] < pend: pend = H[i]
            if not elig: continue
            if ao[i] > 0 and ao[i-1] > 0 and ao[i-2] > 0 and ao[i-2] > ao[i-1] and ao[i] > ao[i-1]: pend = H[i]; plow = L[i]
        else:
            if elig and i in rnd and len(pos) < 5: pos.append((C[i] * (1 + COST), L[i-1] if stop else -np.inf, i))
    for p in pos: close(p, C[-1], n - 1)
    return tr

def eligible(d, B, daily):
    ao, ema, state, O, H, L, C = B; dok = d.dailyok.values
    return np.array([i for i in range(40, len(C) - 1) if state[i] == 1 and C[i] > ema[i] and (dok[i] or not daily)])

def stats(r):
    r = np.asarray(r)
    if len(r) == 0: return dict(n=0, win=np.nan, pf=np.nan, mean=np.nan, tot=0.0)
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=(r > 0).mean() * 100, pf=w / l if l > 0 else np.inf, mean=r.mean() * 100, tot=r.sum() * 10)

if __name__ == "__main__":
    data = {f: load(f) for f in TEN}; Bs = {f: build(data[f]) for f in TEN}
    arms = {"BASE": (False, False), "STOP": (True, False), "DAILY": (False, True), "BOTH": (True, True)}
    out = []
    for uname, U in (("BTC+ETH", TEN[:2]), ("10 coins", TEN)):
        for arm, (st, dy) in arms.items():
            real = {f: run(data[f], Bs[f], st, dy) for f in U}
            seg = lambda trs, hold: [r for t, r in trs if (t >= HOLD) == hold]
            rows = {}
            for hold in (False, True):
                allr = sum((seg(real[f], hold) for f in U), [])
                s = stats(allr); tots = []
                for k in range(100):
                    rng = np.random.default_rng(k); pooled = []
                    for f in U:
                        el = eligible(data[f], Bs[f], dy); el = el[(data[f].index[el] >= HOLD) == hold]
                        m = len(seg(real[f], hold))
                        pick = set(rng.choice(el, size=min(m, len(el)), replace=False)) if m and len(el) else set()
                        pooled += seg(run(data[f], Bs[f], st, dy, rnd=pick), hold)
                    tots.append(stats(pooled)["tot"])
                tots = np.array(tots)
                rows[hold] = f"n{s['n']:4} win {s['win']:4.0f}% PF {s['pf']:.2f} mean {s['mean']:+.2f}% total {s['tot']:+7.1f}% | random median {np.median(tots):+7.1f}%, beats {100*(tots < s['tot']).mean():3.0f}%"
            out.append(f"{uname:8} {arm:5} DEV  {rows[False]}\n{'':8} {'':5} HOLD {rows[True]}")
            print(out[-1], flush=True)
    txt = "\n".join(out) + "\n\ntotal = sum of trade returns x 10 (% of capital at 10% per entry, no compounding). Trials: 8.\n"
    open("runs/saucer_refine_test.txt", "w").write(txt)
