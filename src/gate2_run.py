"""Doc 198 — the candidates re-judged by GATE v2 (walk-forward, multiple-testing adjusted t, cost x1.5, random entries, last-year holdout)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, paperbook7 as P7
from gate_books import ign_prep, ign_signals, ign_manage, ign_eligible, session15, load5, spike_signals, NY, sigframe
import market_search_2 as M2, trend_futures_bets as TF
ONLY = sys.argv[1] if len(sys.argv) > 1 else ""
R = []
def go(name, items, daily=False):
    if ONLY and ONLY not in name: return
    r = G.judge2(name, items, daily=daily); R.append(r); print(G.line2(r), flush=True)
d = ign_prep(); d["eligible"] = ign_eligible(d)
go("v2 IGNITION v1.1 US hours", [("NQ", d, ign_signals, {"manage": ign_manage})])
q = session15(load5("data_ig_cache/USA30IDXUSD_5m.csv"), NY, 570, 960, 2.4); go("v2 SPIKE Wall Street", [("DJI", q, spike_signals, {"flat_at_session_end": True})])
nb = M2.nb_prep("data_nq_cache/nq_5m.csv", 1.0); go("v2 NOISEBAND US Tech 100", [("NQ", nb, M2.nb_signals, {"manage": M2.nb_manage, "flat_at_session_end": True})])
go("v2 TURN-OF-MONTH 6 indices", [(k, M2.daily(k, .0002, 0.05), M2.tom_signals, {}) for k in ("SPX", "NDX", "DJI", "RUT", "DAX", "FTSE")], daily=True)
go("v2 TREND100 IG quarterly bets 18 markets", TF.items, daily=True)
import market_search_3 as M3
gd = load5("data_ig_cache/XAUUSD_5m.csv")[["open", "high", "low", "close"]].astype(float); gd["cost"] = 0.4; gd["atr"] = G.atr(gd).shift(1)
lt = gd.index.tz_convert("UTC"); gd["session"] = pd.Series(lt.date, index=gd.index).astype(str); gd["eligible"] = (lt.hour >= 6) & (lt.hour < 19)
go("v2 GOLD London breakout of Asian range", [("XAU", gd, M3.gold_signals, {"flat_at_session_end": True})])
open(f"{G.OUT}/gate2_{ONLY or 'all'}.txt", "w").write("\n".join(G.line2(r) for r in R) + "\n")
