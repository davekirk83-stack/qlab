"""Doc 191 — CAPITULATION-DAY RETEST LADDER (indices, daily). DK 7 Nov: Venu's "signs of a bottom"; Thursday 5 Nov NDX -6.4%, VIX +70%.
Trigger day: index falls >= D% on the day AND VIX rises >= V% that day. Then, for 20 trading days, buy rungs at the trigger day's low,
low -3%, low -6% (limit orders; filled if the day's low reaches them). Exit all at average entry x (1+TP) (limit, intraday high),
or after 40 trading days at the close, or stop at trigger low x (1-SL) (daily low). Costs 0.1% round trip. Return per episode on the full
3-rung budget. Dev 1990-2009, hold 2010-2026."""
import json, numpy as np, pandas as pd, itertools
S = "/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/"
OUT = open("runs/capitulation_retest.txt", "w")
def log(s): print(s, flush=True); OUT.write(s + "\n")
def ld(n):
    r = json.load(open(S + n + ".json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=pd.to_datetime(r["timestamp"], unit="s").normalize()).dropna()
V = ld("VIX").close; SPLIT = pd.Timestamp("2010-01-01")
def run(x, D, VV, TP, SL, rung=(0, .03, .06)):
    x = x.copy(); x["r"] = x.close.pct_change() * 100; x["vr"] = V.pct_change().reindex(x.index) * 100
    O, H, L, C = x.open.values, x.high.values, x.low.values, x.close.values; eps = []; i = 1
    while i < len(x) - 2:
        if not (x.r.iloc[i] <= -D and x.vr.iloc[i] >= VV): i += 1; continue
        low0 = L[i]; lv = [low0 * (1 - g) for g in rung]; filled = [False] * 3; cb = 0; u = 0; out = None
        for k in range(i + 1, min(i + 41, len(x))):
            for j in range(3):
                if not filled[j] and k <= i + 20 and L[k] <= lv[j]: filled[j] = True; px = min(lv[j], O[k]); cb += px; u += 1
            if u and L[k] <= low0 * (1 - SL): out = min(low0 * (1 - SL), O[k]); how = "stop"; break
            if u and H[k] >= cb / u * (1 + TP): out = cb / u * (1 + TP); how = "tp"; break
        else:
            out = C[k] if u else None; how = "time"
        if u: eps.append((x.index[i], (u * out - cb - 0.001 * cb) / (low0 * 3), u, how, k - i))
        else: eps.append((x.index[i], 0.0, 0, "nofill", 0))
        i = k + 1
    return pd.DataFrame(eps, columns=["t", "ret", "rungs", "how", "days"])
def summ(E):
    c = []
    for seg, msk in (("dev", E.t < SPLIT), ("hold", E.t >= SPLIT)):
        e = E[msk & (E.rungs > 0)]; c.append(f"{seg} n{len(e):2} mean {100*e.ret.mean():+5.1f}% win {100*(e.ret>0).mean():3.0f}% worst {100*e.ret.min():+5.1f}%" if len(e) else f"{seg} none")
    return " || ".join(c)
for name in ("NDX", "GSPC", "RUT"):
    x = ld(name); x = x[x.index >= "1990-01-02"]
    log(f"\n{name}")
    for D, VV in ((4, 40), (3, 25), (2.5, 20)):
        best = None
        for TP, SL in itertools.product((0.03, 0.05, 0.08), (0.10, 0.15)):
            E = run(x, D, VV, TP, SL); d = E[(E.t < SPLIT) & (E.rungs > 0)]
            sc = d.ret.mean() * np.sqrt(len(d)) if len(d) > 2 else -9
            if best is None or sc > best[0]: best = (sc, TP, SL, E)
        log(f"  trigger -{D}% & VIX +{VV}%: chosen TP{best[1]*100:.0f}% SL{best[2]*100:.0f}% on dev -> {summ(best[3])}")
    E = run(x, 3, 25, 0.05, 0.15); log(f"  fixed TP5 SL15 on -3%/VIX+25%: {summ(E)}; latest triggers: " + ", ".join(f"{t.date()}" for t in E.t.tail(3)))
