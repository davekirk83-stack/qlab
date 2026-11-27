"""DK 27 Nov 22:17: "swap to 'creation' mode. Find promising aspects, things that work, and try them in novel combinations."
Building blocks that held up (docs 272-278):
  B1  flush-day reversal: after a -1.5 sigma morning BTC rose +0.80% to the day close (n=91), 9/10 coins positive (checker, doc 278)
  B2  BTC 22:00-23:00 UTC strength (Quantpedia; +0.06%/trade gross, both halves)
  B3  DK v2 bids: resting maker bids just under the obvious level (maker 0 cost) beat deeper / market entries
  B4  deep-flush / uptrend context (v2), flush-reclaim daily
  B5  Connors RSI(2) pullback (reliable on stocks for decades) - untested on crypto here
Combinations built from reasons (not a sweep), each judged on BTC halves AND the 9 alts pooled:
  S1  SIGMA BAND BID: a resting maker bid each UTC day at day-open x (1 - k sigma) (B1 + B3: buy the abnormal move AT the band, no taker
      fee on entry); exit at the day's close (S1a) or at 23:00 UTC (S1b, before the late strength fades? no - B2 says 22-23 is up, so
      S1c holds to 23:00 and S1d holds to the NEXT 23:00).  Fill only if the low trades THROUGH the bid (conservative).
  S2  S1 only in v2's context (deep flush >= 15% off the 20-day high, or uptrend above 50 & 200-day) (B1+B3+B4)
  S3  RSI(2) < 10 on the daily close, in v2's context, buy the close (taker), exit when the close > 5-day mean, 10-day limit (B5+B4)
  S4  RSI(2) stretch with a maker entry: rest a bid next day at yesterday's close x (1 - 0.5 sigma) when RSI(2) < 10 (B5+B3)
Costs Revolut X: maker 0, taker 0.09% + 0.05% slip. Results in % per trade (unlevered)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import dk_v2_all_charts as A
TK = 0.0014
ALTS = ("ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")

def daily(d):
    D = pd.DataFrame({"o": d.open.resample("1D").first(), "h": d.high.resample("1D").max(), "l": d.low.resample("1D").min(), "c": d.close.resample("1D").last()}).dropna()
    D["ret"] = D.c / D.o - 1; D["sig"] = (D.c.pct_change()).rolling(14).std().shift(1)
    D["ctx"] = ((D.c.shift(1) <= D.h.rolling(20).max().shift(1) * 0.85) | ((D.c.shift(1) > D.c.rolling(50).mean().shift(1)) & (D.c.shift(1) > D.c.rolling(200, min_periods=120).mean().shift(1))))
    dd = D.c.diff(); up = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    D["rsi2"] = 100 - 100 / (1 + up / dn.replace(0, np.nan)); D["ma5"] = D.c.rolling(5).mean()
    return D

def s1(d, k=1.5, hold="close", ctx=False, stop=None):
    D = daily(d); out = {}
    g = d.groupby(d.index.floor("1D"))
    days = list(g.groups.keys())
    for i, day in enumerate(days[:-2]):
        if day not in D.index or not np.isfinite(D.at[day, "sig"]): continue
        if ctx and not D.at[day, "ctx"]: continue
        x = g.get_group(day); bid = D.at[day, "o"] * (1 - k * D.at[day, "sig"])
        hit = np.where(x.low.values < bid)[0]
        if not len(hit): continue
        h0 = hit[0]
        if x.index[h0].hour >= 22: continue                                         # too late to hold
        if hold == "close": seg = x.iloc[h0:]
        elif hold == "23": seg = x.iloc[h0:][x.index[h0:].hour < 23]
        else: seg = pd.concat([x.iloc[h0:], g.get_group(days[i + 1])]); seg = seg[seg.index < days[i + 1] + pd.Timedelta("23h")]
        if not len(seg): continue
        px = seg.close.iloc[-1]
        if stop:
            sl = bid * (1 - stop * D.at[day, "sig"]); s = np.where(seg.low.values[1:] <= sl)[0]
            if len(s): px = sl
        out[x.index[h0]] = px * (1 - TK) / bid - 1
    return pd.Series(out, dtype=float)

def s3(d, maker=False):
    D = daily(d); out = {}; i = 220; n = len(D)
    while i < n - 11:
        r = D.iloc[i]
        if r.rsi2 < 10 and D.ctx.iloc[i + 1 if maker else i] and np.isfinite(r.sig):
            if maker:
                bid = r.c * (1 - 0.5 * r.sig); nx = D.iloc[i + 1]
                if nx.l >= bid: i += 1; continue
                e, j0 = bid, i + 1
            else: e, j0 = r.c * (1 + TK), i
            j = j0 + 1
            while j < min(n - 1, j0 + 10) and D.c.iloc[j] <= D.ma5.iloc[j]: j += 1
            out[D.index[j0]] = D.c.iloc[j] * (1 - TK) / e - 1; i = j
        i += 1
    return pd.Series(out, dtype=float)

def st(t):
    t = t.dropna().sort_index()
    if len(t) < 8: return dict(n=len(t))
    h = len(t) // 2; return dict(n=len(t), win=round((t > 0).mean(), 2), mean=round(100 * t.mean(), 3), h1=round(100 * t[:h].mean(), 3), h2=round(100 * t[h:].mean(), 3), total=round(100 * t.sum(), 1))

if __name__ == "__main__":
    DATA = {s: A.coin(s) for s in ("BTCUSDT",) + ALTS}
    tests = {}
    for k in (1.0, 1.5, 2.0):
        tests[f"S1 sigma-band bid k={k}, exit day close"] = lambda d, k=k: s1(d, k, "close")
    tests["S1 k=1.5, exit 23:00"] = lambda d: s1(d, 1.5, "23")
    tests["S1 k=1.5, hold to NEXT 23:00"] = lambda d: s1(d, 1.5, "next23")
    tests["S1 k=1.5 next23 + stop 1 sigma lower"] = lambda d: s1(d, 1.5, "next23", stop=1.0)
    tests["S2 = S1 k=1.5 day close, v2 context only"] = lambda d: s1(d, 1.5, "close", ctx=True)
    tests["S2 = S1 k=1.5 next23, v2 context only"] = lambda d: s1(d, 1.5, "next23", ctx=True)
    tests["S2 = S1 k=1.0 next23, v2 context only"] = lambda d: s1(d, 1.0, "next23", ctx=True)
    tests["S3 RSI2<10 in v2 context, buy close, exit > 5d mean"] = lambda d: s3(d)
    tests["S4 RSI2<10, maker bid 0.5 sigma under, exit > 5d mean"] = lambda d: s3(d, maker=True)
    rows = []; keep = {}
    for lab, f in tests.items():
        per = {s: f(DATA[s]) for s in DATA}; keep[lab] = per
        alts = pd.concat([per[s] for s in ALTS]); b = st(per["BTCUSDT"]); a = st(alts)
        coins_pos = sum(1 for s in DATA if len(per[s]) >= 8 and per[s].mean() > 0)
        rows.append(dict(test=lab, **{f"btc_{x}": v for x, v in b.items()}, **{f"alts_{x}": v for x, v in a.items()}, coins_pos=f"{coins_pos}/10"))
        print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/creation_combos.csv", index=False)
    pd.to_pickle(keep, "runs/research/creation_combos.pkl")
    pd.set_option("display.width", 300); print(R.to_string(index=False))
