"""Doc 153 — Qullamaggie EXECUTION as a systematic book (rule 188 follow-up to doc 152). Pre-registered 28 Oct 2026 before any result.
DK: "Yes please". Same data, entry, stop and management as doc 151 Q-BO (first-hour-high break, low-of-day stop, skip if risk > 1 ADR,
half off day 3 + breakeven, rest on SMA10), QQQ trend filter. No chart pattern: each day, liquid high-range stocks are RANKED and tried in order.
 BASE  every eligible stock-day (the effect itself, large n)
 K1    rank by 1-month return   K2 rank by 3-month return   (2 trials)
 PORTFOLIO: up to 5 new entries a day, at most 10 open, 0.5% risk per trade, non-compounded; equity in % of capital, by year, max drawdown.
 CONTROL: the same portfolio with a RANDOM daily order (50 draws).

Doc 151 docstring (data and mechanics) follows:
Doc 151 — the legends' setups traded AS INTENDED (rule 188). Pre-registered 28 Oct 2026 before any result. DK: "Yes please".
Data: daily (split/dividend-adjusted) for setup selection; HOURLY bars (Yahoo, regular session, ~Nov 2023/Nov 2024 - Oct 2026) for the
intraday entry, rescaled each day to the daily adjusted basis. 2,719 stocks that were liquid/high-range at some point in the window.
Costs 0.20% per side + 6.5%/yr financing. Results in R (P&L / initial risk) and %.

Q-BO  QULLAMAGGIE BREAKOUT (his "3 timeless setups", stream/blog):
      market: QQQ prior close above its SMA10 and SMA20, SMA10 > SMA20.
      stock: price >= $5, 20d median $vol >= $5m, ADR(20) >= 4%; a top-2% performer over 1, 3 or 6 months (any); orderly
             consolidation: 10-day range <= 2.5 x ADR, close >= SMA20, SMA10 > SMA20.
      entry: day D, after the first hour, buy when price breaks max(first-hour high, prior 10-day high); stop = low of the day so far;
             skip if risk > 1 ADR.
      manage: sell half at the close of the 3rd day after entry and move the stop to breakeven; the rest exits on a close below SMA10
             (variant SMA20). Stop checked on the remaining hourly bars of day D, then daily.
Q-EP  EPISODIC PIVOT (Qullamaggie / Bonde): open >= 10% above prior close; first-hour volume >= 50% of the 50-day average DAILY volume;
      not extended (prior 60-day return <= +20%); same liquidity/ADR; entry = break of the first-hour high; stop = low of day so far;
      same management. No market filter (variant: QQQ filter).
MV    MINERVINI SEPA/VCP: market: SPY above SMA50 > SMA200, SMA50 rising. stock: trend template (doc 148) + volatility contraction:
      range of the last 10 days < 0.75 x range of days 11-25 < 0.75 x range of days 26-50, last range <= 12%; volume dry-up (10-day avg
      < 50-day avg). entry: intraday break of the prior 10-day high (pivot); stop = max(prior 10-day low, entry x 0.925).
      manage: sell half at +20%; move the stop to breakeven once a close is >= +2R; the rest exits on a close below SMA50.
CONTROLS (50 draws, same mechanics, same market filter, same management):
      R1 random eligible stock-days (entry = break of the first-hour high);  R2 (Q-BO only) random top-2% leaders, same entry.
DIAGNOSTICS (rule 188 step 3, reported, not used for the verdict): Q-BO without the market filter; Q-BO without the partial sale."""
import glob, os, json, numpy as np, pandas as pd
COST, FIN = 0.002, 0.065
# ---------------------------------------------------------------- data
H1 = {}
for f in glob.glob("data_stk_1h/*.csv"):
    s = os.path.basename(f)[:-4]
    h = pd.read_csv(f); h["t"] = pd.to_datetime(h.t, utc=True).dt.tz_convert("America/New_York")
    h = h[(h.t.dt.hour >= 9) & (h.t.dt.hour < 16)]
    day = h.t.dt.tz_localize(None).dt.normalize().values
    cut = np.flatnonzero(np.r_[True, day[1:] != day[:-1], True])
    H1[s] = dict(H=h.high.values.astype("f4"), L=h.low.values.astype("f4"), O=h.open.values.astype("f4"), C=h.close.values.astype("f4"),
                 V=h.volume.values.astype("f4"), sl={pd.Timestamp(day[a]): (a, b) for a, b in zip(cut[:-1], cut[1:])})
