"""
CHART REPORT — point it at any chart and get the full read.

DK: "Can our market strategy now look at any chart, establish the key trend
lines and levels, assess the current price action using our preferred
indicators, and then scan it for developing trade set ups?"

This is that tool. It wires together what survived testing and deliberately
leaves out what did not.

WHAT GOES IN — and why each piece is here

  STRUCTURE (structure.py, doc 41)
      major pivots by ATR-scaled prominence; horizontal levels including
      all-time / annual / two-year extremes with cluster strength; established
      diagonal trend lines scored by later touches.

  STATE
      trend (200-bar average), ATR as a percentage of price, distance from the
      annual high and low, and whether minute-scale absolute volatility is high
      enough for the cascade trade to be possible at all.

  SETUPS, in priority order, each with its own entry, stop and target
      1. RETEST of a broken level or trend line  — doc 42: beats buying the
         break on 6 of 6 tests, strongest on diagonals (+0.502R on ETFs). The
         edge is the STOP, not prediction: entering next to the level buys the
         same target for far less risk.
      2. PATTERN completions — double bottom, inverse H&S, ascending triangle,
         scored by the confluence model and gated on a weak close at the
         structural low (docs 39, 40).
      3. APPROACHING a level — not a trade, a watch item.

WHAT IS DELIBERATELY LEFT OUT
      flags (-0.199R vs control), candlestick triggers other than the weak-low
      gate, Bollinger/squeeze/Ichimoku direction signals, and levels used as a
      general-purpose signal — all measured at no edge or negative. Their
      absence is a finding, not an oversight.

MANDATE: research only. This prints an analysis. It places nothing, connects to
no account, and holds no credentials.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, glob
import numpy as np, pandas as pd
import structure as ST
import patterns_proper as PP
import confluence_scanner as CS
import retest as RT

WEIGHTS = "/home/claude/qlab/runs/confluence/crypto_hourly_weights.json"


def load_chart(path):
    df = pd.read_csv(path)
    dc = "date" if "date" in df.columns else df.columns[0]
    df[dc] = pd.to_datetime(df[dc], errors="coerce")
    df = df.dropna(subset=[dc]).set_index(dc).sort_index()
    return df[~df.index.duplicated()]


def state(df):
    px = df.close.iloc[-1]
    a = ST.atr(df).iloc[-1]
    ma200 = df.close.rolling(200).mean().iloc[-1]
    out = dict(close=float(px), atr=float(a), atr_pct=float(a / px * 100),
               trend="UP" if px > ma200 else "DOWN",
               ma200=float(ma200), bars=len(df))
    for lab, n in (("annual", 365), ("two_year", 730)):
        if len(df) > n:
            w = df.iloc[-n:]
            out[f"{lab}_high"] = float(w.high.max())
            out[f"{lab}_low"] = float(w.low.min())
            out[f"from_{lab}_high"] = float(px / w.high.max() - 1) * 100
    ret5 = df.close.pct_change(5)
    out["vol5_pct"] = float(ret5.std() * 100)
    out["cascade_capable"] = bool(out["vol5_pct"] > 0.5)
    return out


def live_retests(df, lookback=30, tol_atr=0.4):
    """Levels and trend lines broken recently and now being retested.

    This is the primary setup (doc 42). A retest is LIVE if the break happened
    within `lookback` bars and price is currently back at the level."""
    try:
        lows, highs = PP.confirmed_pivots(df)
    except Exception:
        return []
    if len(lows) < 4 or len(highs) < 4:
        return []
    n = len(df)
    a = ST.atr(df).bfill().values
    C, L = df.close.values, df.low.values
    px = C[-1]
    out = []
    for u in RT.find_setups(df, highs, lows):
        if u["break_bar"] < n - lookback or u["failed"]:
            continue
        lvl = u["level"]
        if abs(px / lvl - 1) <= tol_atr * a[-1] / px and px > lvl:
            out.append(dict(kind="retest_horizontal", level=float(lvl),
                            entry=float(px), stop=float(u["stop"]),
                            target=float(u["target"]),
                            rr=float((u["target"] - px) / max(px - u["stop"], 1e-9)),
                            broke_bars_ago=int(n - u["break_bar"])))
    for u in RT.diagonal_setups(df, highs, lows):
        if u["break_bar"] < n - lookback or u["failed"]:
            continue
        lvl = u["level"]
        if abs(px / lvl - 1) <= tol_atr * a[-1] / px and px > lvl:
            out.append(dict(kind="retest_diagonal", level=float(lvl),
                            entry=float(px), stop=float(u["stop"]),
                            target=float(u["target"]),
                            rr=float((u["target"] - px) / max(px - u["stop"], 1e-9)),
                            touches=u["touches"],
                            broke_bars_ago=int(n - u["break_bar"])))
    return out


def live_patterns(df, lookback=40):
    """Pattern completions in the recent window, with confluence score and the
    weak-low gate (docs 39, 40)."""
    W = json.load(open(WEIGHTS)) if os.path.exists(WEIGHTS) else None
    try:
        lows, highs = PP.confirmed_pivots(df)
    except Exception:
        return []
    if len(lows) < 4 or len(highs) < 4:
        return []
    lows_i = [i for i, _ in lows]; highs_i = [i for i, _ in highs]
    a = ST.atr(df).bfill().values
    ma = df.close.rolling(200).mean().values
    v = df.volume.replace(0, np.nan) if "volume" in df.columns else None
    vr = (v / v.rolling(20).mean()).fillna(1.0).values if v is not None \
        else np.ones(len(df))
    grid = CS.level_grid(df, lows_i, highs_i)
    C, L, H = df.close.values, df.low.values, df.high.values
    n = len(df)
    out = []
    for det in (PP.d_double_bottom, PP.d_inv_hs, PP.d_asc_triangle):
        try:
            sigs = det(df, lows, highs)
        except Exception:
            continue
        for g in sigs:
            b = g["bar"]
            if b < n - lookback:
                continue
            rr = (g["target"] - g["entry"]) / max(g["entry"] - g["stop"], 1e-9)
            feat = dict(f_level=float(CS.nearest_fast(grid, b, g["stop"])
                                      <= 0.5 * a[b]) if a[b] > 0 else 0.0,
                        f_trend=float(np.isfinite(ma[b]) and C[b] > ma[b]),
                        f_volume=float(vr[b] > 1.5),
                        f_rr=float(rr >= 1.5))
            sc = None
            if W:
                sc = W["base"] + W["pattern"].get(g["name"], 0.0) + \
                    sum(W["weights"][k] * feat[k] for k in W["weights"])
            # weak-low gate
            j, best = None, np.inf
            for k in range(max(0, b - 200), b + 1):
                d = abs(L[k] - g["stop"])
                if d < best:
                    best, j = d, k
            pos = np.nan
            if j is not None and H[j] > L[j]:
                pos = (C[j] - L[j]) / (H[j] - L[j])
            out.append(dict(kind=g["name"], entry=float(g["entry"]),
                            stop=float(g["stop"]), target=float(g["target"]),
                            rr=float(rr), score=sc, low_pos=float(pos),
                            weak_low=bool(pos < 0.3333),
                            bars_ago=int(n - b),
                            at_level=bool(feat["f_level"])))
    return out


def report(path, name=None):
    df = load_chart(path)
    name = name or os.path.basename(path)[:-4]
    if len(df) < 300:
        print(f"{name}: only {len(df)} bars — too short"); return
    s = state(df)
    L = ST.all_levels(df, len(df) - 1)
    px = s["close"]

    print("=" * 92)
    print(f"  {name}   {df.index[-1]}   close {px:,.6g}")
    print("=" * 92)
    print(f"  trend {s['trend']} (200-bar avg {s['ma200']:,.6g})   "
          f"ATR {s['atr_pct']:.2f}% of price   {s['bars']} bars")
    if "from_annual_high" in s:
        print(f"  annual range {s['annual_low']:,.6g} - {s['annual_high']:,.6g}   "
              f"{s['from_annual_high']:+.1f}% from the annual high")
    print(f"  5-bar volatility {s['vol5_pct']:.2f}%   "
          f"cascade trade {'POSSIBLE' if s['cascade_capable'] else 'not possible here'}")

    print(f"\n  STRUCTURE — {len(L)} levels in range")
    above = sorted([l for l in L if l["price"] > px], key=lambda x: x["price"])[:4]
    below = sorted([l for l in L if l["price"] <= px],
                   key=lambda x: -x["price"])[:4]
    for l in reversed(above):
        t = "diag" if l["diagonal"] else "horiz"
        ex = f"touches={l.get('touches')}" if l["diagonal"] else f"pivots={l.get('pivots')}"
        print(f"    ^ {l['price']:12,.6g}  {abs(l['price']/px-1)*100:5.1f}% above  "
              f"{l['kind']:16s} {t:5s} str {l['strength']:2d}  {ex}")
    print(f"    > {px:12,.6g}  <- price")
    for l in below:
        t = "diag" if l["diagonal"] else "horiz"
        ex = f"touches={l.get('touches')}" if l["diagonal"] else f"pivots={l.get('pivots')}"
        print(f"    v {l['price']:12,.6g}  {abs(l['price']/px-1)*100:5.1f}% below  "
              f"{l['kind']:16s} {t:5s} str {l['strength']:2d}  {ex}")

    rts = live_retests(df)
    print(f"\n  SETUPS — retests (the primary trigger, doc 42)")
    if not rts:
        print("    none live")
    for r in sorted(rts, key=lambda x: -x["rr"])[:5]:
        tag = "DIAGONAL" if r["kind"].endswith("diagonal") else "horizontal"
        extra = f" touches={r.get('touches')}" if "touches" in r else ""
        print(f"    {tag:10s} level {r['level']:,.6g}  broke {r['broke_bars_ago']} "
              f"bars ago{extra}")
        print(f"      entry {r['entry']:,.6g}  stop {r['stop']:,.6g}  "
              f"target {r['target']:,.6g}  R:R {r['rr']:.2f}")

    pts = live_patterns(df)
    print(f"\n  SETUPS — pattern completions")
    if not pts:
        print("    none in the recent window")
    for p in sorted(pts, key=lambda x: -(x["score"] or 0))[:5]:
        gates = []
        if p["weak_low"]:
            gates.append("weak-low PASS")
        else:
            gates.append(f"weak-low FAIL (closed {p['low_pos']*100:.0f}% up its range)")
        if p["at_level"]:
            gates.append("at a level")
        sc = f"{p['score']:+.4f}" if p["score"] is not None else "n/a"
        print(f"    {p['kind']:14s} {p['bars_ago']:3d} bars ago  score {sc}  "
              f"R:R {p['rr']:.2f}  [{', '.join(gates)}]")
        print(f"      entry {p['entry']:,.6g}  stop {p['stop']:,.6g}  "
              f"target {p['target']:,.6g}")
    print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            report(p)
    else:
        for p in ("/home/claude/qlab/data_1h_33/BTCUSDT.csv",
                  "/home/claude/qlab/data_1h_33/SOLUSDT.csv",
                  "/home/claude/qlab/data_wide/SPY.csv",
                  "/home/claude/qlab/data_wide/GLD.csv"):
            if os.path.exists(p):
                report(p)
