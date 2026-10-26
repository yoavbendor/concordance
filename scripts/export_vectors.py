"""Export the verse vectors for the browser: docs/data/verse_vectors.f16.

Raw little-endian float16, row-major, 256 values per verse, in the order of tanakh.json.
The page reads it into Float32Array and dots it with the query vector.
"""
import json
from pathlib import Path

import lance
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"


def main():
    verses = json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]
    table = lance.dataset(ROOT / "data" / "lance" / "verse_vectors.lance").to_table(columns=["id", "vector"])
    ids = table.column("id").to_pylist()
    assert ids == [v["id"] for v in verses], "vector rows must follow tanakh.json order"
    vectors = np.asarray(table.column("vector").to_pylist(), dtype=np.float32).astype("<f2")
    (DATA / "verse_vectors.f16").write_bytes(vectors.tobytes())
    print(f"verse_vectors.f16: {vectors.shape[0]} x {vectors.shape[1]} float16 "
          f"({vectors.nbytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
