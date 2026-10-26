"""Embed every Tanakh verse with EmbeddingGemma 2 (GGUF) and write a Lance vector table.

Needs a llama.cpp build with the llama-embedding tool that knows the gemma-embedding2
architecture (the llama.cpp in LLAMA_CPP_BIN below, built from current main), and the
GGUF file from Ollama's registry (embeddinggemma-2, text model blob).

The model gives 768 dimensions. Matryoshka truncation to 256 keeps most of the quality
at a third of the size; the vectors are truncated and renormalized here.

Writes data/lance/verse_vectors.lance (id, vector[256]) with an IVF_PQ index.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import lance
import numpy as np
import pyarrow as pa

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
OUT = ROOT / "data" / "lance"
LLAMA_CPP_BIN = Path(os.environ.get("LLAMA_EMBEDDING", "/home/user/models/llama.cpp/build/bin/llama-embedding"))
GGUF = Path(os.environ.get("EMBEDDINGGEMMA_GGUF", "/home/user/models/embeddinggemma-2/model.gguf"))
DIM = 256
# EmbeddingGemma prompts (from the model card and the cookbook): documents and queries differ.
DOCUMENT_PREFIX = "title: none | text: "
QUERY_PREFIX = "task: search result | query: "
CHUNK = 2000
SEP = "||"

LETTERS_ONLY = re.compile(r"[^א-ת ]+")
MARKS = re.compile(r"[֑-ׇ]")


def query(text):
    """Query text in the form the model was trained on."""
    return QUERY_PREFIX + plain(text)


def plain(he):
    """Hebrew letters and spaces only: the form the model reads for meaning."""
    return " ".join(LETTERS_ONLY.sub(" ", MARKS.sub("", he)).split())


def embed(texts):
    """Return an (n, 768) float32 array, one row per text, in order."""
    assert not any(SEP in t for t in texts)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write(SEP.join(texts))
        path = f.name
    try:
        out = subprocess.run(
            [str(LLAMA_CPP_BIN), "-m", str(GGUF), "-f", path, "--embd-separator", SEP,
             "-c", "512", "--embd-output-format", "json"],
            capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(path)
    rows = sorted(json.loads(out)["data"], key=lambda d: d["index"])
    if len(rows) != len(texts):
        raise RuntimeError(f"expected {len(texts)} embeddings, got {len(rows)}")
    return np.asarray([r["embedding"] for r in rows], dtype=np.float32)


def truncate(vectors):
    """Matryoshka truncation: keep the first DIM dimensions, then renormalize."""
    v = vectors[:, :DIM]
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def main():
    verses = json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]
    ids = [v["id"] for v in verses]
    texts = [DOCUMENT_PREFIX + plain(v["he"]) for v in verses]
    chunks = []
    for start in range(0, len(texts), CHUNK):
        chunk = embed(texts[start:start + CHUNK])
        chunks.append(truncate(chunk))
        print(f"embedded {min(start + CHUNK, len(texts))}/{len(texts)}", file=sys.stderr, flush=True)
    vectors = np.vstack(chunks)

    table = pa.table({
        "id": pa.array(ids, pa.string()),
        "vector": pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel(), pa.float32()), DIM),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "verse_vectors.lance"
    ds = lance.write_dataset(table, path, mode="overwrite")
    ds.create_index("vector", index_type="IVF_PQ", num_partitions=128, num_sub_vectors=32, replace=True)
    print(f"verse_vectors: {ds.count_rows()} rows, dim {DIM}, IVF_PQ -> {path}")


if __name__ == "__main__":
    main()
