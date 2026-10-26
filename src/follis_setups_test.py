"""follis_' two setups as rules (DK, 26 Oct 2026: "Is it possible to scan for and then execute trades based on these set ups?").
CONTINUATION (long; short mirrored): trend into a tight box (12 bars, range < 3 ATR, prior 30 bars moved > 3 ATR in the trend direction),
  close breaks out of the box within 10 bars.
  - RISK entry: limit at the box edge on the first pullback within 12 bars of the breakout; stop beyond the far side of the box.
  - CONFIRMATION entry: after the breakout, a pullback of >= 0.5 ATR that holds outside the box (higher low), then a break of the
    post-breakout extreme; stop beyond the higher low.
REVERSAL (long; short mirrored): a down-leg of > 5 ATR over 40 bars to a swing low; price then breaks the last lower high before the low
  (change of character) within 30 bars.
  - RISK entry: limit at the midpoint of the base (swing low -> break) on the retest within 12 bars; stop below the swing low.
  - CONFIRMATION entry: after the change of character, a pullback of >= 0.5 ATR holding above the base midpoint, then a break of the
    post-break high; stop below that higher low.
All trades: target 2R, 48-bar cap, costs per market. Control: random bar, same side, same stop distance in ATR, same exits.
Measured in R net of costs; both halves; 5y crypto (27 coins, 1h and 4h from 15-min) and 1y NQ (15-min)."""
import glob, os, sys, numpy as np, pandas as pd
rng = np.random.default_rng(5)
OUT = open("/home/claude/qlab/runs/follis_setups_test.txt", "w")
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); OUT.write(s + "\n"); OUT.flush()
def bars(d, rule):
    return d.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def atr14(C, H, L):
    pc = np.roll(C, 1); pc[0] = C[0]; tr = np.maximum(H-L, np.maximum(abs(H-pc), abs(L-pc))); return pd.Series(tr).rolling(14).mean().bfill().values
def trade(C, H, L, i, side, entry, stop, cost_frac, cap=48):
    """Enter at bar i at `entry` (already filled), resolve 2R target / stop / cap from bar i+1. Returns R net of cost."""
    risk = abs(entry - stop)
    if risk <= 0: return None
    tgt = entry + side*2*risk; n = len(C)
    for j in range(i+1, min(i+cap+1, n)):
        if (side == 1 and L[j] <= stop) or (side == -1 and H[j] >= stop): r = -1.0; break
        if (side == 1 and H[j] >= tgt) or (side == -1 and L[j] <= tgt): r = 2.0; break
    else:
        j = min(i+cap, n-1); r = side*(C[j] - entry)/risk
    return r - cost_frac*entry/risk
