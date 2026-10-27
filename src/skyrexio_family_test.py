"""Doc 145d part 2: the source's own window, and Skyrexio's two sister strategies (TradingView, read 27 Oct 2026).
 R  RECONCILE: our 145c BASE on Skyrexio's exact window (BTC 3h, 2023-01-01 to 2024-11-25), where they report PF 3.36.
 AC MultiLayer Acceleration/Deceleration: same filters/exit/pyramid as the saucer, signal = Accelerator Oscillator
    (AC = AO - SMA5(AO)): above zero two rising bars after a falling bar, below zero three; buy stop above the signal bar,
    trailed to lower highs while AC rises, cancelled when AC turns down. Author: BTC 3h 2023-01-01..2024-11-01 PF 2.39.
 RB Bullish Reversal Bar (Williams 'Wiseman 1'): bar high below jaw, teeth and lips, close in its upper half; buy stop
    above its high, cancelled if its low trades first; stop at its low; exit on the fractal/teeth trend flip; one position.
    Author: ETH 4h, 2023-2024, PF 1.63.
Same dev/sealed holdout split (2025-04-01) and random-entry control (100 draws) as part 1. Trials added: 2 strategies x
2 universes = 4 (cumulative 12 with part 1)."""
import numpy as np, pandas as pd
from saucer_refine_test import load, build, stats, TEN, COST, HOLD

def smma(x, n): return x.ewm(alpha=1/n, adjust=False).mean()

def ac_series(d):
    mp = (d.high + d.low) / 2; ao = mp.rolling(5).mean() - mp.rolling(34).mean()
    return (ao - ao.rolling(5).mean()).values

def ac_sig(ac, i):
    if ac[i] > 0: return ac[i] > ac[i-1] > ac[i-2] and ac[i-2] < ac[i-3]
    return ac[i] > ac[i-1] > ac[i-2] > ac[i-3] and ac[i-3] < ac[i-4]

def run_ac(d, B, ac, rnd=None):
    ao, ema, state, O, H, L, C = B; idx = d.index; n = len(C); pos = []; tr = []; pend = None
    for i in range(40, n):
        if state[i] == -1 and pos:
            tr += [(idx[p[1]], C[i]*(1-COST)/p[0]-1) for p in pos]; pos = []; pend = None
        elig = state[i] == 1 and C[i] > ema[i]
        if rnd is None:
            if pend is not None and state[i] == 1:
                if H[i] > pend and len(pos) < 5: pos.append((max(pend, C[i-1])*(1+COST), i)); pend = None
                elif ac[i] < ac[i-1]: pend = None
                elif H[i] < pend: pend = H[i]
            if elig and ac_sig(ac, i): pend = H[i]
        elif elig and i in rnd and len(pos) < 5: pos.append((C[i]*(1+COST), i))
    tr += [(idx[p[1]], C[-1]/p[0]-1) for p in pos]
    return tr

def rb_lines(d):
    mp = (d.high + d.low) / 2
    return smma(mp, 13).shift(8).values, smma(mp, 8).shift(5).values, smma(mp, 5).shift(3).values

def run_rb(d, B, lines, rnd=None):
    ao, ema, state, O, H, L, C = B; jaw, teeth, lips = lines; idx = d.index; n = len(C); pos = None; tr = []; setup = None
    for i in range(40, n):
        if pos is not None:
            if L[i] <= pos[1]: tr.append((idx[pos[2]], min(pos[1], O[i])*(1-COST)/pos[0]-1)); pos = None
            elif state[i] == -1: tr.append((idx[pos[2]], C[i]*(1-COST)/pos[0]-1)); pos = None
        if pos is None and rnd is None and setup is not None:
            hi, lo = setup
            if L[i] <= lo and not H[i] > hi: setup = None
            elif H[i] > hi:
                pos = (max(hi, O[i])*(1+COST), lo, i); setup = None
                if L[i] <= lo: tr.append((idx[i], lo*(1-COST)/pos[0]-1)); pos = None
        below = np.isfinite(jaw[i]) and H[i] < min(jaw[i], teeth[i], lips[i])
        if pos is None and below:
            if rnd is None:
                if C[i] > (H[i] + L[i]) / 2: setup = (H[i], L[i])
            elif i in rnd: pos = (C[i]*(1+COST), L[i], i)
    if pos is not None: tr.append((idx[pos[2]], C[-1]/pos[0]-1))
    return tr