START = pd.Timestamp("2023-12-01")
def daily(s, path="data_stk2"):
    p = f"{path}/{s}.csv"
    if not os.path.exists(p): p = f"data_stk/{s}.csv"
    if not os.path.exists(p): return None
    d = pd.read_csv(p, parse_dates=["t"]).set_index("t"); return d[~d.index.duplicated()].dropna()
D = {s: daily(s) for s in H1 if s not in ("QQQ", "SPY")}; D = {s: d for s, d in D.items() if d is not None and len(d) > 260}
spy = pd.read_csv("data_eqd/SPY.csv", parse_dates=["t"]).set_index("t").adj; qqq = pd.read_csv("data_eqd/QQQ.csv", parse_dates=["t"]).set_index("t").adj
qok = ((qqq > qqq.rolling(10).mean()) & (qqq > qqq.rolling(20).mean()) & (qqq.rolling(10).mean() > qqq.rolling(20).mean())).shift(1)
s50, s200 = spy.rolling(50).mean(), spy.rolling(200).mean()
sok = ((spy > s50) & (s50 > s200) & (s50 > s50.shift(10))).shift(1)
r21 = pd.DataFrame({s: d.close / d.close.shift(21) - 1 for s, d in D.items()}); r63 = pd.DataFrame({s: d.close / d.close.shift(63) - 1 for s, d in D.items()})
r126 = pd.DataFrame({s: d.close / d.close.shift(126) - 1 for s, d in D.items()}); r252 = pd.DataFrame({s: d.close / d.close.shift(252) - 1 for s, d in D.items()})
liq = pd.DataFrame({s: ((d.close >= 5) & ((d.close * d.volume).rolling(20).median() >= 5e6) & ((d.high / d.low - 1).rolling(20).mean() >= 0.04)) for s, d in D.items()})
def toprank(r): return r.where(liq).rank(axis=1, pct=True)
lead = ((toprank(r21) >= 0.98) | (toprank(r63) >= 0.98) | (toprank(r126) >= 0.98))
rs = r252.rank(axis=1, pct=True)
print(len(D), "stocks with daily + hourly", flush=True)
X = {}
for s, d in D.items():
    o, c, h, l, v = d.open, d.close, d.high, d.low, d.volume
    m10, m20, m50, m150, m200 = (c.rolling(n).mean() for n in (10, 20, 50, 150, 200))
    adr = (h / l - 1).rolling(20).mean(); v50 = v.rolling(50).mean()
    el = liq[s].reindex(d.index).fillna(False)
    h10, l10 = h.rolling(10).max(), l.rolling(10).min()
    qbo = el & lead[s].reindex(d.index).fillna(False) & ((h10 - l10) / h10 <= 2.5 * adr) & (c >= m20) & (m10 > m20)
    tt = (c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(21)) & (m50 > m150) & (c > m50) & \
         (c >= 1.3 * l.rolling(252).min()) & (c >= 0.75 * h.rolling(252).max()) & (rs[s].reindex(d.index) >= 0.70)
    rg = lambda a, b: (h.shift(a).rolling(b - a).max() - l.shift(a).rolling(b - a).min()) / h.shift(a).rolling(b - a).max()
    r1, r2, r3 = rg(0, 10), rg(10, 25), rg(25, 50)
    vcp = tt & (r1 < 0.75 * r2) & (r2 < 0.75 * r3) & (r1 <= 0.12) & (v.rolling(10).mean() < v50) & (c >= 10) & ((c * v).rolling(20).median() >= 5e6)
    prev = lambda x: x.shift(1)   # setups are known at the PRIOR close; trade on day D
    X[s] = dict(idx=d.index, O=o.values, H=h.values, L=l.values, C=c.values, m10=m10.values, m20=m20.values, m50=m50.values,
                adr=prev(adr).values, piv=prev(h10).values, plo=prev(l10).values, v50=prev(v50).values,
                el=prev(el).fillna(False).values.astype(bool), lead=prev(lead[s].reindex(d.index)).fillna(False).values.astype(bool),
                qbo=prev(qbo).fillna(False).values.astype(bool), vcp=prev(vcp).fillna(False).values.astype(bool),
                gap=(o / c.shift(1) - 1).values, r60=(c.shift(1) / c.shift(61) - 1).values,
                qok=qok.reindex(d.index).fillna(False).values.astype(bool), sok=sok.reindex(d.index).fillna(False).values.astype(bool),
                hb=H1[s])
    X[s]["hasH"] = np.array([dd in H1[s]["sl"] for dd in d.index])
