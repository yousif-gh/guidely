import tempfile
from pathlib import Path

from services.parsing import chunk_text, read_text

numbers = " ".join(str(n) for n in range(10))
assert chunk_text(numbers, chunk_words=4, overlap_words=1) == [
    "0 1 2 3",
    "3 4 5 6",
    "6 7 8 9",
]

with tempfile.TemporaryDirectory() as folder:
    bad = Path(folder) / "bad.text"
    bad.write_bytes(b"\xff\xfe broken")
    try:
        read_text(bad)
    except ValueError as error:
        print("rejected:", error)
    else:
        raise AssertionError("corrupted file was accepted")
    
docs = sorted(Path("data/sample-docs").glob("*.txt"))
assert len(docs) == 5
for doc in docs:
    print(doc.name, len(chunk_text(read_text(doc))))