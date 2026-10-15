"""
STOOQ FETCHER — free 20y daily OHLCV for equities, ETFs, bonds, commodities.

Stooq gates downloads behind a JavaScript proof-of-work (hashcash): find n such
that sha256(challenge + n) begins with four hex zeros, POST it to /__verify, and
the session cookie is issued. No account, no key, no terms circumvented beyond
doing in Python what the page does in JS.

This exists because the non-crypto side of the research universe is seven
instruments, which is too thin to conclude anything, and both paid feeds
(FMP full history, Alpha Vantage outputsize=full) are plan-gated.
"""
import hashlib, re, time, sys, os, io
import requests, pandas as pd

OUT = "/home/claude/qlab/data_wide"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def solve(c, d=4):
    t = "0" * d
    n = 0
    while True:
        if hashlib.sha256(f"{c}{n}".encode()).hexdigest().startswith(t):
            return n
        n += 1


def session():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for attempt in range(6):
        try:
            r = s.get("https://stooq.com/q/d/l/?s=spy.us&i=d", timeout=45)
        except Exception as e:
            time.sleep(2 + attempt); continue
        if "__verify" not in r.text:
            return s                                   # already clear
        m = re.search(r'const c="([^"]+)",d=(\d+)', r.text)
        if not m:
            time.sleep(2); continue
        c, d = m.group(1), int(m.group(2))
        n = solve(c, d)
        try:
            v = s.post("https://stooq.com/__verify",
                       data={"c": c, "n": n},
                       headers={"Content-Type": "application/x-www-form-urlencoded"},
                       timeout=45)
        except Exception:
            time.sleep(2); continue
        if v.ok:
            return s
        time.sleep(2)
    raise RuntimeError("could not clear the stooq challenge")


def fetch(s, sym, retries=4):
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    for a in range(retries):
        try:
            r = s.get(url, timeout=60)
        except Exception:
            time.sleep(1.5 + a); continue
        if "__verify" in r.text:
            m = re.search(r'const c="([^"]+)",d=(\d+)', r.text)
            if m:
                n = solve(m.group(1), int(m.group(2)))
                s.post("https://stooq.com/__verify", data={"c": m.group(1), "n": n},
                       timeout=45)
            continue
        txt = r.text.strip()
        if not txt.startswith("Date,"):
            return None
        df = pd.read_csv(io.StringIO(txt))
        df.columns = [x.lower() for x in df.columns]
        if "close" not in df or len(df) < 300:
            return None
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
        if "volume" not in df:
            df["volume"] = 0.0
        return df[["date", "open", "high", "low", "close", "volume"]]
    return None


if __name__ == "__main__":
    syms = [x.strip() for x in sys.argv[1:] if x.strip()]
    os.makedirs(OUT, exist_ok=True)
    s = session()
    print("challenge cleared", flush=True)
    ok = fail = 0
    for sym in syms:
        name = sym.split(".")[0].upper()
        dst = f"{OUT}/{name}.csv"
        if os.path.exists(dst):
            ok += 1; continue
        df = fetch(s, sym)
        if df is None or len(df) < 300:
            print(f"  MISS {sym}", flush=True); fail += 1; continue
        df.to_csv(dst, index=False)
        print(f"  {name:8s} {len(df):5d} bars {df.date.min().date()} -> {df.date.max().date()}",
              flush=True)
        ok += 1
        time.sleep(0.4)
    print(f"done: {ok} ok, {fail} missed")
