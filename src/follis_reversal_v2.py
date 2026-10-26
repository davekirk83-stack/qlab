"""Reversal setup, second attempt with CONTEXT (DK 26 Oct: "give the reversal thing another try after some further refinements").
PRE-DECLARED before running (rule 179) — nothing below was changed after seeing results:
  Base pattern (doc 135): a > 5 ATR leg over 40 bars into a swing extreme; within 30 bars a close through the last lower high
  (change of character) with no new extreme. Risk entry = limit at the base midpoint; confirmation = higher low then break.
  Refinement A — LIQUIDITY SWEEP: the swing extreme must take out the PREVIOUS UTC DAY's low (high for shorts) and price must close
    back above it within 3 bars (a failed breakdown), i.e. the reversal starts from a stop-run at a level everyone can see.
  Refinement B — CAPITULATION: A, plus the swing bar's volume > 2x the median volume of the prior 100 bars.
  Exits: 2R target (as before) and 1.5R target. 48-bar cap.
  Grid: {A, B} x {risk, confirm} x {2R, 1.5R} = 8 cuts x 3 data sets = 24 -> deflated bar t > 2.87.
Control: random bar, same side, same stop width in ATR, same exits."""
import glob, numpy as np, pandas as pd
from scipy.stats import norm
rng = np.random.default_rng(9); OUT = open("/home/claude/qlab/runs/follis_reversal_v2.txt", "w")
def say(*a): s = " ".join(map(str, a)); print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
def atr14(C, H, L):
    pc = np.roll(C, 1); pc[0] = C[0]; tr = np.maximum(H-L, np.maximum(abs(H-pc), abs(L-pc))); return pd.Series(tr).rolling(14).mean().bfill().values
def trade(C, H, L, i, side, entry, stop, cost, tR, cap=48):
    risk = abs(entry-stop)
    if risk <= 0: return None
    tgt = entry + side*tR*risk; n = len(C)
    for j in range(i+1, min(i+cap+1, n)):
        if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop): return -1.0 - cost*entry/risk
        if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt): return tR - cost*entry/risk
    j = min(i+cap, n-1); return side*(C[j]-entry)/risk - cost*entry/risk
def scan(b, cost):
    C, H, L, V = b.close.values, b.high.values, b.low.values, b.volume.values; a = atr14(C, H, L); n = len(C)
    day = b.index.floor("D"); dh = b.high.groupby(day).max(); dl = b.low.groupby(day).min()
    pdh = pd.Series(day).map(dh.shift(1)).values; pdl = pd.Series(day).map(dl.shift(1)).values
    vmed = pd.Series(V).rolling(100).median().values
    out = {f"{f}|{e}|{t}": [] for f in ("A", "B") for e in ("risk", "conf") for t in (2.0, 1.5)}
    i = 60
    while i < n - 60:
        hit = False
        for side in (1, -1):
            w = slice(i-40, i+1)
            if side == 1:
                if not (L[i] == L[w].min() and C[i-40] - L[i] > 5*a[i]): continue
                lvl = pdl[i]; swept = np.isfinite(lvl) and L[i] < lvl and any(C[k] > lvl for k in range(i, min(i+4, n)))
                lh = H[i-15:i].max(); ext0 = L[i]
            else:
                if not (H[i] == H[w].max() and H[i] - C[i-40] > 5*a[i]): continue
                lvl = pdh[i]; swept = np.isfinite(lvl) and H[i] > lvl and any(C[k] < lvl for k in range(i, min(i+4, n)))
                lh = L[i-15:i].min(); ext0 = H[i]
            if not swept: continue
            cap_ok = np.isfinite(vmed[i]) and V[i] > 2*vmed[i]
            ch = next((j for j in range(i+1, min(i+31, n)) if side*(C[j]-lh) > 0 and ((side == 1 and L[i+1:j+1].min() >= ext0) or (side == -1 and H[i+1:j+1].max() <= ext0))), None)
            if ch is None: continue
            hit = True; mid = (ext0 + lh)/2; filters = ["A"] + (["B"] if cap_ok else [])
            for j in range(ch+1, min(ch+13, n-1)):
                if (side == 1 and L[j] <= mid) or (side == -1 and H[j] >= mid):
                    stop = ext0 - side*0.25*a[i]
                    for tR in (2.0, 1.5):
                        r = trade(C, H, L, j, side, mid, stop, cost, tR)
                        if r is not None:
                            for f in filters: out[f"{f}|risk|{tR}"].append((b.index[j], side, r, abs(mid-stop)/a[i]))
                    break
            ext = H[ch] if side == 1 else L[ch]; pulled = False; hl = None
            for j in range(ch+1, min(ch+30, n-1)):
                if not pulled:
                    if side*((H[j] if side == 1 else L[j]) - ext) > 0: ext = H[j] if side == 1 else L[j]
                    if side*(ext - (L[j] if side == 1 else H[j])) >= 0.5*a[j]: pulled = True; hl = L[j] if side == 1 else H[j]
                    continue
                if side*((L[j] if side == 1 else H[j]) - mid) < 0: break
                hl = min(hl, L[j]) if side == 1 else max(hl, H[j])
                if (side == 1 and H[j] > ext) or (side == -1 and L[j] < ext):
                    stop = hl - side*0.1*a[j]
                    for tR in (2.0, 1.5):
                        r = trade(C, H, L, j, side, ext, stop, cost, tR)
                        if r is not None:
                            for f in filters: out[f"{f}|conf|{tR}"].append((b.index[j], side, r, abs(ext-stop)/a[j]))
                    break
        i += 12 if hit else 1
    ctrl = {}
    for k, v in out.items():
        tR = float(k.split("|")[2]); cr = []
        for (_, side, _, wdt) in v:
            for _ in range(3):
                q = int(rng.integers(60, n-60)); e = C[q]; rr = trade(C, H, L, q, side, e, e - side*wdt*a[q], cost, tR)
                if rr is not None: cr.append(rr)
        ctrl[k] = cr
    return out, ctrl
def report(label, R, Cc):
    say(f"\n== {label}")
    for k in R:
        v = sorted(R[k]); x = np.array([r for (_, _, r, _) in v])
        if len(x) < 15: say(f"  {k:14s} n {len(x)} — too few"); continue
        c = np.mean(Cc[k]); h = len(x)//2; t = x.mean()/x.std()*np.sqrt(len(x))
        say(f"  {k:14s} n {len(x):4d}  {x.mean():+.3f}R  t {t:+.1f}  win {100*(x>0).mean():.0f}%  H1 {x[:h].mean():+.3f} H2 {x[h:].mean():+.3f}  | random {c:+.3f}R  edge {x.mean()-c:+.3f}R")
def agg(d, rule, vol="volume"):
    return d.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", vol: "sum"}).rename(columns={vol: "volume"}).dropna()
if __name__ == "__main__":
    for rule, label in (("4h", "crypto 4h, 27 coins, 5y"), ("1h", "crypto 1h, 27 coins, 5y")):
        R, Cc = None, None
        for f in sorted(glob.glob("/home/claude/qlab/data_15m/*.csv")):
            d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True)
            o, c = scan(agg(d, rule), 0.0011)
            R = {k: (R[k] if R else []) + o[k] for k in o}; Cc = {k: (Cc[k] if Cc else []) + c[k] for k in c}
        report(label, R, Cc)
    d = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True)
    o, c = scan(agg(d, "15min", "vol"), 1.0/29000); report("US Tech 100 15m, 1y", o, c)
    say(f"\n24 cuts -> deflated bar t > {norm.ppf(1-0.05/24):.2f}")
