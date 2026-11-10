import os

from tests.check_answers import FakeGroq, client, refund

os.environ["GROQ_API_KEY"] = "fake-key-for-test"
FakeGroq.reply = "Damaged item refunds take 3 business days [1]."

before = client.get("/metrics").json()
for _ in range(5):
    assert client.post("/ask", json=refund).status_code == 200
after = client.get("/metrics").json()

assert after["documents"] == 5
assert after["chunks"] == 6
assert after["queries_served"] == before["queries_served"] + 5
assert after["embedding_cache"]["hits"] == before["embedding_cache"]["hits"] + 5
assert after["embedding_cache"]["misses"] == before["embedding_cache"]["misses"]
assert after["latency_ms"]["p95"] >= after["latency_ms"]["median"] > 0
assert after["failures"] == {"404": 2, "422": 1, "503": 1, "504": 1}

print("repeated questions re-embedded: 0")
print("failures:", after["failures"])
print("latency_ms:", after["latency_ms"])
