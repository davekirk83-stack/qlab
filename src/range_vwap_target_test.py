"""Range v3: mid-EMA target vs anchored-VWAP target (doc 144). Same entries, ladder, stop, cap, regime exits.
Variants: target = weekly VWAP (Monday 00:00 UTC anchor) / daily VWAP (00:00 UTC), each used only when it lies on the
profitable side of the current position cost, otherwise the mid EMA (so the variant never targets a loss).
Five years of 15-minute bars, 27 registered coins, v3 costs. Writes runs/range_vwap_target_test.txt incrementally."""
import sys, json, types, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import paperbook6 as P
U = json.load(open("/home/claude/qlab/runs/range_universe.json")); syms = U if isinstance(U, list) else list(U.get("registered_universe", []))
src = open("/home/claude/qlab/src/paperbook6.py").read()
a1 = 'tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]'; a2 = 'tgt = ema[i] if lvl == "mid" else lo_b[i]-lvl*a[i]'
assert src.count(a1) == 1 and src.count(a2) == 1
cst = 'cost_ = sum(x["px"]*x["sz"] for x in p["inv"])/max(sum(x["sz"] for x in p["inv"]),1e-12) if p["inv"] else ema[i]; '
v = src.replace(a1, cst + 'tgt = (VW[i] if (np.isfinite(VW[i]) and VW[i] > cost_) else ema[i]) if lvl == "mid" else hi_b[i]+lvl*a[i]') \
       .replace(a2, cst + 'tgt = (VW[i] if (np.isfinite(VW[i]) and VW[i] < cost_) else ema[i]) if lvl == "mid" else lo_b[i]-lvl*a[i]')
M = types.ModuleType("pb6_vw"); M.__file__ = P.__file__; exec(compile(v, "pb6_vw", "exec"), M.__dict__)
def vwap(d, freq):
    tp = (d.high + d.low + d.close) / 3; g = d.index.floor("D") if freq == "D" else (d.index - pd.to_timedelta(d.index.dayofweek, unit="D")).floor("D")
    return ((tp * d.volume).groupby(g).cumsum() / d.volume.groupby(g).cumsum().replace(0, np.nan)).values
out = open("/home/claude/qlab/runs/range_vwap_target_test.txt", "w"); res = {"ema": [], "wk": [], "day": []}
for sym in syms:
    d = pd.read_csv(f"/home/claude/qlab/data_15m/{sym}.csv"); d["ts"] = pd.to_datetime(d.iloc[:, 0], utc=True); d = d.set_index("ts")[["open", "high", "low", "close", "volume"]].astype(float)
    for name in res:
        mod = P if name == "ema" else M
        if name != "ema": mod.VW = vwap(d, "W" if name == "wk" else "D")
        mod._MED = {}; pos = {}; slots = [40]
        try: closed, _ = mod.step(sym, d[["open", "high", "low", "close"]], pos, str(d.index[250]), slots)
        except Exception as e: out.write(f"{sym} {name} ERROR {e}\n"); out.flush(); continue
        e = pd.DataFrame(closed, columns=["sym", "side", "open", "close", "ret", "how"]); e["close"] = pd.to_datetime(e.close); res[name].append(e)
        out.write(f"{sym:10s} {name:4s} n{len(e):5d} per-ep {e.ret.mean()*100:+.3f}% win {(e.ret>0).mean():.0%}\n"); out.flush()
for name in res:
    a = pd.concat(res[name]); a["yr"] = a.close.dt.year
    out.write(f"FINAL {name}: n{len(a)} per-ep {a.ret.mean()*100:+.4f}% sum {a.ret.sum():.2f} win {(a.ret>0).mean():.1%} t {a.ret.mean()/a.ret.std()*np.sqrt(len(a)):+.1f} by year {(a.groupby('yr').ret.mean()*100).round(3).to_dict()} exits {a.how.value_counts().to_dict()}\n"); out.flush()
# paired per coin
b = {k: pd.concat(v).groupby("sym").ret.sum() for k, v in res.items()}
for k in ("wk", "day"): out.write(f"{k} beats ema on {(b[k] > b['ema']).sum()}/{len(b['ema'])} coins (sum of episode returns)\n")
out.close()
