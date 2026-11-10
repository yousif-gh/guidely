import json
import statistics
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"

# question, file that holds the answer, exact text proving the right passage
QUERIES = [
    ("How long does a refund take for a damaged item?", "policy.txt", "3 business days"),
    ("How many days do customers have to return an item?", "policy.txt", "within 30 days"),
    ("How much does express delivery cost?", "policy.txt", "costs 15 dollars"),
    ("Which countries does Larkfield ship to?", "policy.txt", "Canada and the United Kingdom"),
    ("When is a parcel treated as lost?", "policy.txt", "10 business days"),
    ("How many vacation days do I get?", "faq.txt", "25 vacation days"),
    ("When do I need a doctor's note?", "faq.txt", "longer than 3 working days"),
    ("When is payday?", "faq.txt", "last working day"),
    ("How much is the yearly learning budget?", "faq.txt", "1,000 dollars"),
    ("What is the maximum weight of a box?", "guide.txt", "23 kilograms"),
    ("When does the standard carrier collect parcels?", "guide.txt", "4 pm"),
    ("What is the minimum password length?", "it-security.txt", "14 characters"),
    ("How quickly must a lost laptop be reported?", "it-security.txt", "within 1 hour"),
    ("What time should I arrive on my first day?", "onboarding.txt", "9:30 am"),
    ("How long is the probation period?", "onboarding.txt", "6 months"),
]


def post(path: str, body: dict) -> tuple[int, dict | list]:
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def cache_counts() -> dict:
    with urllib.request.urlopen(BASE_URL + "/metrics", timeout=10) as response:
        return json.load(response)["embedding_cache"]


for question, _, _ in QUERIES:
    post("/search", {"question": question, "k": 3})

before = cache_counts()
retrieved = 0
referenced = 0
latencies = []

for question, source, phrase in QUERIES:
    _, results = post("/search", {"question": question, "k": 3})
    found = any(r["source"] == source and phrase in r["text"] for r in results)
    retrieved += found

    started = time.perf_counter()
    status, data = post("/ask", {"question": question})
    latencies.append((time.perf_counter() - started) * 1000)
    cited = status == 200 and any(s["source"] == source for s in data["sources"])
    referenced += cited

    answer = data["answer"] if status == 200 else data["detail"]
    print(f"\nQ: {question}\nA: {answer}\nretrieved={found} cited={cited} status={status}")

after = cache_counts()
hits = after["hits"] - before["hits"]
misses = after["misses"] - before["misses"]
total = len(QUERIES)
p95 = statistics.quantiles(latencies, n=20, method="inclusive")[-1]

print("\n--- RESULTS ---")
print(f"Retrieval@3: {retrieved}/{total} = {retrieved / total:.0%} (target 80%)")
print(f"Answer reference coverage: {referenced}/{total} = {referenced / total:.0%} (target 90%)")
print(f"Latency median: {statistics.median(latencies):.0f} ms (target under 3000)")
print(f"Latency p95: {p95:.0f} ms (target under 5000)")
print(f"Embedding cache on repeat: {hits} hits, {misses} misses (target 0 misses)")
print("Empty query status:", post("/ask", {"question": "   "})[0], "(target 422)")
print("No results status:", post("/ask", {"question": "What is the capital of France?"})[0], "(target 404)")
print("Not in docs status:", post("/ask", {"question": "What is the wifi password?"})[0], "(target 404)")
