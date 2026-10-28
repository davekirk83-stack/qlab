"""Doc 153b: point-in-time control check for docs 151/152. The doc 151/152 random controls drew random days only from stocks that produced
a setup signal at SOME point in the window (counts per stock) — that picks stocks with hindsight. Here the control draws from ALL eligible
stocks on each day, as a live book would face. Same mechanics as doc 151."""
exec(open("src/legends_faithful_test.py").read().split("import multiprocessing as mp")[0])
rng = np.random.default_rng(7)
def sample(setup, n=20000):
    pool = []
    for s, x in X.items():
        ok = x["el"] & x["hasH"] & (x["idx"] >= START) & (x["sok"] if setup == "MV" else (x["qok"] if setup == "QBO" else True))
        if setup == "MV": ok = ok & (x["C"] >= 10)
        pool += [(s, i) for i in np.flatnonzero(ok[:-1])]
    pick = [pool[k] for k in rng.choice(len(pool), min(n, len(pool)), replace=False)]
    R = []; yr = {}
    for s, i in pick:
        x = X[s]; r = intraday(x, i, None)
        if r is None: continue
        e, stop, later, v1 = r
        if setup == "MV": stop = max(x["plo"][i], e * 0.925)
        elif (e - stop) / e > x["adr"][i]: continue
        ex = stop if (len(later) and later.min() <= stop) else None
        rr, risk, d = manage_m(x, i, e, stop, ex) if setup == "MV" else manage_q(x, i, e, stop, ex, "m10", True)
        R.append(rr / max(risk, 0.002)); yr.setdefault(x["idx"][i].year, []).append(R[-1])
    return f"{setup} point-in-time random control: n{len(R)} avg {np.mean(R):+.3f}R  by year " + " | ".join(f"{y}: {np.mean(v):+.2f}R" for y, v in sorted(yr.items()))
out = [sample("MV"), sample("EP"), sample("QBO")]
print("\n".join(out)); open("runs/control_check_pit.txt", "w").write("\n".join(out) + "\n")
