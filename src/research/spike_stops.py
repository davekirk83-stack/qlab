"""DK 27 Nov review: live Spike NQ short 19 Nov was stopped (-229 pts) then moved +176 our way within 2h. Tests the Spike engine's stop
placement on the 15-min cash-session history (src/ig_spike_engine.py rule), NQ and US500, spread 1 pt NQ / 0.4 US500:
  live    = stop at the confirming bar's opposite extreme
  spike   = stop at the SPIKE bar's opposite extreme (wider)
  half    = stop entry -/+ 0.5 x spike range;  full = entry -/+ 1 x spike range
Target stays entry +/- 1 x spike range; exit after 8 bars or at the cash close. Results in points and in units of the spike range."""
import warnings; warnings.filterwarnings("ignore")
import os, numpy as np, pandas as pd
F = {"NQ": ("data_nq_cache/nq_5m.csv", 1.0), "US500": ("data_ig_cache/USA500IDXUSD_5m.csv", 0.4)}

def load(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    d = d[["open", "high", "low", "close"]].astype(float)
    return d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()

def run(d, cost, mode):
    lt = d.index.tz_convert("America/New_York"); hh = lt.hour + lt.minute / 60; day = np.array(lt.date); sess = (hh >= 9.5) & (hh < 16)
    O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; rng = H - L
    dm = pd.Series(np.where(sess, rng, np.nan)).groupby(day).mean().dropna(); ref5 = dm.shift(1).rolling(5).mean()
    out = []; i = 2; n = len(C)
    while i < n - 1:
        j = i - 1
        if not (sess[i] and sess[j] and day[i] == day[j]): i += 1; continue
        ref = ref5.get(day[i], np.nan)
        if not (np.isfinite(ref) and ref > 0 and rng[j] >= 3 * ref): i += 1; continue
        r = rng[j]; s = 1 if C[j] > O[j] else -1
        if s == 1 and not (H[i] > H[j] + 0.25 * r and C[i] > C[j]): i += 1; continue
        if s == -1 and not (L[i] < L[j] - 0.25 * r and C[i] < C[j]): i += 1; continue
        e = C[i]
        st = {"live": (L[i] if s == 1 else H[i]), "spike": (L[j] if s == 1 else H[j]),
              "half": e - s * 0.5 * r, "full": e - s * 1.0 * r}[mode]
        if s * (e - st) <= 0: i += 1; continue
        tp = e + s * r; x = None
        for q in range(i + 1, min(n, i + 9)):
            if day[q] != day[i] or not sess[q]: x = C[q - 1]; break
            if (s == 1 and L[q] <= st) or (s == -1 and H[q] >= st): x = st; break
            if (s == 1 and H[q] >= tp) or (s == -1 and L[q] <= tp): x = tp; break
            x = C[q]
        pts = s * (x - e) - cost
        out.append((d.index[i], pts, pts / abs(e - st), pts / r)); i += 9
    return pd.DataFrame(out, columns=["t", "pts", "R", "per_spike"])

if __name__ == "__main__":
    rows = []
    for m, (f, cost) in F.items():
        d = load(f)
        for mode in ("live", "spike", "half", "full"):
            t = run(d, cost, mode); h = len(t) // 2
            rows.append(dict(m=m, stop=mode, n=len(t), since=str(t.t.iloc[0].date()) if len(t) else "", win=(t.pts > 0).mean(), mean_pts=t.pts.mean(),
                             per_risk_R=t.R.mean(), per_spike=t.per_spike.mean(), h1=t.per_spike[:h].mean(), h2=t.per_spike[h:].mean()))
    r = pd.DataFrame(rows); r.to_csv("runs/research/spike_stops.csv", index=False); pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
