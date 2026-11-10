import os
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient
from groq import APITimeoutError

from main import app
from services import llm
from services.vector_store import build_index


class FakeGroq:
    reply = ""
    error = None

    def __init__(self, **kwargs):
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        if FakeGroq.error:
            raise FakeGroq.error
        message = SimpleNamespace(content=FakeGroq.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


llm.Groq = FakeGroq
os.environ["GROQ_API_KEY"] = "fake-key-for-test"
build_index()
client = TestClient(app)
refund = {"question": "How long does a refund take for a damaged item?"}

FakeGroq.reply = "Damaged item refunds take 3 business days [1]."
response = client.post("/ask", json=refund)
assert response.status_code == 200
assert [source["source"] for source in response.json()["sources"]] == ["policy.txt"]
print("cited answer: 200")

FakeGroq.reply = "Damaged item refunds take 3 business days【1†L2-L4】."
response = client.post("/ask", json=refund)
assert response.json()["answer"].endswith("days[1].")
assert [source["source"] for source in response.json()["sources"]] == ["policy.txt"]
print("full-width citation: 200")

FakeGroq.reply = "NOT_FOUND"
assert client.post("/ask", json=refund).status_code == 404
print("model found no answer: 404")

off_topic = client.post("/ask", json={"question": "What is the capital of France?"})
assert off_topic.status_code == 404
print("off-topic question: 404")

assert client.post("/ask", json={"question": "   "}).status_code == 422
print("empty question: 422")

FakeGroq.error = APITimeoutError(request=httpx.Request("POST", "http://test"))
assert client.post("/ask", json=refund).status_code == 504
print("model timeout: 504")
FakeGroq.error = None

del os.environ["GROQ_API_KEY"]
missing_key = client.post("/ask", json=refund)
assert missing_key.status_code == 503
print("missing key:", missing_key.status_code, missing_key.json()["detail"])
