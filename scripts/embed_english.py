"""Embed the English verses (docs/data/english.json) with EmbeddingGemma 2, as the page
searches them: documents with the document prompt, truncated to 256 dimensions.

Writes docs/data/english_vectors.f16 (the page reads it, in tanakh.json order) and
data/lance/english_vectors.lance (id, vector) with an IVF_PQ index.
"""
import json
import sys
from pathlib import Path

import lance
import numpy as np
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embed_verses import DIM, DOCUMENT_PREFIX, embed, truncate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
OUT = ROOT / "data" / "lance"
CHUNK = 2000


def main():
    ids = [v["id"] for v in json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]]
    english = json.loads((DATA / "english.json").read_text(encoding="utf-8"))
    texts = [DOCUMENT_PREFIX + " ".join(english[i].split()) for i in ids]
    chunks = []
    for start in range(0, len(texts), CHUNK):
        chunks.append(truncate(embed(texts[start:start + CHUNK])))
        print(f"embedded {min(start + CHUNK, len(texts))}/{len(texts)}", file=sys.stderr, flush=True)
    vectors = np.vstack(chunks)

    (DATA / "english_vectors.f16").write_bytes(vectors.astype("<f2").tobytes())
    table = pa.table({
        "id": pa.array(ids, pa.string()),
        "vector": pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel(), pa.float32()), DIM),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "english_vectors.lance"
    ds = lance.write_dataset(table, path, mode="overwrite")
    ds.create_index("vector", index_type="IVF_PQ", num_partitions=128, num_sub_vectors=32, replace=True)
    print(f"english_vectors: {ds.count_rows()} rows -> {path}")


if __name__ == "__main__":
    main()
