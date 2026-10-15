"""
CASCADE v3 — BASE-THEN-BID. Forward paper tracker.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance.

HISTORY — two voided versions, and why this one is different
  v1  bought the first green minute at market. Chasing the turn; breakeven
      slippage ~24bp against a median entry bar of 0.96% (doc 52). Void.
  v2  laddered limit bids DOWN into the flush. Better numbers (+0.665%) but
      structurally wrong: rungs fill deeper as price falls, so the position is
      largest in exactly the cascades that never bounce. Knife-catching with a
      hidden tail. Void (doc 53).
  v3  WAIT for the base. Never buys while price is still falling.

THE SPEC
    universe    18 crypto perps with sufficient absolute minute volatility
    signal      close falls >= 3% over 5 minutes
    1. LOW      track the cascade low
    2. LIFT     price must close >= 0.8% above that low
    3. HOLD     10 consecutive minutes WITHOUT making a new low. This is the
                base — the "few levels a bit higher" before it goes up.
    4. BID      rest a limit 0.4% below the current price, but ABOVE the low.
                Maker fill. If it never fills, no trade.
    5. STOP     0.05% under the cascade low. STRUCTURAL, not arbitrary.
    6. TARGET   +1.5%, 60-minute cap.
    NO BASE = NO TRADE. The cascades that keep falling never trigger, which is
    the entire risk control.

    costs       maker 2bp in, maker 2bp on a target exit, taker 5bp + 10bp
                slippage on a stop. Netted in every figure below.

BACKTEST (not a promise) — time-matched control in the same cascade window
    base-then-bid   n=225  +0.378%/trade  win 65.8%  t=+4.42
    control         n=225  +0.062%        win 58.2%
    EDGE            +0.316pp  t=+2.50
    2025            n= 82  +0.345%  t=+2.14
    2026            n=143  +0.397%  t=+4.04
    symbols         17/18 positive
    parameter grid  36/36 configurations positive — a plateau, not a spike

PRE-REGISTERED KILL CRITERION — not amendable mid-run

CASCADE v4 — registered 2026-10-15, doc 79.

Two changes from v3, both validated on 31 symbols never used in development:

  THRESHOLD   a 2% five-minute drop, not 3%. The 3% figure was inherited and
              never tested. At 2% the edge is slightly HIGHER (+0.236% vs
              +0.232%) with 3.5x the trades and t=+7.95 against +3.40.
              Below 2% the edge decays roughly linearly, so 2% is the knee.

  FILTER      close_in_bar on the hourly bar containing the fill must be at
              least 0.5 — the hour closed in the upper half of its own range.
              Out-of-sample this took the edge from +0.222% to +0.652% per
              trade at t=+14.33 and the win rate from 57.1% to 73.5%, while
              keeping half the trades.

  UNIVERSE    39 symbols, up from 18. Doc 78 found profitable SMALL accounts
              trade 22 instruments to the whales' 14; breadth was one of only
              two behavioural markers that separated winners from losers.

Everything else is v3 unchanged: wait for the base (0.8% lift, 10-minute
hold), rest a limit 0.4% below, structural stop 0.05% under the cascade low,
target +1.5%, 60-minute cap, maker in and out, taker plus slippage on stops.

EXPECTED, so that the forward run can falsify it: roughly 87 trades a month
across the universe at about +0.65% per trade and a 73% win rate. Materially
fewer trades, a materially lower win rate, or an edge under +0.3% would all
be evidence the out-of-sample result did not survive contact with live data.

KILL CRITERION: 100 closed trades or 6 months. PASS requires mean > 0 net of
costs AND beating a time-matched control. Early kill on any 20-trade block
worse than -1.5%. Any change to the drop, lift, hold, bid depth, stop, target,
filter threshold or costs voids the run and starts a new one.

MANDATE: research and paper trading only. No live order, brokerage or exchange
account, credential, authentication, or committed capital of any size, on any
signal, under any circumstance.
"""
import os, io, json, glob, zipfile, urllib.request, datetime as dt
import numpy as np, pandas as pd