del r21, r63, r126, r252, liq, lead, rs, D; import gc; gc.collect()
# ---------------------------------------------------------------- one trade
def intraday(x, i, trig_from_pivot):
    """Entry on day i: after the first hour, break of max(first-hour high, pivot). Returns (entry, stop_so_far, exit_px_or_None) on the daily basis."""
    hb = x["hb"]; ab = hb["sl"].get(x["idx"][i])
    if ab is None or ab[1] - ab[0] < 3: return None
    a, b_ = ab; k = x["C"][i] / float(hb["C"][b_ - 1])                  # rescale hourly bars to the adjusted daily basis
    Hh, Lh, Oh = hb["H"][a:b_] * k, hb["L"][a:b_] * k, hb["O"][a:b_] * k
    trig = Hh[0] if trig_from_pivot is None else max(Hh[0], trig_from_pivot)
    for b in range(1, len(Hh)):
        if Hh[b] > trig:
            e = max(trig, Oh[b]); stop = min(Lh[:b + 1].min(), e * 0.999)
            return e, stop, Lh[b + 1:], float(hb["V"][a])
    return None
def manage_q(x, i, e, stop, ex_same, ma, partial=True):
    C, L, O, M = x["C"], x["L"], x["O"], x[ma]; n = len(C); eC = e * (1 + COST); risk = (e - stop) / e
    if ex_same is not None: return (ex_same * (1 - COST) / eC - 1), risk, 0
    legs = []; w = 1.0; st = stop
    for j in range(i + 1, n):
        if L[j] <= st: legs.append((w, min(st, O[j]))); w = 0; break
        if partial and j == i + 3 and w == 1.0: legs.append((0.5, C[j])); w = 0.5; st = max(st, e)
        if C[j] < M[j]: legs.append((w, C[j])); w = 0; break
    if w > 0: legs.append((w, C[n - 1])); j = n - 1
    days = (x["idx"][j] - x["idx"][i]).days
    r = sum(ww * (px * (1 - COST) / eC - 1) for ww, px in legs) - FIN * days / 365
    return r, risk, days
def manage_m(x, i, e, stop, ex_same):
    C, H, L, O, M = x["C"], x["H"], x["L"], x["O"], x["m50"]; n = len(C); eC = e * (1 + COST); risk = (e - stop) / e
    if ex_same is not None: return (ex_same * (1 - COST) / eC - 1), risk, 0
    legs = []; w = 1.0; st = stop
    for j in range(i + 1, n):
        if L[j] <= st: legs.append((w, min(st, O[j]))); w = 0; break
        if w == 1.0 and H[j] >= e * 1.20: legs.append((0.5, max(e * 1.20, O[j]))); w = 0.5
        if C[j] >= e * (1 + 2 * risk): st = max(st, e)
        if C[j] < M[j]: legs.append((w, C[j])); w = 0; break
    if w > 0: legs.append((w, C[n - 1])); j = n - 1
    days = (x["idx"][j] - x["idx"][i]).days
    return sum(ww * (px * (1 - COST) / eC - 1) for ww, px in legs) - FIN * days / 365, risk, days
