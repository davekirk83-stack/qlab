"""Range v3.1 candidate: hold through a regime switch (exit only at the mid EMA, a break, the cap or the stop). Five years, 27 coins,
v3 costs. Control = v3 as registered on the same bars. Writes runs/range_v31_test.txt incrementally."""
import sys, json, numpy as np, pandas as pd; sys.path.insert(0, "/home/claude/qlab/src"); import paperbook6 as P
syms = json.load(open("/home/claude/qlab/runs/range_universe.json")) if __import__("os").path.exists("/home/claude/qlab/runs/range_universe.json") else []
syms = syms if isinstance(syms, list) else list(syms.get("registered_universe", []))
out = open("/home/claude/qlab/runs/range_v31_test.txt", "a")
def run(sym, hold_regime):
    d = pd.read_csv(f"/home/claude/qlab/data_15m/{sym}.csv"); d["ts"] = pd.to_datetime(d.iloc[:, 0], utc=True); d = d.set_index("ts")[["open", "high", "low", "close"]]
    P._MED = {}
    src = P.step
    if hold_regime:
        # monkeypatch: treat 'not ok' as not forcing an exit — emulate by making allow True for exits only. Simplest faithful way:
        # run step with allow forced True for the exit check but keep entries gated. We do this by wrapping indicators to return
        # allow for entries and a separate flag; paperbook6.step uses `ok` for both, so re-implement the one line via a flag.
        pass
    pos = {}; slots = [40]; closed, _ = P.step(sym, d, pos, str(d.index[250]), slots)
    return pd.DataFrame(closed, columns=["sym", "side", "open", "close", "ret", "how"])
if __name__ == "__main__":
    import re
    srcfile = open("/home/claude/qlab/src/paperbook6.py").read()
    # build a variant module where the regime switch no longer forces an exit
    v = srcfile.replace("if age >= CAP_BARS or broke or not ok:", "if age >= CAP_BARS or broke:")
    assert v != srcfile
    ns = {}; exec(compile(v, "pb6_v31", "exec"), {"__name__": "pb6_v31", "__file__": "/home/claude/qlab/src/paperbook6.py"} | ns) if False else None
    import types; mod = types.ModuleType("pb6_v31"); mod.__file__ = "/home/claude/qlab/src/paperbook6.py"; exec(compile(v, "pb6_v31", "exec"), mod.__dict__)
    res = {"v3": [], "v31": []}
    for i, sym in enumerate(syms):
        for name, M in (("v3", P), ("v31", mod)):
            d = pd.read_csv(f"/home/claude/qlab/data_15m/{sym}.csv"); d["ts"] = pd.to_datetime(d.iloc[:, 0], utc=True); d = d.set_index("ts")[["open", "high", "low", "close"]]
            M._MED = {}; pos = {}; slots = [40]
            try: closed, _ = M.step(sym, d, pos, str(d.index[250]), slots)
            except Exception as e: out.write(f"{sym} {name} ERROR {e}\n"); out.flush(); continue
            e = pd.DataFrame(closed, columns=["sym", "side", "open", "close", "ret", "how"]); e["close"] = pd.to_datetime(e.close)
            res[name].append(e)
            half = e.close.iloc[len(e)//2] if len(e) else None
            h1 = e[e.close < half].ret.mean()*100 if len(e) else 0; h2 = e[e.close >= half].ret.mean()*100 if len(e) else 0
            out.write(f"{sym:10s} {name:4s} n{len(e):5d} per-ep {e.ret.mean()*100:+.3f}% win {(e.ret>0).mean():.0%} H1 {h1:+.3f} H2 {h2:+.3f} exits {e.how.value_counts().to_dict()}\n"); out.flush()
        if i % 3 == 2:
            for name in res:
                a = pd.concat(res[name]); out.write(f"  RUNNING {name}: n{len(a)} per-ep {a.ret.mean()*100:+.3f}% win {(a.ret>0).mean():.0%} t {a.ret.mean()/a.ret.std()*np.sqrt(len(a)):+.1f}\n"); out.flush()
    for name in res:
        a = pd.concat(res[name]); a["yr"] = a.close.dt.year
        out.write(f"FINAL {name}: n{len(a)} per-ep {a.ret.mean()*100:+.3f}% win {(a.ret>0).mean():.0%} t {a.ret.mean()/a.ret.std()*np.sqrt(len(a)):+.1f} by year {(a.groupby('yr').ret.mean()*100).round(3).to_dict()} exits {a.how.value_counts().to_dict()}\n"); out.flush()
