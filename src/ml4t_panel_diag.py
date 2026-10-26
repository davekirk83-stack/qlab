"""Diagnostics on test B (doc 139): net long-short with costs, per-year, ridge coefficients, decile spread."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
import ml4t_combined_test as M
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import lightgbm as lgb
# rebuild the panel exactly as test_b does
import glob, os
syms = [os.path.basename(p)[:-4] for p in glob.glob("data_daily/*USD.csv")]
rows = []; btc_r7 = np.log(M.load("BTCUSD").close).diff(7)
for s in syms:
    try: d = M.load(s)
    except Exception: continue
    if not (len(d) > 250 and d.index[-1] >= pd.Timestamp("2026-10-01", tz="UTC")): continue
    F = M.feats(d); F["btc_r7"] = btc_r7.reindex(F.index); F["fwd7"] = np.log(d.close.shift(-7) / d.close); F["sym"] = s
    dv = (d.close * d.volume).rolling(30).median(); age = np.arange(len(d)); F["dv"] = dv
    rows.append(F[(dv > 1e6).values & (age >= 200)])
P = pd.concat(rows).reset_index(); P = P[P.t.dt.dayofweek == 0]
for col in ("r7", "r30", "r90", "vol30", "d_ema200"): P[col + "_xs"] = P.groupby("t")[col].rank(pct=True)
P["y"] = P.groupby("t")["fwd7"].rank(pct=True)
feat = [c for c in P.columns if c not in ("t", "sym", "fwd7", "y", "dow", "dv")]
P = P.dropna(subset=feat + ["y"]).reset_index(drop=True)
out = []
for name, fn in (("ridge", lambda: make_pipeline(StandardScaler(), M.Ridge(alpha=10.0))), ("lgbm", lambda: lgb.LGBMRegressor(**M.LGB))):
    P["p"] = M.walk(P[feat], P.y, fn, 7, P.t)
    wk = []; pl = ps = set()
    for t, g in P.dropna(subset=["p"]).groupby("t"):
        k = max(1, len(g) // 5); top = g.nlargest(k, "p"); bot = g.nsmallest(k, "p")
        tl = len(set(top.sym) ^ pl) / (2 * k) if pl else 1; ts = len(set(bot.sym) ^ ps) / (2 * k) if ps else 1
        pl, ps = set(top.sym), set(bot.sym)
        L = np.expm1(top.fwd7).mean(); S = np.expm1(bot.fwd7).mean(); E = np.expm1(g.fwd7).mean()
        # costs: 20bp/side each leg; perp funding on the short leg ~ +0.01%/8h paid by longs -> shorts earn it; ignore (conservative)
        wk.append(dict(t=t, L=L - E, S=E - S, LS=(L - S) / 2 - 0.0020 * (tl + ts), bot_med_dv=bot.dv.median(), top_med_dv=top.dv.median(), n=len(g)))
    W = pd.DataFrame(wk).set_index("t"); sh = lambda r: r.mean() / r.std() * np.sqrt(52); tst = lambda r: r.mean() / r.std() * np.sqrt(len(r))
    for seg, m in (("dev", W.index < M.HOLD), ("HOLDOUT", W.index >= M.HOLD)):
        w = W[m]
        out.append(f"{name:5} {seg:7} weeks {len(w):3}  net L/S (half each side) Sharpe {sh(w.LS):5.2f} t {tst(w.LS):4.1f} total {((1+w.LS).prod()-1)*100:+6.1f}% | "
                   f"long-vs-EW Sharpe {sh(w.L):5.2f}  EW-vs-short Sharpe {sh(w.S):5.2f} | median $vol top {w.top_med_dv.median()/1e6:.1f}m bottom {w.bot_med_dv.median()/1e6:.1f}m")
    yr = W.LS.groupby(W.index.year).agg(lambda r: r.mean() / r.std() * np.sqrt(52))
    out.append(f"{name:5} net L/S Sharpe by year: " + "  ".join(f"{y}:{v:+.2f}" for y, v in yr.items()))
# ridge coefficients (fit on all dev data)
m = make_pipeline(StandardScaler(), M.Ridge(alpha=10.0)); dev = P.t < M.HOLD - pd.Timedelta(days=7); m.fit(P.loc[dev, feat], P.loc[dev, "y"])
co = pd.Series(m[-1].coef_, index=feat).sort_values(key=abs, ascending=False)
out.append("ridge standardised coefficients (top 8): " + ", ".join(f"{k} {v:+.4f}" for k, v in co.head(8).items()))
txt = "\n".join(out); print(txt); open("runs/ml4t_panel_diag.txt", "w").write(txt + "\n")