def scan(C, H, L, a, cost_frac):
    n = len(C); E = pd.Series(C).ewm(span=50, adjust=False).mean().values; res = {k: [] for k in ("cont_risk", "cont_conf", "rev_risk", "rev_conf")}
    N = 12; i = 60
    while i < n - 60:
        lo, hi = L[i-N+1:i+1].min(), H[i-N+1:i+1].max()
        took = False
        for side in (1, -1):
            # ---------------- continuation
            if hi - lo < 3*a[i] and side*(C[i-N] - C[i-N-30]) > 3*a[i] and side*(C[i] - E[i]) > 0:
                edge, far = (hi, lo) if side == 1 else (lo, hi)
                b = next((j for j in range(i+1, min(i+11, n)) if side*(C[j] - edge) > 0), None)
                if b is None: continue
                # risk entry: first touch of the edge within 12 bars after the breakout
                for j in range(b+1, min(b+13, n-1)):
                    if (side == 1 and L[j] <= edge) or (side == -1 and H[j] >= edge):
                        stop = far - side*0.1*a[i]; r = trade(C, H, L, j, side, edge, stop, cost_frac)
                        if r is not None: res["cont_risk"].append((j, side, r, abs(edge-stop)/a[i]))
                        break
                # confirmation entry
                ext = H[b] if side == 1 else L[b]; pulled = False; hl = None
                for j in range(b+1, min(b+30, n-1)):
                    if not pulled:
                        if side*(H[j] if side == 1 else L[j]) > side*ext: ext = H[j] if side == 1 else L[j]
                        if side*(ext - (L[j] if side == 1 else H[j])) >= 0.5*a[j]: pulled = True; hl = L[j] if side == 1 else H[j]
                        continue
                    if side*((L[j] if side == 1 else H[j]) - edge) < -0.25*a[j]: break          # gave the box back: no setup
                    hl = min(hl, L[j]) if side == 1 else max(hl, H[j])
                    if (side == 1 and H[j] > ext) or (side == -1 and L[j] < ext):
                        stop = hl - side*0.1*a[j]; r = trade(C, H, L, j, side, ext, stop, cost_frac)
                        if r is not None: res["cont_conf"].append((j, side, r, abs(ext-stop)/a[j]))
                        break
                took = True
            # ---------------- reversal (side = direction of the NEW move)
            k = i  # candidate swing extreme at bar i: lowest low of the last 40 bars after a > 5 ATR fall (for side=1)
            w = slice(i-40, i+1)
            if side == 1 and L[i] == L[w].min() and C[i-40] - L[i] > 5*a[i]:
                lh = H[i-15:i].max(); ext0 = L[i]
            elif side == -1 and H[i] == H[w].max() and H[i] - C[i-40] > 5*a[i]:
                lh = L[i-15:i].min(); ext0 = H[i]
            else: continue
            ch = next((j for j in range(i+1, min(i+31, n)) if side*(C[j] - lh) > 0 and ((side == 1 and L[i+1:j+1].min() >= ext0) or (side == -1 and H[i+1:j+1].max() <= ext0))), None)
            if ch is None: continue
            mid = (ext0 + lh)/2
            for j in range(ch+1, min(ch+13, n-1)):
                if (side == 1 and L[j] <= mid) or (side == -1 and H[j] >= mid):
                    stop = ext0 - side*0.25*a[i]; r = trade(C, H, L, j, side, mid, stop, cost_frac)
                    if r is not None: res["rev_risk"].append((j, side, r, abs(mid-stop)/a[i]))
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
                    stop = hl - side*0.1*a[j]; r = trade(C, H, L, j, side, ext, stop, cost_frac)
                    if r is not None: res["rev_conf"].append((j, side, r, abs(ext-stop)/a[j]))
                    break
            took = True
        i += N if took else 1
    # controls: random bars, same side and stop width in ATR
    ctrl = {}
    for k, v in res.items():
        cr = []
        for (j, side, r, w) in v:
            for _ in range(3):
                q = int(rng.integers(60, n-60)); e = C[q]; rr = trade(C, H, L, q, side, e, e - side*w*a[q], cost_frac)
                if rr is not None: cr.append(rr)
        ctrl[k] = cr
    return res, ctrl
def report(label, allres, allctrl):
    say(f"\n== {label}")
    for k in ("cont_risk", "cont_conf", "rev_risk", "rev_conf"):
        v = sorted(allres[k]); x = np.array([r for (_, _, r, _) in v]) if v else np.array([])
        c = np.array(allctrl[k]) if allctrl[k] else np.array([np.nan])
        if len(x) < 20: say(f"  {k:9s} n {len(x)} — too few"); continue
        h = len(x)//2; t = x.mean()/x.std()*np.sqrt(len(x))
        say(f"  {k:9s} n {len(x):5d}  {x.mean():+.3f}R  t {t:+.1f}  win {100*(x>0).mean():.0f}%  H1 {x[:h].mean():+.3f} H2 {x[h:].mean():+.3f}  | random same geometry {np.nanmean(c):+.3f}R  edge {x.mean()-np.nanmean(c):+.3f}R")
if __name__ == "__main__":
    for rule, label in (("4h", "crypto 4-hour, 27 coins, 5 years, cost 0.11%"), ("1h", "crypto 1-hour, 27 coins, 5 years, cost 0.11%")):
        R = {k: [] for k in ("cont_risk", "cont_conf", "rev_risk", "rev_conf")}; Cc = {k: [] for k in R}
        for f in sorted(glob.glob("/home/claude/qlab/data_15m/*.csv")):
            d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True); b = bars(d, rule)
            C, H, L = b.close.values, b.high.values, b.low.values; a = atr14(C, H, L)
            res, ctrl = scan(C, H, L, a, 0.0011)
            for k in R: R[k] += [(b.index[j], s, r, w) for (j, s, r, w) in res[k]]; Cc[k] += ctrl[k]
        report(label, R, Cc)
    d = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True); b = bars(d, "15min")
    C, H, L = b.close.values, b.high.values, b.low.values; a = atr14(C, H, L)
    res, ctrl = scan(C, H, L, a, 1.0/29000)
    report("US Tech 100 15-minute, 1 year, IG 1-pt spread", {k: [(b.index[j], s, r, w) for (j, s, r, w) in v] for k, v in res.items()}, ctrl)
    say("\ncuts: 4 setups x 3 data sets = 12 -> deflated bar t > 2.64 (rule 179)")
