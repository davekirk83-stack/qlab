"""
DK 27 Nov: "look closely at the mistakes ... especially good 'winning trades' which eventually lost us money."
For every live and demo trade we hold: how far it ran in our favour (MFE) and against us (MAE) before it closed,
from the runners' own 5-minute bars. Flags trades that were up at least 1x the size of their final loss (or up >= 0.5 ATR-ish)
and still closed at a loss, plus what price did in the 2 hours after the exit.
Output: runs/research/trade_excursions.csv and a printed summary.
"""
import glob, json, os, numpy as np, pandas as pd

R = "runs"

def bars(mkt):
    fs = []
    for v in ("ig_live", "ig_demo"):
        fs += glob.glob(f"{R}/{v}/bars_{mkt}_2026-*.csv")
        if mkt == "NQ": fs += glob.glob(f"{R}/{v}/bars_2026-*.csv")
    ds = []
    for f in fs:
        try:
            x = pd.read_csv(f, header=None).iloc[:, :5]; x.columns = "t o h l c".split()
            x["t"] = pd.to_datetime(x.t, utc=True, errors="coerce"); ds.append(x.dropna())
        except Exception: pass
    if not ds: return None
    d = pd.concat(ds).drop_duplicates("t", keep="last").set_index("t").sort_index()
    return d[["o", "h", "l", "c"]].astype(float)

def T(s): return pd.Timestamp(s).tz_localize("UTC") if pd.Timestamp(s).tzinfo is None else pd.Timestamp(s).tz_convert("UTC")

rows = []
def add(venue, engine, mkt, side, opened, closed, entry, exit_, gbp, how, size=None, entry_at_open=False):
    rows.append(dict(venue=venue, engine=engine, mkt=mkt, side=int(side), opened=T(opened), closed=T(closed), entry=float(entry),
                     exit=float(exit_) if pd.notna(exit_) else np.nan, gbp=float(gbp) if pd.notna(gbp) else np.nan, how=how, size=size,
                     entry_at_open=entry_at_open))

for v in ("ig_live", "ig_demo"):
    for _, r in pd.read_csv(f"{R}/{v}/trades.csv").iterrows():
        add(v, "AD/Ignition", "NQ", r.side, r.opened, r.closed, r.ig_entry, r.ig_exit, np.nan, r.how)
    for _, r in pd.read_csv(f"{R}/{v}/wvb_trades.csv").iterrows():
        add(v, "WVB range", r.market, r.side, r.opened_bar, r.closed, r.entry, r.exit, r.gbp, r.how, r["size"])
    f = f"{R}/{v}/spike_trades.csv"
    if os.path.exists(f):
        for _, r in pd.read_csv(f).iterrows():
            add(v, "Spike", r.market, r.side, r.opened_bar, r.closed, r.entry, r.exit, r.gbp, r.how, r["size"])
    for _, r in pd.read_csv(f"{R}/{v}/range_trades.csv").iterrows():
        legs = json.loads(r.detail); px = [l["px"] for l in legs if l.get("px")]; ex = [l["exit"] for l in legs if l.get("exit") not in (None, "NaN") and pd.notna(l.get("exit"))]
        if not px or not ex: continue
        add(v, "Range ladder", r.instr, 1 if r.side == "L" else -1, r.opened, r.closed, np.mean(px), np.mean(ex), r.gbp, r.how)
for _, r in pd.read_csv(f"{R}/ig_daily_live/trades.csv").iterrows():
    mk = "US500" if r.market == "US500" else r.market
    add("ig_live", "Daily " + r.book, mk, 1, str(r.entered) + " 14:30", str(r.closed) + " 21:00", r.entry, r.exit, r.pnl_gbp, r.why, r["size"], True)

cache = {}
out = []
for t in rows:
    if t["mkt"] not in cache: cache[t["mkt"]] = bars(t["mkt"])
    d = cache[t["mkt"]]
    if d is None: continue
    start = t["opened"] if t["entry_at_open"] else t["opened"] + pd.Timedelta("5min")
    w = d[(d.index >= start) & (d.index < t["closed"])]
    if w.empty: continue
    s = t["side"]; e = t["entry"]
    mfe = (w.h.max() - e) if s == 1 else (e - w.l.min())
    mae = (e - w.l.min()) if s == 1 else (w.h.max() - e)
    t_mfe = (w.h.idxmax() if s == 1 else w.l.idxmin())
    pts = (t["exit"] - e) * s if pd.notna(t["exit"]) else np.nan
    after = d[(d.index >= t["closed"]) & (d.index < t["closed"] + pd.Timedelta("2h"))]
    post = ((after.c.iloc[-1] - t["exit"]) * s) if (len(after) and pd.notna(t["exit"])) else np.nan
    # bars are mid-ish; compare to the 5m range to normalise
    rng = (d.h - d.l).rolling(48).mean().reindex([w.index[0]]).iloc[0]
    out.append({**t, "pts": pts, "mfe": mfe, "mae": mae, "mins_to_mfe": (t_mfe - start).total_seconds() / 60,
                "mins_held": (t["closed"] - start).total_seconds() / 60, "post2h": post, "bar_rng": rng,
                "gave_back": (mfe - pts) if pd.notna(pts) else np.nan})

X = pd.DataFrame(out)
X["loss"] = X.pts < 0
X["was_up_1x"] = X.loss & (X.mfe >= X.pts.abs())            # was up at least as much as it finally lost
X["was_up_half"] = X.loss & (X.mfe >= 0.5 * X.pts.abs())
X["mfe_in_bar_rng"] = X.mfe / X.bar_rng
os.makedirs("runs/research", exist_ok=True); X.drop(columns=["entry_at_open"]).to_csv("runs/research/trade_excursions.csv", index=False)

pd.set_option("display.width", 250)
cols = ["venue", "engine", "mkt", "side", "opened", "how", "pts", "mfe", "mae", "mins_to_mfe", "mins_held", "post2h", "gbp"]
print("ALL TRADES with excursions:", len(X), "of", len(rows))
for (v, eng), g in X.groupby(["venue", "engine"]):
    L = g[g.loss]
    print(f"\n== {v} {eng}: n {len(g)}, losers {len(L)}, losers that were up >= their final loss {int(g.was_up_1x.sum())}, up >= half {int(g.was_up_half.sum())}; "
          f"winners' avg MFE captured {np.nanmean((g[~g.loss].pts / g[~g.loss].mfe).clip(upper=1)):.0%}")
    print(g[cols].round(1).to_string(index=False))
