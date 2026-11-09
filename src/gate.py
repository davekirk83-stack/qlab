"""
THE GATE — one standard test for every book (doc 196; DK 9 Nov: "you don't have a standardised test").
Fixed in advance, the same for every idea. A book plugs in a `signals(df)` function; the gate does everything else.

HONESTY, ENFORCED BY THE GATE (not by the strategy author):
  1. LOOK-AHEAD CHECK: signals(df[:T]) must equal signals(df) on every bar before T, at 25 random cut points. Any difference -> FAILED.
  2. FILLS: a signal on bar i is filled only by later bars: kind "close" at bar i's close + cost (order sent the moment the bar closes);
     "market" at bar i+1's open; "limit" if a later bar trades strictly THROUGH the price (fill at the price, or the open if it gapped better);
     "stop" if a later bar trades through it (fill at the price, or the open if it gapped worse). Unfilled orders expire after `valid` bars.
  3. IN A TRADE: every bar, the stop is checked BEFORE the target; a gap through the stop fills at the open. Trailing/breakeven changes from
     manage() apply from the NEXT bar. Exit at the close after `max_bars`, or at the session end if `flat_at_session_end`.
  4. ONE POSITION PER MARKET at a time; signals while in a trade are ignored. Costs: `cost` column (price units, round trip) charged per trade.
UNIT (fixed 9 Nov, before any book was re-judged): results are in ATR units — the trade's points divided by the ATR at the signal —
  not in multiples of the initial stop, because a very tight stop (noise-band entries) inflates 'R' without making money.
JUDGEMENT, FIXED: holdout = last 365 days (or the last 40% if the data is under 2 years) — the development period never touches it.
  TESTED  = holdout n >= 50, mean R > 0 with t >= 2.0, both holdout halves > 0, beats the 95th percentile of 200 random-entry runs
            (same sessions, same side mix, same stop/target distances in ATR, same exits), and the look-ahead check passes.
  WEAK    = holdout mean R > 0 and both halves > 0, but fails a count / significance / random-entry condition.
  FAILED  = anything else (or look-ahead found).
Output: one line per book in runs/gate/results.txt and a JSON per book in runs/gate/.
"""
import os, json, numpy as np, pandas as pd

ROOT = os.environ.get("QLAB_ROOT", ".")
OUT = f"{ROOT}/runs/gate"; os.makedirs(OUT, exist_ok=True)
COLS = ["side", "kind", "price", "stop", "target", "max_bars", "valid"]


def atr(df, n=14):
    tr = np.maximum(df.high - df.low, np.maximum((df.high - df.close.shift()).abs(), (df.low - df.close.shift()).abs()))
    return tr.rolling(n).mean()