def evaluate(name, U, data, Bs, runner, eligf, extra):
    seg = lambda trs, hold: [r for t, r in trs if (t >= HOLD) == hold]
    real = {f: runner(data[f], Bs[f], extra[f]) for f in U}; rows = []
    for hold in (False, True):
        s = stats(sum((seg(real[f], hold) for f in U), [])); tots = []
        for k in range(100):
            rng = np.random.default_rng(k); pooled = []
            for f in U:
                el = eligf(data[f], Bs[f], extra[f]); el = el[(data[f].index[el] >= HOLD) == hold]; m = len(seg(real[f], hold))
                pick = set(rng.choice(el, size=min(m, len(el)), replace=False)) if m and len(el) else set()
                pooled += seg(runner(data[f], Bs[f], extra[f], rnd=pick), hold)
            tots.append(stats(pooled)["tot"])
        tots = np.array(tots)
        rows.append(f"{'HOLD' if hold else 'DEV '} n{s['n']:4} win {s['win']:4.0f}% PF {s['pf']:.2f} mean {s['mean']:+.2f}% total {s['tot']:+7.1f}% | random median {np.median(tots):+7.1f}%, beats {100*(tots < s['tot']).mean():3.0f}%")
    return f"{name}\n  " + "\n  ".join(rows)

if __name__ == "__main__":
    out = []
    # R: reconcile on Skyrexio's window
    from saucer_refine_test import run as run_sauc
    d = load("BTCUSD"); d = d[(d.index >= "2022-12-01") & (d.index < "2024-11-26")]; B = build(d)
    t = [r for tt, r in run_sauc(d, B) if tt >= pd.Timestamp("2023-01-01", tz="UTC")]; s = stats(t)
    out.append(f"RECONCILE BTC 3h 2023-01-01..2024-11-25 (Skyrexio: 107 trades, 43% win, PF 3.36, +28.4%): "
               f"ours n{s['n']} win {s['win']:.0f}% PF {s['pf']:.2f} total {s['tot']:+.1f}% | BTC buy&hold {100*(d.close.iloc[-1]/d.close[d.index>='2023-01-01'].iloc[0]-1):+.0f}%")
    print(out[-1], flush=True)
    data3 = {f: load(f) for f in TEN}; B3 = {f: build(data3[f]) for f in TEN}; ACs = {f: ac_series(data3[f]) for f in TEN}
    el_ac = lambda d, B, x: np.array([i for i in range(40, len(B[6])-1) if B[2][i] == 1 and B[6][i] > B[1][i]])
    for uname, U in (("BTC+ETH", TEN[:2]), ("10 coins", TEN)):
        out.append(evaluate(f"AC strategy 3h, {uname}", U, data3, B3, run_ac, el_ac, ACs)); print(out[-1], flush=True)
    # RB on 4h
    def load4(f):
        x = pd.read_csv(f"data_15m/{f}.csv"); x["t"] = pd.to_datetime(x.t, utc=True)
        return x.set_index("t")[["open","high","low","close"]].astype(float).resample("4h").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
    data4 = {f: load4(f) for f in TEN}; B4 = {f: build(data4[f]) for f in TEN}; LN = {f: rb_lines(data4[f]) for f in TEN}
    def el_rb(d, B, ln):
        H = B[4]; j, t_, l = ln
        return np.array([i for i in range(40, len(H)-1) if np.isfinite(j[i]) and H[i] < min(j[i], t_[i], l[i])])
    for uname, U in (("ETH only", ["ETHUSD"]), ("10 coins", TEN)):
        out.append(evaluate(f"Reversal bar 4h, {uname} (total at 10%/trade; author sized 50%)", U, data4, B4, run_rb, el_rb, LN)); print(out[-1], flush=True)
    open("runs/skyrexio_family_test.txt", "w").write("\n".join(out) + "\n")
