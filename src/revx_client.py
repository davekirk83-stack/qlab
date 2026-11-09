"""
Revolut X REST client (doc 194). Signing copied from Revolut's own client (github.com/revolut-engineering/revolut-x-api, api/src/auth/signer.ts):
  message = timestamp_ms + METHOD + "/api/1.0<path>" + query + body ; Ed25519 ; base64 ; headers X-Revx-API-Key / X-Revx-Timestamp / X-Revx-Signature.
Keys come ONLY from the environment (DK's GitHub secrets REVX_API_KEY / REVX_PRIVATE_KEY). Nothing here prints them.
`python src/revx_client.py check` = one read-only signed call (balances) to prove the keys work. No orders.
"""
import os, sys, json, time, base64, uuid, urllib.request, urllib.error, urllib.parse
from cryptography.hazmat.primitives.serialization import load_pem_private_key

BASE = "https://revx.revolut.com"


class RevX:
    def __init__(self):
        k, p = os.environ.get("REVX_API_KEY", "").strip(), os.environ.get("REVX_PRIVATE_KEY", "").strip()
        if not k: raise SystemExit("REVX_API_KEY secret is missing or empty")
        if not p: raise SystemExit("REVX_PRIVATE_KEY secret is missing or empty")
        if "BEGIN PUBLIC KEY" in p: raise SystemExit("REVX_PRIVATE_KEY holds the PUBLIC key — it needs the private one")
        if "PRIVATE KEY" not in p:
            raise SystemExit("REVX_PRIVATE_KEY doesn't look like a private key (no '-----BEGIN PRIVATE KEY-----' line) — "
                             "it may hold the API key instead")
        if "BEGIN" in k or len(k) < 20: raise SystemExit("REVX_API_KEY doesn't look like a Revolut X API key (it may hold one of the PEM keys)")
        self.key = k
        try: self.pk = load_pem_private_key(p.encode(), password=None)
        except Exception as e: raise SystemExit(f"REVX_PRIVATE_KEY could not be read as a PEM private key ({type(e).__name__})")

    def req(self, method, path, params=None, body=None):
        full = "/api/1.0" + path
        q = urllib.parse.urlencode(sorted((k, str(v)) for k, v in (params or {}).items() if v is not None))
        b = json.dumps(body, separators=(",", ":")) if body is not None else ""
        ts = str(int(time.time() * 1000))
        sig = base64.b64encode(self.pk.sign((ts + method.upper() + full + q + b).encode())).decode()
        h = {"X-Revx-API-Key": self.key, "X-Revx-Timestamp": ts, "X-Revx-Signature": sig, "Accept": "application/json", "User-Agent": "qlab-revx"}
        if b: h["Content-Type"] = "application/json"
        r = urllib.request.Request(BASE + full + ("?" + q if q else ""), data=b.encode() if b else None, headers=h, method=method.upper())
        for k in range(4):
            try:
                with urllib.request.urlopen(r, timeout=30) as resp:
                    t = resp.read().decode(); return json.loads(t) if t else {}
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:300]
                if e.code == 429 and k < 3: time.sleep(5 * (k + 1)); continue
                raise RuntimeError(f"HTTP {e.code} on {method} {path}: {msg}")

    def balances(self): return self.req("GET", "/balances")
    def pairs(self): return self.req("GET", "/configuration/pairs")
    def active_orders(self, symbols=None): return self.req("GET", "/orders/active", {"symbols": symbols})
    def cancel(self, oid): return self.req("DELETE", f"/orders/{oid}")
    def order(self, oid): return self.req("GET", f"/orders/{oid}")

    def place(self, symbol, side, base_size=None, quote_size=None, price=None, tif="gtc", post_only=False):
        if price is None:
            cfg = {"market": {"base_size": base_size} if base_size else {"quote_size": quote_size}}
        else:
            lim = {"base_size": base_size} if base_size else {"quote_size": quote_size}
            lim.update(price=str(price), time_in_force=tif)
            if post_only: lim["execution_instructions"] = ["post_only"]
            cfg = {"limit": lim}
        return self.req("POST", "/orders", body={"client_order_id": str(uuid.uuid4()), "symbol": symbol, "side": side, "order_configuration": cfg})


if __name__ == "__main__" and sys.argv[1:2] == ["check"]:
    rx = RevX()
    try:
        bal = rx.balances()
    except RuntimeError as e:
        s = str(e)
        hint = (" — the API key and private key don't match, or the key was pasted into the wrong secret" if "401" in s
                else " — the key has no permission for this (spot trade needs to be ticked)" if "403" in s else "")
        raise SystemExit(f"KEY CHECK FAILED: {s.split(':')[0]}{hint}")
    rows = bal if isinstance(bal, list) else bal.get("data", bal)
    nz = [f"{b.get('currency')} {b.get('total') or b.get('available')}" for b in rows if float(b.get("total") or b.get("available") or 0) > 0]
    print("KEY CHECK OK — Revolut X accepted the signed request.")
    print("Balances held:", ", ".join(nz) if nz else "none yet (account empty)")
    try:
        pr = rx.pairs(); syms = list(pr.keys()) if isinstance(pr, dict) else []
        gbp = sorted(s for s in syms if s.endswith("GBP")); usd = sorted(s for s in syms if s.endswith("USD"))
        print(f"Pairs: {len(syms)} total, {len(gbp)} quoted in GBP, {len(usd)} in USD")
        json.dump(pr, open(os.path.join(os.environ.get("QLAB_ROOT", "."), "runs", "revx_live", "pairs.json"), "w"), indent=1)
    except Exception as e: print("pairs:", e)