# ---------------------------------------------------------------- setups
def run(setup, days_sel, market=True, partial=True, ma="m10", control=None, rng=None, counts=None):
    out = []; cnt = {}
    for s, x in X.items():
        ok = x["idx"] >= START
        if control is None:
            if setup == "QBO": sel = x["qbo"] & (x["qok"] if market else True)
            elif setup == "EP": sel = x["el"] & (x["gap"] >= 0.10) & (x["r60"] <= 0.20) & (x["qok"] if market else True)
            else: sel = x["vcp"] & x["sok"]
            cand = np.flatnonzero(sel & ok)
        else:
            m = counts.get(s, 0)
            if not m: continue
            base = (x["lead"] & x["el"]) if control == "R2" else x["el"]
            filt = (x["qok"] if (market and setup in ("QBO", "EP")) else True) & (x["sok"] if setup == "MV" else True)
            pool = np.flatnonzero(base & filt & ok & x["hasH"])
            if not len(pool): continue
            cand = np.sort(rng.choice(pool, min(m * 3, len(pool)), replace=False))
        busy = -1; k = 0
        for i in cand:
            if i <= busy or i >= len(x["C"]) - 1: continue
            if control is not None and k >= counts[s]: break
            piv = None if control is not None or setup == "EP" else x["piv"][i]
            r = intraday(x, i, piv)
            if r is None: continue
            e, stop, later_lows, v1 = r
            if setup == "EP" and control is None and not (v1 >= 0.5 * x["v50"][i]): continue
            if setup in ("QBO", "EP") and (e - stop) / e > x["adr"][i]: continue
            if setup == "MV": stop = max(x["plo"][i] if control is None else stop, e * 0.925)
            ex = stop if (len(later_lows) and later_lows.min() <= stop) else None
            res = manage_m(x, i, e, stop, ex) if setup == "MV" else manage_q(x, i, e, stop, ex, ma, partial)
            out.append((x["idx"][i], res[0], res[1], res[2])); k += 1
            busy = i + max(1, int(res[2] * 5 / 7))
        cnt[s] = k
    return out, cnt
def summ(t):
    if not t: return "n0", np.nan
    r = np.array([a[1] for a in t]); R = r / np.array([max(a[2], 0.002) for a in t])
    pfR = R[R > 0].sum() / max(-R[R < 0].sum(), 1e-9)
    return (f"n{len(r):5} win {100*(r>0).mean():3.0f}% avg {R.mean():+.2f}R (PF {pfR:.2f}) {100*r.mean():+.2f}%/trade, "
            f">=5R {100*(R>=5).mean():.1f}%, median {np.median(R):+.2f}R, sum {R.sum():+.0f}R"), R.mean()

import multiprocessing as mp
CAND = {}   # day -> list of (stock, i, r21, r63)
for s, x in X.items():
    ok = x["el"] & x["qok"] & x["hasH"] & (x["idx"] >= START)
    for i in np.flatnonzero(ok[:-1]):
        CAND.setdefault(x["idx"][i], []).append((s, i))