STATE="/home/claude/qlab/runs/paper/cascade_v4.json"
BASE="https://data.binance.vision/data/futures/um/daily/klines"
SYMS=["SOLUSDT","XRPUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","LTCUSDT","NEARUSDT",
      "APTUSDT","ARBUSDT","OPUSDT","SUIUSDT","INJUSDT","TIAUSDT","ADAUSDT",
      "FILUSDT","ETHUSDT","BNBUSDT","BTCUSDT",
      # breadth: doc 78 found profitable SMALL accounts trade 22 instruments to
      # the whales' 14, and doc 79's out-of-sample validation ran on these.
      "AAVEUSDT","ALGOUSDT","AXSUSDT","CHZUSDT","ATOMUSDT","BCHUSDT","DOTUSDT",
      "ETCUSDT","GALAUSDT","ORDIUSDT","RUNEUSDT","SANDUSDT","SEIUSDT","TONUSDT",
      "TRXUSDT","UNIUSDT","WIFUSDT","CRVUSDT","ENAUSDT","JUPUSDT","TAOUSDT"]
DROP,WIN=0.02,5          # doc 79: 2% is the knee, not 3%
LIFT,HOLD,DEPTH,TP,MAXH=0.008,10,0.004,0.015,60
MAKER,TAKER,SLIP=2/10000,5/10000,10/10000
COLS=["open_time","open","high","low","close","volume","close_time","qav",
      "trades","tbbav","tbqav","ignore"]

REGISTERED={
 "spec_version":3,"registered_on":"2026-10-15","spec_doc":"56-base-then-bid",
 "v1_void":"market entry at first green minute; ~24bp breakeven (doc 52)",
 "v2_void":"laddered bids DOWN into the flush; knife-catching (doc 53)",
 "method":"cascade low -> lift 0.8% -> hold 10min without a new low -> rest a "
          "bid 0.4% below price and above the low -> stop under the low",
 "risk_control":"no base, no trade — the cascades that keep falling never fire",
 "minimum_evidence":"100 closed trades or 6 months",
 "pass":"mean > 0 net of costs AND beats the time-matched control",
 "fail":"mean <= 0 at n=100",
 "early_kill":"any 20-trade block worse than -1.5% mean",
 "amendment":"any spec change voids the run and restarts the clock",
 "backtest":{"n":225,"mean":0.00378,"win":0.658,"t":4.42,
             "control_mean":0.00062,"edge_pp":0.316,"edge_t":2.50,
             "y2025":0.00345,"y2026":0.00397,"symbols":"17/18",
             "grid":"36/36 configurations positive"},
}

def fetch(sym,day):
    try:
        with urllib.request.urlopen(f"{BASE}/{sym}/1m/{sym}-1m-{day}.zip",timeout=60) as r:
            z=zipfile.ZipFile(io.BytesIO(r.read()))
            df=pd.read_csv(z.open(z.namelist()[0]),header=None,names=COLS,
                           usecols=["open_time","open","high","low","close"])
    except Exception: return None
    if str(df.open_time.iloc[0]).startswith("open"): df=df.iloc[1:]
    df["dt"]=pd.to_datetime(pd.to_numeric(df.open_time,errors="coerce"),unit="ms")
    for c in ("open","high","low","close"): df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna(subset=["dt","close"]).set_index("dt").sort_index()

def find_base(C,L,i,n,maxwait=60):
    lo=L[i];k=i
    while k<min(i+maxwait,n-1):
        if L[k]<lo: lo=L[k]
        if C[k]>=lo*(1+LIFT): break
        k+=1
    if k>=min(i+maxwait,n-1) or C[k]<lo*(1+LIFT): return None
    j=k;held=0
    while j<min(k+maxwait,n-1):
        if L[j]<lo: return None
        held+=1
        if held>=HOLD: return j,lo
        j+=1
    return None

