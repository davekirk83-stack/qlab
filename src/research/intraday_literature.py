"""Doc 283: published day-trading methods with real evidence on index ETFs, built as their papers specify (15-min Alpaca bars 2021-26,
SPY / QQQ / IWM; confirmation on IG NQ Oct 2025 - Nov 2026). Real trades, one per day, per trade results.
  IM   Gao, Han, Li & Zhou (JFE 2018) "Market intraday momentum": the return from the previous close to 10:00 ET predicts the return of
       the LAST half hour (15:30-16:00). Trade: at 15:30 go long if the first-half-hour return > 0, short if < 0; exit at the close.
       Variants: only when |first-half-hour return| is large (top half of its trailing 60 days); also use the 15:00-15:30 return
       (their "second-to-last half hour") as an extra predictor (same sign).
  ORB  Zarattini & Aziz (2023) "Can day trading really be profitable?" (5-min ORB on QQQ): direction of the first candle; enter at the
       next bar's open; stop at the first candle's other end; exit at the close (they also test a 10R target). Here on the first
       15-min candle (our bars); doji candles skipped. Variant: their 'stocks in play' idea -> only when the first candle's volume is
       > 1.5x its 20-day average for that slot.
Costs per side: ETFs 0.0075% (= IG index spread + slippage); IG NQ 1 pt per round trip + 0.5 pt slippage each side (2 pts)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import intraday_search as I

def days(d):
    for day, x in d.groupby(d.index.normalize()):
        if len(x) >= 24: yield day, x

def im(d, pts=False, strong=False, two=False):
    out = []; prev_close = None; hist = []
    for day, x in days(d):
        t = x.index.hour * 60 + x.index.minute
        if prev_close is None: prev_close = x.close.iloc[-1]; continue
        b10 = x[t == 585]; b1530 = x[t == 930]; b15 = x[t == 900]
        if not len(b10) or not len(b1530): prev_close = x.close.iloc[-1]; continue
        r1 = b10.close.iloc[0] / prev_close - 1                                 # prev close -> 10:00 (close of the 09:45 bar)
        hist.append(abs(r1)); s = np.sign(r1)
        ok = s != 0
        if strong: ok = ok and len(hist) > 60 and abs(r1) >= np.median(hist[-61:-1])
        if two and len(b15): ok = ok and np.sign(b15.close.iloc[0] / b15.open.iloc[0] - 1) == s
        if ok:
            e = b1530.open.iloc[0]; xcl = x.close.iloc[-1]
            out.append((day, s, s * (xcl - e) - 2.0 if pts else s * (xcl / e - 1) - 0.00015))
        prev_close = x.close.iloc[-1]
    return pd.DataFrame(out, columns=["t", "side", "r"])

def orb(d, pts=False, relvol=False, target_r=None):
    out = []; vols = []
    for day, x in days(d):
        f = x.iloc[0]; s = np.sign(f.close - f.open); vols.append(f.vol if np.isfinite(f.vol) else np.nan)
        if s == 0: continue
        if relvol and (len(vols) < 21 or not np.isfinite(f.vol) or f.vol < 1.5 * np.nanmean(vols[-21:-1])): continue
        e = x.open.iloc[1]; st = f.low if s == 1 else f.high; risk = abs(e - st)
        if risk <= 0: continue
        tgt = e + s * target_r * risk if target_r else None; px = x.close.iloc[-1]
        for k in range(1, len(x)):
            lo, hi, op = x.low.iloc[k], x.high.iloc[k], x.open.iloc[k]
            if (s == 1 and lo <= st) or (s == -1 and hi >= st): px = st if ((s == 1 and op > st) or (s == -1 and op < st)) else op; break
            if tgt is not None and ((s == 1 and hi >= tgt) or (s == -1 and lo <= tgt)): px = tgt; break
        r = s * (px - e) - 2.0 if pts else s * (px / e - 1) - 0.00015
        out.append((day, s, r, r / (risk if pts else risk / e)))
    return pd.DataFrame(out, columns=["t", "side", "r", "R"])

def summ(T, lab, mk, pts):
    if len(T) < 10: return dict(test=lab, market=mk, n=len(T))
    T = T.sort_values("t"); r = T.r if pts else 100 * T.r; h = len(r) // 2; y = r.groupby(pd.to_datetime(T.t).dt.year.values).sum()
    d = dict(test=lab, market=mk, n=len(r), win=round((r > 0).mean(), 3), mean=round(r.mean(), 4), h1=round(r[:h].mean(), 4), h2=round(r[h:].mean(), 4),
             t=round(r.mean() / (r.std() / np.sqrt(len(r))), 2), worst=round(r.min(), 3), years=" ".join(f"{k}:{v:+.1f}" for k, v in y.items()))
    if "R" in T: d["mean_R"] = round(T.R.mean(), 3)
    return d

if __name__ == "__main__":
    D = {s: I.rth(f"data_alpaca/{s}_15m.csv.gz") for s in I.IDXE}; NQ = I.rth("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/nq15.csv")
    rows = []
    for lab, fn in (("IM: first half hour -> last half hour", lambda d, p: im(d, p)), ("IM strong first half hour", lambda d, p: im(d, p, strong=True)),
                    ("IM + 15:00-15:30 same sign", lambda d, p: im(d, p, two=True)),
                    ("ORB first 15m candle, stop other end, EOD", lambda d, p: orb(d, p)), ("ORB + 10R target", lambda d, p: orb(d, p, target_r=10)),
                    ("ORB 'in play' (first-bar volume > 1.5x)", lambda d, p: orb(d, p, relvol=True))):
        for s, d in D.items(): rows.append(summ(fn(d, False), lab, s, False))
        rows.append(summ(fn(NQ, True), lab, "IG NQ (pts)", True))
        print(lab, "done", flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/intraday_literature.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
