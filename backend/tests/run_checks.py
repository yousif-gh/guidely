"""Manual validation script for the README Testing & Metrics table.

Run from backend/:  python tests/run_checks.py
Uses FastAPI's TestClient, so no server needs to be running.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

c = TestClient(main.app)

QUERIES = [
    ("How many days per week can I work remotely?", "remote-work-policy.txt"),
    ("What is the daily meal allowance when travelling?", "expense-policy.txt"),
    ("How do I reset my password?", "it-security-faq.txt"),
    ("What happens on my first day of onboarding?", "onboarding-guide.txt"),
    ("How long do customers have to return a product?", "product-returns-faq.txt"),
    ("Who declares a security incident and what are the severity levels?", "incident-response-guide.txt"),
    ("Can I install software on my work laptop?", "it-security-faq.txt"),
    ("What expenses need pre-approval?", "expense-policy.txt"),
    ("What equipment does the company provide for remote work?", "remote-work-policy.txt"),
    ("How are refunds issued for returned items?", "product-returns-faq.txt"),
    ("What should I do if I lose my laptop?", "it-security-faq.txt"),
    ("What training must new hires complete in the first week?", "onboarding-guide.txt"),
]


def main_run():
    print("=== /health ===")
    print(c.get("/health").json())

    print("\n=== reindex #1 ===")
    r = c.post("/documents/reindex").json()
    print(f"indexed={len(r['indexed'])} skipped={len(r['skipped_unchanged'])} "
          f"chunks={r['total_chunks']} new_emb={r['embeddings_new']} "
          f"cached={r['embeddings_cached']} ms={r['elapsed_ms']}")

    print("\n=== reindex #2 (unchanged files must be skipped) ===")
    r = c.post("/documents/reindex").json()
    print(f"indexed={r['indexed']} skipped={len(r['skipped_unchanged'])} new_emb={r['embeddings_new']}")

    print("\n=== Retrieval@3 ===")
    hits = cov = 0
    lat = []
    for q, expected in QUERIES:
        resp = c.post("/ask", json={"question": q})
        if resp.status_code != 200:
            print("FAIL", resp.status_code, q)
            continue
        b = resp.json()
        files = [s["file"] for s in b["sources"]]
        ok = expected in files
        hits += ok
        cov += bool(files)
        lat.append(b["latency_ms"])
        print(("PASS" if ok else "FAIL"), f"{b['latency_ms']:6.1f}ms",
              q[:50].ljust(50), "->", files[0] if files else "-")
    lat.sort()
    n = len(QUERIES)
    print(f"\nRetrieval@3: {hits}/{n} = {hits / n:.0%}   Reference coverage: {cov}/{n} = {cov / n:.0%}")
    print(f"Latency median {lat[n // 2]:.1f}ms  p95 {lat[max(0, int(n * 0.95) - 1)]:.1f}ms")

    print("\n=== cache: repeat 6 queries ===")
    h = m = 0
    for q, _ in QUERIES[:6]:
        b = c.post("/ask", json={"question": q}).json()
        h += b["cache"]["hits"]
        m += b["cache"]["misses"]
    print(f"hits={h} misses={m} -> {'100% cache hit rate' if m == 0 else 'MISSES DETECTED'}")

    print("\n=== error handling ===")
    r = c.post("/ask", json={"question": "   "})
    print("empty query   ->", r.status_code, r.json()["detail"][:70])
    r = c.post("/ask", json={"question": "zzqx microwave zorp asteroid"})
    print("no results    ->", r.status_code, r.json()["detail"][:70])
    r = c.post("/documents", files={"file": ("bad.txt", b"\x00\x01binary")})
    print("corrupt file  ->", r.status_code, r.json()["detail"][:70])
    r = c.post("/documents", files={"file": ("x.exe", b"hello")})
    print("bad extension ->", r.status_code, r.json()["detail"][:70])
    os.environ["EMBEDDINGS_PROVIDER"] = "openai"  # no key -> missing-key path
    r = c.post("/ask", json={"question": "test missing key"})
    print("missing key   ->", r.status_code, r.json()["detail"][:70])
    os.environ["EMBEDDINGS_PROVIDER"] = "local"

    print("\n=== upload / edit / delete roundtrip ===")
    body = (b"VPN Guide\n\nConnect to the corporate VPN using the GlobalConnect client. "
            b"Use your employee ID and OTP token to sign in. The VPN is mandatory on public Wi-Fi.")
    r = c.post("/documents", files={"file": ("vpn-guide.txt", body)}, data={"tags": "it,network"})
    print("upload ->", r.status_code, r.json()["document"]["id"], "chunks:", r.json()["chunks_created"])
    b2 = c.post("/ask", json={"question": "How do I connect to the VPN?"}).json()
    print("query new doc ->", [s["file"] for s in b2["sources"]][0])
    r = c.put("/documents/vpn-guide",
              json={"content": "VPN Guide (v2)\n\nUse the new WireGuard profile from the IT portal."})
    print("edit ->", r.status_code, "new_emb:", r.json()["embeddings_new"])
    r = c.delete("/documents/vpn-guide")
    print("delete ->", r.status_code, r.json())

    print("\n=== /metrics ===")
    print(json.dumps(c.get("/metrics").json(), indent=2))


if __name__ == "__main__":
    main_run()