r21d = {s: pd.Series(X[s]["C"], index=X[s]["idx"]).pct_change(21).shift(1).values for s in X}
r63d = {s: pd.Series(X[s]["C"], index=X[s]["idx"]).pct_change(63).shift(1).values for s in X}
DAYS = sorted(CAND)
CACHE = {}
def tr(s, i):
    k = (s, i)
    if k not in CACHE:
        x = X[s]; r = intraday(x, i, None); out = None
        if r is not None:
            e, stop, later, v1 = r
            if (e - stop) / e <= x["adr"][i]:
                ex = stop if (len(later) and later.min() <= stop) else None
                rr, risk, days = manage_q(x, i, e, stop, ex, "m10", True)
                out = (rr / max(risk, 0.002), rr, x["idx"][min(i + max(1, int(days * 5 / 7)), len(x["idx"]) - 1)])
        CACHE[k] = out
    return CACHE[k]
def portfolio(order, seed=0):
    rng = np.random.default_rng(seed); book = []; open_until = []
    for day in DAYS:
        c = list(CAND[day])
        if order == "K1": c.sort(key=lambda t: -np.nan_to_num(r21d[t[0]][t[1]], nan=-9))
        elif order == "K2": c.sort(key=lambda t: -np.nan_to_num(r63d[t[0]][t[1]], nan=-9))
        else: rng.shuffle(c)
        open_until = [d for d in open_until if d > day]; new = 0
        for s, i in c:
            if new >= 5 or len(open_until) >= 10: break
            t = tr(s, i)
            if t is None: continue
            book.append((day, t[0], t[1], t[2])); open_until.append(t[2]); new += 1
    return book
def stats(book):
    R = np.array([b[1] for b in book]); eq = pd.Series([0.5 * b[1] for b in book], index=[b[3] for b in book]).sort_index().cumsum()
    dd = (eq - eq.cummax()).min()
    yrs = sorted(set(b[0].year for b in book))
    by = " | ".join(f"{y}: {np.mean([b[1] for b in book if b[0].year == y]):+.2f}R n{sum(1 for b in book if b[0].year == y)} ({0.5*sum(b[1] for b in book if b[0].year == y):+.0f}%)" for y in yrs)
    return R.mean(), f"n{len(R)} win {100*(R>0).mean():.0f}% avg {R.mean():+.2f}R total {0.5*R.sum():+.0f}% of capital (0.5% risk/trade) maxDD {dd:.0f}%\n    by year {by}"
_O = None
def _draw(k): return stats(portfolio("RND", k))[0]
lines = []
# BASE: every eligible stock-day
allR = [tr(s, i) for day in DAYS for s, i in CAND[day]]; allR = [t for t in allR if t is not None]
by = {}
for (day, lst) in ((d, CAND[d]) for d in DAYS):
    for s, i in lst:
        t = CACHE.get((s, i))
        if t is not None: by.setdefault(day.year, []).append(t[0])
lines.append(f"BASE every eligible stock-day in a trending Nasdaq: n{len(allR)} avg {np.mean([t[0] for t in allR]):+.3f}R win {100*np.mean([t[1]>0 for t in allR]):.0f}%  by year " + " | ".join(f"{y}: {np.mean(v):+.3f}R n{len(v)}" for y, v in sorted(by.items())))
print(lines[-1], flush=True)
with mp.get_context("fork").Pool(2) as p: ctrl = np.array(p.map(_draw, range(50)))
lines.append(f"CONTROL random daily order: median {np.median(ctrl):+.3f}R/trade (5-95%: {np.percentile(ctrl,5):+.3f} to {np.percentile(ctrl,95):+.3f})"); print(lines[-1], flush=True)
for k, nm in (("K1", "rank by 1-month return"), ("K2", "rank by 3-month return")):
    m, txt = stats(portfolio(k)); lines.append(f"{k} {nm}: {txt}\n    beats random order {100*(ctrl < m).mean():.0f}%"); print(lines[-1], flush=True)
m, txt = stats(portfolio("RND", 999)); lines.append(f"one random-order portfolio for scale: {txt}"); print(lines[-1], flush=True)
open("runs/qm_execution_book_test.txt", "w").write("\n".join(lines) + "\n")
