"""Dealer gamma (GEX) recorder - doc 260 (DK 22 Nov: AuclairsDad "does a lot with options"; Grok: his map is GEX call wall / put wall /
gamma flip, fade above the flip, follow below it). QuantData is paid, so we compute our own from Cboe's free delayed option chains
(open interest + gamma per contract), once a day, and keep the history so the regime filter can be tested on our books later.
Convention (SpotGamma/SqueezeMetrics style): dealers long calls / short puts -> call GEX +, put GEX -.
GEX per strike = gamma * OI * 100 * S^2 * 0.01 ($ per 1% move). Flip = price where total GEX crosses zero (re-priced across a grid).
Also pulls SqueezeMetrics' DIX/GEX history CSV once (free, 2011-) for the backtest."""
import os, sys, json, math, datetime as dt, urllib.request
import numpy as np, pandas as pd
OUT = "runs/gex"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
def parse_sym(s):   # e.g. SPXW261127P06000000 -> expiry, type, strike
    i = len(s) - 15; root, ymd, cp, k = s[:i], s[i:i+6], s[i+6], int(s[i+7:]) / 1000
    return root, dt.datetime.strptime(ymd, "%y%m%d").date(), cp, k
def bs_gamma(S, K, T, iv):
    if T <= 0 or iv <= 0: return 0.0
    d1 = (math.log(S / K) + 0.5 * iv * iv * T) / (iv * math.sqrt(T)); return math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) / (S * iv * math.sqrt(T))
def levels(sym):
    j = json.loads(get(f"https://cdn.cboe.com/api/global/delayed_quotes/options/{sym}.json"))["data"]
    S = float(j.get("current_price") or j.get("close")); today = dt.date.today(); rows = []
    for o in j["options"]:
        try: root, exp, cp, k = parse_sym(o["option"])
        except Exception: continue
        T = max((exp - today).days, 0.5) / 365; oi = float(o.get("open_interest") or 0); iv = float(o.get("iv") or 0)
        if oi <= 0 or (exp - today).days > 90: continue
        rows.append((exp, cp, k, oi, iv, float(o.get("gamma") or 0), T))
    d = pd.DataFrame(rows, columns=["exp", "cp", "k", "oi", "iv", "gamma", "T"]); sgn = np.where(d.cp == "C", 1, -1)
    d["gex"] = sgn * d.gamma * d.oi * 100 * S * S * 0.01
    by = d.groupby("k").gex.sum(); calls = d[d.cp == "C"].groupby("k").gex.sum(); puts = d[d.cp == "P"].groupby("k").gex.sum()
    grid = np.linspace(S * 0.85, S * 1.15, 121); tot = []
    for x in grid:
        g = sum(s * bs_gamma(x, k, T, iv) * oi * 100 * x * x * 0.01 for s, k, T, iv, oi in zip(sgn, d.k, d.T, d.iv, d.oi))
        tot.append(g)
    tot = np.array(tot); cross = np.where(np.diff(np.sign(tot)) != 0)[0]
    flip = float(grid[cross[np.argmin(abs(grid[cross] - S))]]) if len(cross) else None
    return dict(date=str(today), sym=sym, spot=round(S, 2), net_gex_bn=round(d.gex.sum() / 1e9, 3), regime="positive" if d.gex.sum() > 0 else "negative",
                gamma_flip=round(flip, 1) if flip else None, call_wall=float(calls.idxmax()) if len(calls) else None,
                put_wall=float(puts.idxmin()) if len(puts) else None, top_abs_strike=float(by.abs().idxmax()))
if __name__ == "__main__":
    out = []
    for sym in ("_SPX", "_NDX", "SPY", "QQQ"):
        try: r = levels(sym); out.append(r); print(r)
        except Exception as e: print(sym, "failed:", e)
    if out:
        f = f"{OUT}/gex_daily.csv"; df = pd.DataFrame(out); df.to_csv(f, mode="a", header=not os.path.exists(f), index=False)
    if not os.path.exists(f"{OUT}/squeezemetrics_dix.csv"):
        try: open(f"{OUT}/squeezemetrics_dix.csv", "wb").write(get("https://squeezemetrics.com/monitor/static/DIX.csv")); print("SqueezeMetrics DIX/GEX history saved")
        except Exception as e: print("SqueezeMetrics history failed:", e)
