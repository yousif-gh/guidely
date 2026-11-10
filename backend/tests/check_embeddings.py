import tempfile
from pathlib import Path

from services.embeddings import embed_texts
from services.parsing import chunk_text, read_text

docs = sorted(Path("data/sample-docs").glob("*.txt"))
chunks = [chunk for doc in docs for chunk in chunk_text(read_text(doc))]

with tempfile.TemporaryDirectory() as folder:
    cache = Path(folder) / "cache.json"
    first, first_hits = embed_texts(chunks, cache)
    second, second_hits = embed_texts(chunks, cache)
    _, changed_hits = embed_texts([chunks[0] + " changed"], cache)

assert first_hits == 0
assert second_hits == len(chunks)
assert first == second
assert changed_hits == 0
assert len(first[0]) == 384
print(f"chunks: {len(chunks)}")
print(f"first run cache hits: {first_hits}")
print(f"second run cache hits: {second_hits}")
