"""Cross-asset setup screener (DK 27 Nov 22:18: "Use screening to find set ups to trade across all asset classes"). DATA + PAPER ONLY -
no orders anywhere (promotion rule: nothing goes on DK's money until 2 weeks / 20+ demo trades inside the backtest range).
Setups (backtests: runs/research/cross_asset_s3.csv, creation_combos.csv; doc 279):
  S3   RSI(2) < 10 on the daily close, in DK v2's context (uptrend above the 50- and 200-day, or a deep flush >= 15% off the 20-day high).
       Buy at the close, sell the first close above the 5-day mean, 10-day limit. 'S3+' = RSI(2) < 5 (stronger: US stocks +0.66%/trade).
       Backtest per trade: US stocks +0.49% (55,782 trades 2005-26, 21/22 years +, survivorship caveat), indices +0.48%, commodities +0.55%,
       crypto +0.43% (RSI2<5 +0.98%), FX +0.08%. Bonds negative -> excluded.
  S2   crypto only: a resting bid for the coming UTC day at the open x (1 - 1 daily sigma), only in v2's context; hold to the NEXT 23:00
       UTC. Backtest: BTC +0.57%/trade, 9 alts +0.82%, 10/10 coins, both halves positive.
Modes: MODE=us (run ~20 min before the NYSE close; uses Alpaca SIP to 16 min ago) / MODE=crypto (run ~23:45 UTC; Binance public data).
Writes runs/screener/latest_<mode>.md, appends runs/screener/signals.csv, and keeps a paper ledger runs/screener/paper.csv
(opened at the screen price, closed by the same exit rule) so the forward test scores itself."""
import os, sys, json, time, glob, urllib.request, urllib.parse
import numpy as np, pandas as pd
MODE = os.environ.get("MODE", "us"); OUT = "runs/screener"; os.makedirs(OUT, exist_ok=True)
NOW = pd.Timestamp.now(tz="UTC")
ETFS = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow", "IWM": "Russell 2000", "EWG": "DAX (Germany)", "EWU": "FTSE (UK)", "EWJ": "Nikkei (Japan)",
        "GLD": "gold", "SLV": "silver", "CPER": "copper", "USO": "oil", "UNG": "natgas", "FXE": "EURUSD", "FXB": "GBPUSD", "FXA": "AUDUSD", "FXY": "JPY", "FXC": "CAD"}
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")

def http(url, headers=None):
    for a in range(5):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60))
        except Exception: time.sleep(2 + 3 * a)
    return None

