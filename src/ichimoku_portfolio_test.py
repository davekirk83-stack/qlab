"""Doc 163 — Ichimoku H1 (strong TK) and H2 (kumo breakout), LONG, classic 9/26/52/26, Kijun exit (doc 162 rules unchanged), as ONE
portfolio across the 27 registered coins + the 32 registered ETFs (DK 29 Oct: "Yes please"). Pre-registered.
Costs: coins 0.10%/side, ETFs 0.05%/side. Dev: coins to 2022, ETFs to 2018; holdout after.
Control: per market, random entries on bars already above the cloud, same Kijun exit, same count (200 draws, pooled).
Portfolio sim: each trade gets 5% of equity at entry, at most 20 open (taken in date order), non-leveraged."""
import json, numpy as np, pandas as pd
exec(open("src/ichimoku_system_test.py").read().split("lines = []")[0])
coins = json.load(open("/home/claude/qlab-git/runs/range_universe.json"))["registered_universe"]
etfs = open("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/etfs.txt").read().split()
def ld(sym, kind):
    if kind == "coin":
        d = pd.read_csv(f"data_daily/{sym}.csv"); d["t"] = pd.to_datetime(d.t, unit="ms"); d = d.set_index("t").sort_index()
    else: d = pd.read_csv(f"data_etfd/{sym}.csv", parse_dates=["t"]).set_index("t").sort_index()
    return d[["open", "high", "low", "close"]].astype(float)
M = [(s, "coin", 0.001, pd.Timestamp("2023-01-01")) for s in coins] + [(s, "etf", 0.0005, pd.Timestamp("2019-01-01")) for s in etfs]
lines = []
for sysname in ("H1", "H2"):
    pooled = {"dev": [], "hold": []}; ctl = {"dev": np.zeros(200), "hold": np.zeros(200)}; cnt = {"dev": 0, "hold": 0}; per = {}
    allrows = []
    for sym, kind, cost, split in M:
        try: d = ld(sym, kind)
        except Exception: continue
        if len(d) < 400: continue
        I = ichi(d, 9, 26, 52, 26); sig, above = signals(d, I, 1)
        for seg, msk in (("dev", d.index < split), ("hold", d.index >= split)):
            ent = np.flatnonzero(sig[sysname] & msk)
            tr = trades(d, I, ent[ent < len(d) - 1], 1, cost)
            if not tr: continue
            pooled[seg] += [(sym, kind) + t for t in tr]; cnt[seg] += len(tr)
            pool = np.flatnonzero(above & msk); pool = pool[(pool > 200) & (pool < len(d) - 2)]
            if len(pool):
                for k in range(200):
                    rng = np.random.default_rng(k); pick = np.sort(rng.choice(pool, min(len(tr) * 3, len(pool)), replace=False))
                    ct = trades(d, I, pick, 1, cost)[:len(tr)]
                    ctl[seg][k] += sum(t[1] for t in ct)
            allrows += [(sym, kind) + t for t in tr]
    for seg in ("dev", "hold"):
        r = np.array([t[3] for t in pooled[seg]]); n = len(r)
        if not n: continue
        cm = ctl[seg] / n
        by_k = {k: np.mean([t[3] for t in pooled[seg] if t[1] == k]) for k in ("coin", "etf")}
        nk = {k: sum(1 for t in pooled[seg] if t[1] == k) for k in ("coin", "etf")}
        pos_mk = len({t[0] for t in pooled[seg] if t[3] > 0})
        lines.append(f"{sysname} {seg}: n{n} win {100*(r>0).mean():.0f}% mean {100*r.mean():+.2f}% median {100*np.median(r):+.2f}% | coins {100*by_k['coin']:+.2f}% (n{nk['coin']}) ETFs {100*by_k['etf']:+.2f}% (n{nk['etf']}) | random above-cloud entries {100*np.median(cm):+.2f}%, beats {100*(cm < r.mean()).mean():.0f}%")
        print(lines[-1], flush=True)
    # portfolio sim over all trades, date order
    T = sorted(allrows, key=lambda t: t[2]); eq = 1.0; open_ = []; curve = []; yr = {}
    for sym, kind, t, r, hold in T:
        open_ = [o for o in open_ if o > t]
        if len(open_) >= 20: continue
        eq *= 1 + 0.05 * r; open_.append(t + pd.Timedelta(days=int(hold * (1 if kind == "coin" else 1.45)))); curve.append((t, eq)); yr.setdefault(t.year, []).append(0.05 * r)
    c = pd.Series([e for _, e in curve], index=[t for t, _ in curve]); dd = (c / c.cummax() - 1).min()
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    lines.append(f"{sysname} portfolio (5%/trade, max 20 open): CAGR {100*(c.iloc[-1]**(1/yrs)-1):+.1f}% maxDD {100*dd:.0f}% | by year " + " ".join(f"{y}:{100*sum(v):+.0f}%" for y, v in sorted(yr.items())))
    print(lines[-1], flush=True)
open("runs/ichimoku_portfolio_test.txt", "w").write("\n".join(lines) + "\n")
