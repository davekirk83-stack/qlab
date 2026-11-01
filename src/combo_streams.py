"""Doc 169 helper: trade streams for the daily engines of the combined IG book, saved to runs/combo/.
  mv.csv   Minervini VCP (book 11 MV rules, doc 151 engine; IG share costs 0.20%/side + 6.5%/yr financing), with the doc 165 cloud flag
  etf.csv  Daily trend-line retest, practitioner arm P, 60 clean ETFs (doc 168 engine, causal pivots), IG-style financing added"""
import sys, os, numpy as np, pandas as pd
os.chdir("/home/claude/qlab"); sys.path.insert(0, "/home/claude/qlab-git/src")
which = sys.argv[1]
if which == "mv":
    from cloud_gate import cloud_above
    src = open("/home/claude/qlab-git/src/legends_faithful_test.py").read().split("import multiprocessing as mp")[0]
    a = 'out.append((x["idx"][i], res[0], res[1], res[2]))'; assert src.count(a) == 1
    exec(src.replace(a, 'out.append((x["idx"][i], res[0], res[1], res[2], s))'))
    t, _ = run("MV", None); rows = []
    for d0, r, risk, days, s in t:
        x = X[s]; cl = cloud_above(pd.DataFrame({"high": x["H"], "low": x["L"], "close": x["C"]}, index=pd.DatetimeIndex(x["idx"])))
        rows.append((s, d0, d0 + pd.Timedelta(days=max(int(days), 0)), r / max(risk, 0.002), risk, bool(cl.loc[d0])))
    pd.DataFrame(rows, columns=["sym", "t_open", "t_close", "R", "risk", "cloud"]).to_csv("runs/combo/mv.csv", index=False)
else:
    S = open("/home/claude/qlab-git/src/retest_faithful_test.py").read()
    exec(S.split("OUT = open")[0]); exec("def causal_highs" + S.split("def causal_highs", 1)[1].split("res = {}")[0].replace("OUT.write", "pass;#"))
    rows = []
    for s, d, tf, cost in universe("etf"):
        U, a = setups(d); H, L, C = d.high.values, d.low.values, d.close.values; n = len(C)
        for u in U:
            if "P" not in u: continue
            c = u["conf"]; e, st, tg = u["P"]; risk = e - st
            if risk <= 0 or (tg - e) / risk < 1.5: continue
            px = None
            for j in range(c + 1, min(c + 121, n)):
                if L[j] <= st: px = st; break
                if H[j] >= tg: px = tg; break
            if px is None: j = min(c + 120, n - 1); px = C[j]
            days = (d.index[j] - d.index[c]).days
            R = (px - e) / risk - 2 * 0.0005 * e / risk - 0.065 * days / 365 * e / risk     # IG spread + overnight funding
            rows.append((s, d.index[c], d.index[j], R, risk / e))
    pd.DataFrame(rows, columns=["sym", "t_open", "t_close", "R", "risk"]).to_csv("runs/combo/etf.csv", index=False)
print("done", which)
