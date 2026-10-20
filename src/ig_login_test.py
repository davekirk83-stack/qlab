"""One-off: log in to the IG DEMO API with the repo secrets and write runs/ig_login_test.txt.
DEMO ONLY (CAP-021 as amended 20 Oct 2026: demo-account credentials only). Prints and records no secret."""
import os, json, datetime, requests
BASE = "https://demo-api.ig.com/gateway/deal"
out = "runs/ig_login_test.txt"; os.makedirs("runs", exist_ok=True)
now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
try:
    u, p, k = (os.environ[x].strip() for x in ("IG_USERNAME","IG_PASSWORD","IG_API_KEY"))
    if not (u and p and k): raise RuntimeError("one or more secrets are empty")
    h = {"X-IG-API-KEY": k, "Content-Type": "application/json; charset=UTF-8", "Accept": "application/json; charset=UTF-8", "Version": "2"}
    r = requests.post(f"{BASE}/session", headers=h, data=json.dumps({"identifier": u, "password": p}), timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"login HTTP {r.status_code}: {r.json().get('errorCode', r.text[:80])} (key length {len(k)}, hex={all(c in '0123456789abcdef' for c in k)}, user length {len(u)})")
    h2 = {**h, "CST": r.headers["CST"], "X-SECURITY-TOKEN": r.headers["X-SECURITY-TOKEN"], "Version": "1"}
    a = requests.get(f"{BASE}/accounts", headers=h2, timeout=30).json().get("accounts", [])
    kinds = sorted({x.get("accountType", "?") for x in a})
    m = requests.get(f"{BASE}/markets?searchTerm=US%20Tech%20100", headers=h2, timeout=30).json().get("markets", [])
    epics = [x["epic"] for x in m if "Tech 100" in x.get("instrumentName", "")][:6]
    line = f"ok {now} — demo login good; {len(a)} demo account(s) {kinds}; US Tech 100 epics: {epics}"
except Exception as e:
    line = f"FAIL {now} — {e}"
open(out, "w").write(line + "\n"); print(line)
# rerun 10:20
# rerun 10:31
# rerun 10:32:14
# rerun 10:34:10
