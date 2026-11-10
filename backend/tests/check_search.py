from services.vector_store import build_index, search

print(build_index())

cases = {
    "How long does a refund take for a damaged item?": "policy.txt",
    "How many vacation days do I get?": "faq.txt",
    "What is the minimum password length?": "it-security.txt",
    "How heavy can a box be?": "guide.txt",
    "What time should I arrive on my first day?": "onboarding.txt",
}

for question, expected in cases.items():
    results = search(question)
    print(f"\n{question}")
    for result in results:
        print(f"  {result['score']:.3f}  {result['source']}")
    assert results[0]["source"] == expected, f"expected {expected}"

assert "3 business days" in search("How long does a refund take for a damaged item?")[0]["text"]