def alpaca_daily(syms):
    H = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["ALPACA_API_SECRET_KEY"]}
    end = (NOW - pd.Timedelta("16min")).strftime("%Y-%m-%dT%H:%M:%SZ"); start = (NOW - pd.Timedelta("420D")).strftime("%Y-%m-%dT00:00:00Z"); out = {}
    for i in range(0, len(syms), 50):
        chunk = syms[i:i + 50]; tok = None
        while True:
            q = {"symbols": ",".join(chunk), "timeframe": "1Day", "start": start, "end": end, "limit": 10000, "adjustment": "all", "feed": "sip"}
            if tok: q["page_token"] = tok
            r = http("https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q), H)
            if not r: break
            for s, bars in (r.get("bars") or {}).items(): out.setdefault(s, []).extend(bars)
            tok = r.get("next_page_token")
            if not tok: break
            time.sleep(0.3)
    D = {}
    for s, b in out.items():
        x = pd.DataFrame(b); x.index = pd.to_datetime(x.t).dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        D[s] = x.rename(columns={"o": "o", "h": "h", "l": "l", "c": "c"})[["o", "h", "l", "c"]].astype(float)
    return D

def binance_daily(sym):
    r = http(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1d&limit=420")
    x = pd.DataFrame(r).iloc[:, :5]; x.columns = ["t", "o", "h", "l", "c"]; x.index = pd.to_datetime(x.t, unit="ms"); return x[["o", "h", "l", "c"]].astype(float)

def prep(D):
    D = D.copy(); D["sig"] = D.c.pct_change().rolling(14).std().shift(1)
    m50, m200 = D.c.rolling(50).mean(), D.c.rolling(200, min_periods=150).mean()
    D["up"] = (D.c > m50) & (D.c > m200); D["deep"] = D.c <= D.h.rolling(20).max() * 0.85; D["ctx"] = D.up | D.deep
    dd = D.c.diff(); u = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    D["rsi2"] = 100 - 100 / (1 + u / dn.replace(0, np.nan)); D["ma5"] = D.c.rolling(5).mean()
    D["ibs"] = (D.c - D.l) / (D.h - D.l).replace(0, np.nan); D["shock"] = D.c.pct_change() <= -3 * D.sig; return D

def s3_ok(r, commodity=False):
    """doc 280 refined S3: RSI(2) < 10 in v2 context, close in the bottom quarter of the day's range (not for commodities, where it hurt),
    and not a > 3-sigma shock day (news/earnings, not a pullback)."""
    return bool(r.rsi2 < 10 and r.ctx and not r.shock and (commodity or (np.isfinite(r.ibs) and r.ibs < 0.25)))

def ledger_update(P, data):
    """close open paper trades by the S3 exit (close > 5-day mean, 10-day limit) or the S2 exit (next 23:00 UTC -> approximated by next daily close)."""
    for i, p in P[P.status == "open"].iterrows():
        D = data.get(p.sym)
        if D is None: continue
        after = D[D.index > pd.Timestamp(p.date)]
        if not len(after): continue
        if p.setup.startswith("S3"):
            hit = after[after.c > after.ma5]; k = hit.index[0] if len(hit) else (after.index[9] if len(after) >= 10 else None)
        else: k = after.index[0] if len(after) >= 1 and p.get("filled", True) else None
        if k is None: continue
        px = float(D.at[k, "c"]); cost = 0.0014 if p.cls == "crypto" else 0.001
        P.loc[i, ["status", "exit_date", "exit", "ret_pct"]] = ["closed", str(k.date()), px, round(100 * (px * (1 - cost) / (p.entry * (1 + cost)) - 1), 3)]
    return P

def main():
    rows = []
    if MODE == "us":
        ny = NOW.tz_convert("America/New_York"); mins = ny.hour * 60 + ny.minute
        if os.environ.get("FORCE") != "1" and not (ny.dayofweek < 5 and 905 <= mins <= 950): print("not ~20 min before the NYSE close:", ny); return
        stocks = sorted({os.path.basename(f)[:-7].replace("-", ".") for f in glob.glob("data_stocks/*.csv.gz") if not f.endswith(".L.csv.gz")})
        data = {s: prep(x) for s, x in alpaca_daily(stocks + list(ETFS)).items() if len(x) >= 210}
        spy = data.get("SPY"); spx_dn = bool(spy is not None and spy.c.iloc[-1] < spy.c.rolling(200).mean().iloc[-1])
        for s, D in data.items():
            r = D.iloc[-1]; cls = "macro ETF" if s in ETFS else "US stock"
            if s3_ok(r, commodity=s in ("GLD", "SLV", "CPER", "USO", "UNG")):
                rows.append(dict(setup="S3+" if r.rsi2 < 5 else "S3", tier=("A" if (spx_dn and not r.up) else ("B" if (spx_dn or not r.up) else "C")) if cls == "US stock" else ("A" if (spx_dn or not r.up) else "B"), sym=s, name=ETFS.get(s, ""), cls=cls, price=round(r.c, 2), rsi2=round(r.rsi2, 1), ibs=round(r.ibs, 2),
                                 context="uptrend" if r.up else "deep flush", exit_rule=f"sell first close > 5d mean (now {r.ma5:.2f}); 10-day limit"))
    else:
        data = {}
        for s in COINS:
            # 28 Nov fix: GitHub's scheduler can fire hours late. Near the UTC close (>= 23:00) today's bar is (almost) complete: S3 on it,
            # S2 bid for TOMORROW at ~today's close x (1 - sigma). Otherwise (a late run after midnight): S3 on YESTERDAY's completed bar
            # (flagged late), and the S2 bid for TODAY from today's actual open - the backtest rule exactly.
            raw = binance_daily(s); near_close = NOW.hour == 23
            D = prep(raw if near_close else raw.iloc[:-1]); data[s] = D; r = D.iloc[-1]
            late = "" if near_close else f" (signal from {D.index[-1].date()} close; screen ran late at {NOW:%H:%M} UTC)"
            if s3_ok(r):
                rows.append(dict(setup="S3+" if r.rsi2 < 5 else "S3", tier="-", sym=s, cls="crypto", price=r.c, rsi2=round(r.rsi2, 1), ibs=round(r.ibs, 2), context="uptrend" if r.up else "deep flush",
                                 exit_rule=f"sell first daily close > 5d mean (now {r.ma5:.4g}); 10-day limit" + late))
            sig = D.c.pct_change().rolling(14).std().iloc[-1]
            if bool(r.up or r.deep):
                base, day = (r.c, "tomorrow (UTC)") if near_close else (float(raw.o.iloc[-1]), f"today {NOW.date()} (UTC, from its open)")
                bid = base * (1 - sig); hit = (not near_close) and float(raw.l.iloc[-1]) < bid
                rows.append(dict(setup="S2 band bid", sym=s, cls="crypto", price=float(raw.c.iloc[-1]), rsi2=round(r.rsi2, 1), context="uptrend" if r.up else "deep flush",
                                 bid=float(f"{bid:.6g}"), exit_rule=f"resting bid for {day}; if filled, sell at 23:00 UTC the day after" + (" — ALREADY FILLED today" if hit else "")))
    S = pd.DataFrame(rows)
    stamp = NOW.strftime("%Y-%m-%d %H:%M UTC")
    if len(S):
        S.insert(0, "screened", stamp); S = S.sort_values([c for c in ("tier", "setup", "rsi2") if c in S])
        hdr = not os.path.exists(f"{OUT}/signals.csv"); S.to_csv(f"{OUT}/signals.csv", mode="a", header=hdr, index=False)
    md = [f"# Screener ({MODE}) — {stamp}", "", "Data and paper only. No orders are placed. US stocks: tier A = own deep flush AND S&P below its 200-day (~+2%/trade); B = one of the two (~+0.3-0.5%); C = calm uptrend (no edge after checker - paper only). ETFs: A = deep flush or S&P below 200-day. Crypto: no tier (it reverses there). Doc 280.", ""]
    md += [S.drop(columns=["screened"]).to_markdown(index=False) if len(S) else "No setups today."]
    open(f"{OUT}/latest_{MODE}.md", "w").write("\n".join(md) + "\n"); print("\n".join(md))
    # paper ledger
    pf = f"{OUT}/paper.csv"
    P = pd.read_csv(pf) if os.path.exists(pf) else pd.DataFrame(columns=["date", "sym", "cls", "setup", "entry", "status", "exit_date", "exit", "ret_pct"])
    if "tier" not in P: P["tier"] = ""
    P = ledger_update(P, data)
    today = str(NOW.tz_convert("America/New_York" if MODE == "us" else "UTC").date())
    for r in rows:
        if r["setup"].startswith("S3") and not ((P.sym == r["sym"]) & (P.status == "open")).any():
            P.loc[len(P)] = [today, r["sym"], r["cls"], r["setup"], r["price"], "open", "", np.nan, np.nan, r.get("tier", "")]
    P.to_csv(pf, index=False)
    c = P[P.status == "closed"]
    if len(c): print(f"\npaper: {len(c)} closed, mean {c.ret_pct.astype(float).mean():+.3f}%/trade, win {(c.ret_pct.astype(float) > 0).mean():.0%}; open {(P.status == 'open').sum()}")

if __name__ == "__main__":
    main()