def scan_day(sym,day):
    m=fetch(sym,day)
    if m is None or len(m)<200: return []
    C,L,H=m.close.values,m.low.values,m.high.values; n=len(C)
    mv=np.full(n,np.nan); mv[WIN:]=C[WIN:]/C[:-WIN]-1
    out=[];last=-10**9
    for i in np.flatnonzero(mv<=-DROP):
        if i<=last or i+2*MAXH>=n: continue
        r=find_base(C,L,i,n); last=i+MAXH
        if r is None: continue
        base_k,lo=r
        bid=max(C[base_k]*(1-DEPTH),lo*1.0002)
        fill=None
        for q in range(base_k+1,min(base_k+1+MAXH,n)):
            if L[q]<lo: break
            if L[q]<=bid: fill=q; break
        if fill is None: continue
        px=bid*(1+MAKER); stop=lo*(1-0.0005); tgt=px*(1+TP)
        if stop>=px: continue
        # ---- THE v4 FILTER (doc 79) -------------------------------------
        # close_in_bar = (C-L)/(H-L) on the HOURLY bar containing the fill:
        # where that hour closed inside its own range. Take the bounce only
        # when the hour closed in the upper half — visible confirmation that
        # buyers took control, rather than a guess that they will.
        # Out-of-sample on 31 unseen symbols this took the edge from +0.222%
        # to +0.652% per trade at t=+14.33 while keeping half the trades.
        # It scored +0.004 as a STANDALONE predictor (doc 57), which is why
        # it was invisible until the book was conditioned on it.
        hb=m.iloc[:fill+1].resample("1h").agg(
            high=("high","max"),low=("low","min"),close=("close","last")).dropna()
        if len(hb)<2: continue
        hh,hl,hc=float(hb.high.iloc[-1]),float(hb.low.iloc[-1]),float(hb.close.iloc[-1])
        if hh<=hl: continue
        cib=(hc-hl)/(hh-hl)
        if cib < 0.5: continue
        # -----------------------------------------------------------------
        ret,how=None,None
        for q in range(fill+1,min(fill+1+MAXH,n)):
            if L[q]<=stop: ret=(stop*(1-SLIP-TAKER))/px-1; how="stop"; break
            if H[q]>=tgt: ret=(tgt*(1-MAKER))/px-1; how="target"; break
        if ret is None:
            q=min(fill+MAXH,n-1); ret=(C[q]*(1-MAKER))/px-1; how="time"
        out.append(dict(sym=sym,day=day,entry_time=str(m.index[fill]),
                        entry=round(float(px),8),stop=round(float(stop),8),
                        ret=round(float(ret),6),exit=how,close_in_bar=round(cib,4),
                        risk_pct=round(float((px-stop)/px),5)))
    return out

def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    os.makedirs(os.path.dirname(STATE),exist_ok=True)
    return dict(registered=REGISTERED,started=str(dt.date.today()),
                days_done=[],trades=[])

def step(days_back=3):
    s=load(); today=dt.date.today()
    for k in range(2,2+days_back):
        day=str(today-dt.timedelta(days=k))
        if day in s["days_done"]: continue
        found=[]
        for sym in SYMS: found+=scan_day(sym,day)
        s["days_done"].append(day); s["trades"]+=found
        print(f"  {day}: {len(found)} v4 trades",flush=True)
    s["days_done"]=sorted(set(s["days_done"]))[-400:]
    json.dump(s,open(STATE,"w"),indent=1)
    return s

def report(s):
    T=pd.DataFrame(s["trades"])
    print("="*76); print(f"  CASCADE v4  2% DROP + close_in_bar FILTER — forward paper, started {s['started']}")
    print("="*76); print("  Research only. No order, no account, no capital.\n")
    if not len(T): print("  no trades yet"); return
    r=T.ret.values; se=r.std(ddof=1)/np.sqrt(len(r)) if len(r)>1 else np.nan
    print(f"  n={len(r)}  mean {r.mean()*100:+.3f}%  win {float((r>0).mean())*100:.1f}%"
          +(f"  t={r.mean()/se:+.2f}" if se==se and se>0 else ""))
    print(f"\n  evidence: {len(r)}/100 closed trades")
    if len(r)<100: print("  -> NO VERDICT. Below the minimum.")

if __name__=="__main__":
    import sys
    report(step(int(sys.argv[1]) if len(sys.argv)>1 else 3))
