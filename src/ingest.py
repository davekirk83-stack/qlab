import json, os, sys, glob, hashlib, pandas as pd
TR = "/root/.claude/projects/-home-claude/6103913e-5d93-5930-ba67-b97312457994/tool-results"
OUT = "/home/claude/qlab/data"
MAN = "/home/claude/qlab/data/_manifest.json"

def parse(path):
    raw = open(path).read()
    try: d = json.loads(raw)
    except Exception: return None
    if isinstance(d, list) and d and isinstance(d[0], dict) and "text" in d[0]:
        d = json.loads(d[0]["text"])
    if isinstance(d, dict):
        for k in ("historical","data","results"):
            if k in d: d = d[k]; break
    if not isinstance(d, list) or not d: return None
    df = pd.DataFrame(d)
    if "date" not in df or "close" not in df: return None
    return df

man = json.load(open(MAN)) if os.path.exists(MAN) else {}
for p in sorted(glob.glob(f"{TR}/mcp-FMP-*.txt")):
    df = parse(p)
    if df is None: continue
    sym = df["symbol"].iloc[0] if "symbol" in df else None
    if not sym: continue
    for c in ("open","high","low","close","volume"):
        if c not in df: df[c] = df["close"] if c!="volume" else 0.0
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date","open","high","low","close","volume"]].sort_values("date")
    df = df[~df.date.duplicated(keep="first")].reset_index(drop=True)
    dst = f"{OUT}/{sym}.csv"
    df.to_csv(dst, index=False)
    man[sym] = {"rows": len(df), "start": str(df.date.min().date()),
                "end": str(df.date.max().date()),
                "source": "FMP historical-price-eod-full",
                "sha256": hashlib.sha256(open(dst,'rb').read()).hexdigest()[:16]}
    print(f"{sym:8s} {len(df):5d} bars  {df.date.min().date()} -> {df.date.max().date()}")
json.dump(man, open(MAN,"w"), indent=1)