def lookahead_check(signals, df, n_cuts=25, seed=1):
    base = signals(df)
    rng = np.random.default_rng(seed); cuts = sorted(rng.integers(len(df) // 3, len(df) - 2, n_cuts))
    for T in cuts:
        s = signals(df.iloc[:T])
        a = base[base.index < df.index[T - 1]]; a = a[a.index >= df.index[max(0, T - 3000)]]
        b = s[s.index < df.index[T - 1]]; b = b[b.index >= df.index[max(0, T - 3000)]]
        if len(a) != len(b) or not (a.index == b.index).all() or not np.allclose(a[["side", "price", "stop", "target"]].astype(float).fillna(0).values,
                                                                                 b[["side", "price", "stop", "target"]].astype(float).fillna(0).values, rtol=1e-9, atol=1e-9):
            return False, str(df.index[T])
    return True, ""


def simulate(df, sig, manage=None, flat_at_session_end=False):
    """sig: DataFrame indexed by bar time with COLS. Returns list of trades (dict)."""
    O, H, L, C = df.open.values, df.high.values, df.low.values, df.close.values
    cost = df["cost"].values if "cost" in df else np.zeros(len(df))
    sess = df["session"].values if "session" in df else np.zeros(len(df))
    pos_of = {t: k for k, t in enumerate(df.index)}
    rows = [(pos_of[t], r) for t, r in sig.iterrows() if t in pos_of]
    trades = []; busy_until = -1; n = len(C)
    for i, r in rows:
        if i <= busy_until or i >= n - 1: continue
        s = int(r.side); kind = r.kind
        # --- entry ---
        e = None; j0 = None
        if kind == "close": e, j0 = C[i], i
        elif kind == "market": e, j0 = O[i + 1], i + 1
        else:
            for j in range(i + 1, min(i + 1 + int(r.valid), n)):
                if flat_at_session_end and sess[j] != sess[i]: break
                p = r.price
                if kind == "limit" and ((s == 1 and L[j] < p) or (s == -1 and H[j] > p)): e, j0 = (min(p, O[j]) if s == 1 else max(p, O[j])), j; break
                if kind == "stop" and ((s == 1 and H[j] > p) or (s == -1 and L[j] < p)): e, j0 = (max(p, O[j]) if s == 1 else min(p, O[j])), j; break
        if e is None: continue
        # stop/target: absolute prices, or distances from the fill when the signal row has dist=True
        if bool(r.get("dist", False)): stop, tgt = e - s * r.stop, (e + s * r.target if np.isfinite(r.target) else np.nan)
        else: stop, tgt = r.stop, r.target
        risk = s * (e - stop)
        if not (risk > 0): continue
        c = cost[j0]; px = None; how = None; st = {"stop": stop, "best": e, "e": e, "s": s, "risk0": risk, "i": i, "cost": c}
        # which bars come AFTER the fill: "close" -> from the next bar; "market" -> the whole fill bar (filled at its open);
        # limit/stop -> the fill bar too, but only the stop can trigger on it (we can't know the order inside the bar: assume the worst)
        k = j0 + 1 if kind == "close" else j0
        while k < n:
            fill_bar = (k == j0)
            if (s == 1 and L[k] <= st["stop"]) or (s == -1 and H[k] >= st["stop"]):
                gap = (not fill_bar) and ((s == 1 and O[k] < st["stop"]) or (s == -1 and O[k] > st["stop"]))
                px = O[k] if gap else st["stop"]; how = "stop"; break
            if np.isfinite(tgt) and not (fill_bar and kind in ("limit", "stop")) and ((s == 1 and H[k] >= tgt) or (s == -1 and L[k] <= tgt)):
                gap = (not fill_bar) and ((s == 1 and O[k] > tgt) or (s == -1 and O[k] < tgt))
                px = O[k] if gap else tgt; how = "target"; break
            held = k - j0 + (0 if kind == "close" else 1)
            if held >= int(r.max_bars): px = C[k]; how = "time"; break
            if flat_at_session_end and (k + 1 >= n or sess[k + 1] != sess[k]): px = C[k]; how = "session"; break
            st["best"] = max(st["best"], H[k]) if s == 1 else min(st["best"], L[k])
            if manage: manage(df, k, st)
            k += 1
        if px is None: break
        if "carry" in df: c = c + float(np.nansum(df["carry"].values[j0:k + 1]))
        if "carry_long" in df: c = c + float(np.nansum((df["carry_long"] if s == 1 else df["carry_short"]).values[j0:k + 1]))   # side-dependent funding / basis
        if "roll_every" in df: c = c + cost[j0] * ((k - j0) // int(df["roll_every"].values[j0]))   # one spread per quarterly roll   # overnight funding etc., price units per bar held
        pnl = s * (px - e) - c
        a_i = df["atr"].values[i] if "atr" in df and np.isfinite(df["atr"].values[i]) and df["atr"].values[i] > 0 else risk
        trades.append({"t": df.index[j0], "side": s, "e": e, "x": px, "R": pnl / a_i, "R_risk": pnl / risk, "pts": pnl, "how": how, "bars": k - j0,
                       "stop_atr": risk / df["atr"].values[i] if "atr" in df and df["atr"].values[i] > 0 else np.nan,
                       "tgt_atr": (abs(tgt - e) / df["atr"].values[i]) if "atr" in df and np.isfinite(tgt) and df["atr"].values[i] > 0 else np.nan,
                       "i": i})
        busy_until = k
    return trades


def random_benchmark(df, trades, max_bars, manage, flat, n_runs=200, seed=7):
    if "atr" not in df or not trades: return None
    t = pd.DataFrame(trades); elig = df["eligible"].values if "eligible" in df else np.ones(len(df), bool)
    cand = np.where(elig & np.isfinite(df["atr"].values) & (df["atr"].values > 0))[0]; cand = cand[cand < len(df) - 2]
    if len(cand) < len(t): return None
    rng = np.random.default_rng(seed); means = []
    sa = t.stop_atr.dropna().values; ta = t.tgt_atr.values; sides = t.side.values
    for _ in range(n_runs):
        idx = np.sort(rng.choice(cand, size=len(t), replace=False))
        k = rng.integers(0, len(t), len(t))
        a = df["atr"].values[idx]
        sig = pd.DataFrame({"side": sides[k], "kind": "close", "price": np.nan, "stop": sa[k % len(sa)] * a, "target": ta[k] * a,
                            "max_bars": max_bars, "valid": 1, "dist": True}, index=df.index[idx])
        rt = simulate(df, sig, manage, flat)
        if rt: means.append(np.mean([x["R"] for x in rt]))
    return float(np.percentile(means, 95)) if means else None


def judge(name, df, signals, manage=None, flat_at_session_end=False, max_bars_for_random=None, holdout_days=365, note=""):
    ok, where = lookahead_check(signals, df)
    sig = signals(df); trades = simulate(df, sig, manage, flat_at_session_end)
    span = df.index[-1] - df.index[0]
    cut = df.index[-1] - pd.Timedelta(days=holdout_days) if span >= pd.Timedelta(days=730) else df.index[0] + 0.6 * span
    t = pd.DataFrame(trades)
    res = {"book": name, "note": note, "data": f"{df.index[0].date()}..{df.index[-1].date()}", "holdout_from": str(pd.Timestamp(cut).date()),
           "lookahead_ok": ok, "lookahead_at": where}
    if len(t) == 0:
        res.update(label="FAILED", reason="no trades"); return res
    if (t.t >= cut).sum() == 0:
        res.update(label="FAILED", reason="no holdout trades", hold_n=0, dev_n=int(len(t)), dev_R=round(float(t.R.mean()), 3)); return res
    dev, hold = t[t.t < cut], t[t.t >= cut]
    yrs = max((df.index[-1] - pd.Timestamp(cut)).days / 365.25, 0.05)
    hm = hold.R.mean() if len(hold) else np.nan; hs = hold.R.std(ddof=1) if len(hold) > 1 else np.nan
    tstat = hm / hs * np.sqrt(len(hold)) if len(hold) > 1 and hs > 0 else 0.0
    h1, h2 = (hold.iloc[: len(hold) // 2].R.mean(), hold.iloc[len(hold) // 2:].R.mean()) if len(hold) >= 4 else (np.nan, np.nan)
    eq = hold.R.cumsum(); mdd = float((eq - eq.cummax()).min()) if len(hold) else np.nan
    mb = max_bars_for_random or int(np.nanmedian(sig.max_bars)) if len(sig) else 10
    p95 = random_benchmark(df[df.index >= cut], hold.to_dict("records"), mb, manage, flat_at_session_end) if len(hold) >= 10 else None
    res.update(dev_n=int(len(dev)), dev_R=round(float(dev.R.mean()), 3) if len(dev) else None, hold_n=int(len(hold)), hold_per_year=round(len(hold) / yrs),
               hold_R=round(float(hm), 3) if len(hold) else None, t=round(float(tstat), 2), h1=round(float(h1), 3), h2=round(float(h2), 3),
               win=round(float((hold.R > 0).mean()), 2) if len(hold) else None, maxdd_R=round(mdd, 1), random_p95=None if p95 is None else round(p95, 3))
    beats = p95 is not None and hm > p95
    if not ok: res.update(label="FAILED", reason=f"look-ahead found (cut {where})")
    elif len(hold) >= 50 and hm > 0 and tstat >= 2.0 and h1 > 0 and h2 > 0 and beats: res.update(label="TESTED", reason="all conditions met")
    elif len(hold) and hm > 0 and h1 > 0 and h2 > 0:
        why = [w for w, c in (("n<50", len(hold) < 50), ("t<2", tstat < 2.0), ("not above random 95th pct", not beats)) if c]
        res.update(label="WEAK", reason=", ".join(why))
    else: res.update(label="FAILED", reason="holdout mean R <= 0 or a holdout half <= 0")
    json.dump(res, open(f"{OUT}/{name.replace(' ', '_').replace('/', '-')}.json", "w"), indent=1, default=str)
    pd.DataFrame(trades).to_csv(f"{OUT}/{name.replace(' ', '_').replace('/', '-')}_trades.csv", index=False)
    return res


def line(r):
    if "hold_n" not in r or r.get("hold_R") is None: return f"{r['label']:7s} {r['book']:34s} holdout n{r.get('hold_n',0)} dev n{r.get('dev_n',0)} {r.get('dev_R')} | {r.get('reason','')}"
    return (f"{r['label']:7s} {r['book']:34s} holdout {r['holdout_from']}+: n{r['hold_n']:4d} ({r['hold_per_year']}/yr) {r['hold_R']:+.3f}R t {r['t']:+.2f} "
            f"halves {r['h1']:+.3f}/{r['h2']:+.3f} win {r['win']:.0%} maxDD {r['maxdd_R']}R random95 {r['random_p95']} | dev n{r['dev_n']} {r['dev_R']} "
            f"| look-ahead {'ok' if r['lookahead_ok'] else 'FOUND'} | {r['reason']}")


def judge_pool(name, items, holdout_days=365, note="", n_random=100):
    """items: list of (market, df, signals_fn, kwargs). Same rules as judge(), applied to the pooled trades of one book across markets."""
    allt, ok_all, where_all, rand = [], True, "", []
    per = []
    for mkt, df, fn, kw in items:
        ok, where = lookahead_check(fn, df, n_cuts=8)
        if not ok: ok_all, where_all = False, f"{mkt} {where}"
        tr = simulate(df, fn(df), kw.get("manage"), kw.get("flat_at_session_end", False))
        span = df.index[-1] - df.index[0]
        cut = df.index[-1] - pd.Timedelta(days=holdout_days) if span >= pd.Timedelta(days=730) else df.index[0] + 0.6 * span
        for x in tr: x["mkt"] = mkt; x["hold"] = x["t"] >= cut
        allt += tr; per.append((mkt, df, cut, kw, [x for x in tr if x["hold"]]))
    t = pd.DataFrame(allt)
    res = {"book": name, "note": note, "lookahead_ok": ok_all, "lookahead_at": where_all, "markets": len(items)}
    if not len(t) or not t.hold.any(): res.update(label="FAILED", reason="no holdout trades", hold_n=0, dev_n=len(t)); return res
    t = t.sort_values("t"); hold, dev = t[t.hold], t[~t.hold]
    hm = hold.R.mean(); hs = hold.R.std(ddof=1); tstat = hm / hs * np.sqrt(len(hold)) if len(hold) > 1 and hs > 0 else 0.0
    h1, h2 = hold.iloc[: len(hold) // 2].R.mean(), hold.iloc[len(hold) // 2:].R.mean()
    # pooled random benchmark
    rng = np.random.default_rng(11); means = []
    for r in range(n_random):
        rr = []
        for mkt, df, cut, kw, ht in per:
            if not ht: continue
            mb = int(np.nanmedian([x["bars"] for x in ht])) + 1
            p = random_benchmark(df[df.index >= cut], ht, max(mb, 1), kw.get("manage"), kw.get("flat_at_session_end", False), n_runs=1, seed=int(rng.integers(1e9)))
            if p is not None: rr.append((p, len(ht)))
        if rr: means.append(sum(p * n for p, n in rr) / sum(n for _, n in rr))
    p95 = float(np.percentile(means, 95)) if means else None
    eq = hold.R.cumsum(); mdd = float((eq - eq.cummax()).min())
    yrs = max(holdout_days / 365.25, 0.05)
    res.update(holdout_from="per market", dev_n=int(len(dev)), dev_R=round(float(dev.R.mean()), 3) if len(dev) else None, hold_n=int(len(hold)),
               hold_per_year=round(len(hold) / yrs), hold_R=round(float(hm), 3), t=round(float(tstat), 2), h1=round(float(h1), 3), h2=round(float(h2), 3),
               win=round(float((hold.R > 0).mean()), 2), maxdd_R=round(mdd, 1), random_p95=None if p95 is None else round(p95, 3),
               by_market={m: round(float(g.R.mean()), 3) for m, g in hold.groupby("mkt")})
    beats = p95 is not None and hm > p95
    if not ok_all: res.update(label="FAILED", reason=f"look-ahead found ({where_all})")
    elif len(hold) >= 50 and hm > 0 and tstat >= 2.0 and h1 > 0 and h2 > 0 and beats: res.update(label="TESTED", reason="all conditions met")
    elif hm > 0 and h1 > 0 and h2 > 0:
        res.update(label="WEAK", reason=", ".join(w for w, c in (("n<50", len(hold) < 50), ("t<2", tstat < 2.0), ("not above random 95th pct", not beats)) if c))
    else: res.update(label="FAILED", reason="holdout mean R <= 0 or a holdout half <= 0")
    json.dump(res, open(f"{OUT}/{name.replace(' ', '_').replace('/', '-')}.json", "w"), indent=1, default=str)
    t.to_csv(f"{OUT}/{name.replace(' ', '_').replace('/', '-')}_trades.csv", index=False)
    return res


# ======================= GATE v2 (9 Nov 2026 late, DK: "check online for other recognised testing systems") =======================
# Adds the recognised checks the v1 gate lacked (sources: Pardo / walk-forward analysis; Bailey & Lopez de Prado, Deflated Sharpe /
# multiple testing; White 2000 Reality Check / Masters permutation tests -> our random-entry benchmark; cost stress):
#   WF   walk-forward consistency: the whole history cut into 6 equal time windows (daily books: calendar years); >= 60% must be positive.
#   MT   multiple-testing: every book name ever judged is logged in runs/gate/registry.json; the full-sample t must beat the Sidak-adjusted
#        threshold for that many trials (two-sided 5%): N=20 -> 3.0, N=60 -> 3.3. One lucky year can no longer pass.
#   COST the full-sample mean must stay > 0 with costs x 1.5.
#   Kept from v1: look-ahead detector, gate-side fills, one position, holdout (last year) mean > 0, beats random-entry 95th percentile.
#   TESTED = all of the above. WEAK = full-sample mean > 0, holdout mean > 0 and WF >= 50%, but fails another check. FAILED = otherwise.
from statistics import NormalDist

def _registry(name):
    f = f"{OUT}/registry.json"
    reg = json.load(open(f)) if os.path.exists(f) else []
    if name not in reg: reg.append(name); json.dump(reg, open(f, "w"), indent=0)
    return len(reg)

def v2(name, trades, cut, p95, lookahead_ok, daily=False, cost_mult_trades=None):
    t = pd.DataFrame(trades).sort_values("t")
    N = _registry(name); tstar = NormalDist().inv_cdf(1 - (1 - (1 - 0.05) ** (1 / N)) / 2)
    full_m = t.R.mean(); full_t = full_m / t.R.std(ddof=1) * np.sqrt(len(t)) if len(t) > 2 else 0.0
    hold = t[t.t >= cut]; hm = hold.R.mean() if len(hold) else np.nan
    if daily: wins = t.groupby(t.t.dt.year).R.sum()
    else:
        edges = pd.date_range(t.t.min(), t.t.max(), periods=7); wins = t.groupby(pd.cut(t.t, edges, include_lowest=True)).R.sum()
    wf = float((wins > 0).mean()) if len(wins) else 0.0
    cost_ok = None
    if cost_mult_trades is not None and len(cost_mult_trades): cost_ok = bool(pd.DataFrame(cost_mult_trades).R.mean() > 0)
    beats = p95 is not None and hm > p95
    checks = {"look-ahead": lookahead_ok, f"full-sample t >= {tstar:.2f} (N={N})": full_t >= tstar, "holdout mean > 0": bool(hm > 0),
              "walk-forward >= 60% windows positive": wf >= 0.6, "beats random 95th pct": beats, "costs x1.5 still positive": bool(cost_ok)}
    if all(checks.values()): label = "TESTED"
    elif lookahead_ok and full_m > 0 and hm > 0 and wf >= 0.5: label = "WEAK"
    else: label = "FAILED"
    return {"label_v2": label, "n_all": int(len(t)), "mean_all": round(float(full_m), 3), "t_all": round(float(full_t), 2), "t_needed": round(tstar, 2),
            "wf_positive": round(wf, 2), "wf_windows": int(len(wins)), "holdout_mean": None if np.isnan(hm) else round(float(hm), 3),
            "failed_checks": [k for k, v in checks.items() if not v]}

def judge2(name, items, daily=False, holdout_days=365, n_random=60):
    """items: list of (market, df, signals_fn, kwargs). Works for one market or many. Returns v2 verdict dict."""
    T, T15, ok_all, p_list = [], [], True, []
    for mkt, df, fn, kw in items:
        ok, _ = lookahead_check(fn, df, n_cuts=8); ok_all &= ok
        sig = fn(df); tr = simulate(df, sig, kw.get("manage"), kw.get("flat_at_session_end", False))
        d15 = df.copy(); d15["cost"] = d15["cost"] * 1.5
        tr15 = simulate(d15, sig, kw.get("manage"), kw.get("flat_at_session_end", False))
        span = df.index[-1] - df.index[0]
        cut = df.index[-1] - pd.Timedelta(days=holdout_days) if span >= pd.Timedelta(days=730) else df.index[0] + 0.6 * span
        for x in tr: x["mkt"] = mkt; x["cut"] = cut
        T += tr; T15 += tr15
        ht = [x for x in tr if x["t"] >= cut]
        if len(ht) >= 5:
            mb = int(np.nanmedian([x["bars"] for x in ht])) + 1
            p = random_benchmark(df[df.index >= cut], ht, max(mb, 1), kw.get("manage"), kw.get("flat_at_session_end", False), n_runs=n_random)
            if p is not None: p_list.append((p, len(ht)))
    if not T: return {"book": name, "label_v2": "FAILED", "failed_checks": ["no trades"]}
    p95 = sum(p * n for p, n in p_list) / sum(n for _, n in p_list) if p_list else None
    tt = pd.DataFrame(T); hold_mask = tt.t >= tt.cut
    t2 = [dict(x, t=x["t"] if not hold_mask.iloc[k] else x["t"]) for k, x in enumerate(T)]
    cut_global = tt.cut.min()
    res = v2(name, [{"t": x["t"], "R": x["R"]} for x in T], cut_global if len(items) == 1 else tt.cut.min(), p95, ok_all, daily, [{"R": x["R"]} for x in T15])
    # holdout per market (each market's own last year)
    res["holdout_mean"] = round(float(tt[hold_mask].R.mean()), 3) if hold_mask.any() else None
    res["holdout_n"] = int(hold_mask.sum()); res["random_p95"] = None if p95 is None else round(p95, 3); res["book"] = name
    if res["holdout_mean"] is None or res["holdout_mean"] <= 0:
        if "holdout mean > 0" not in res["failed_checks"]: res["failed_checks"].append("holdout mean > 0")
        if res["label_v2"] != "FAILED": res["label_v2"] = "FAILED"
    else:
        res["failed_checks"] = [c for c in res["failed_checks"] if c != "holdout mean > 0"]
        if res["label_v2"] == "FAILED" and ok_all and res["mean_all"] > 0 and res["wf_positive"] >= 0.5: res["label_v2"] = "WEAK"
        if not res["failed_checks"]: res["label_v2"] = "TESTED"
    if res["random_p95"] is not None and res["holdout_mean"] is not None and res["holdout_mean"] <= res["random_p95"] and "beats random 95th pct" not in res["failed_checks"]:
        res["failed_checks"].append("beats random 95th pct"); res["label_v2"] = "WEAK" if res["label_v2"] == "TESTED" else res["label_v2"]
    json.dump(res, open(f"{OUT}/v2_{name.replace(' ', '_').replace('/', '-')}.json", "w"), indent=1, default=str)
    return res

def line2(r):
    return (f"{r['label_v2']:7s} {r['book']:44s} all n{r.get('n_all',0):5d} {r.get('mean_all',0):+.3f} ATR t {r.get('t_all',0):+.2f} (need {r.get('t_needed')}) | "
            f"walk-forward {r.get('wf_positive',0):.0%} of {r.get('wf_windows',0)} | last year n{r.get('holdout_n',0)} {r.get('holdout_mean')} | random95 {r.get('random_p95')} | "
            f"fails: {', '.join(r.get('failed_checks', [])) or '-'}")
