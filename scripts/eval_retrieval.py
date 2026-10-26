"""Score meaning search on data/eval/pairs.jsonl: recall@k and MRR for each query length.

Queries are embedded with the same ONNX text model the page runs (CPU, q4), with the query
prompt and the same 256-dimension truncation; verse vectors are read from the Lance table.
Needs the model files in --model-dir (model_q4.onnx, model_q4.onnx_data, tokenizer.json).

    python3 scripts/eval_retrieval.py --model-dir /home/user/models/work
"""
import argparse
import json
import sys
from pathlib import Path

import lance
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
QUERY_PREFIX = "task: search result | query: "
DIM = 256


def embed_queries(texts, model_dir):
    tok = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    sess = ort.InferenceSession(str(model_dir / "model_q4.onnx"), providers=["CPUExecutionProvider"])
    empty = np.zeros((0, 512), dtype=np.float32)
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, text in enumerate(texts):
        enc = tok.encode(QUERY_PREFIX + text)
        ids = np.array([enc.ids], dtype=np.int64)
        mask = np.array([enc.attention_mask], dtype=np.int64)
        emb = sess.run(None, {"input_ids": ids, "attention_mask": mask,
                              "image_features": empty, "video_features": empty,
                              "audio_features": empty})[1][0][:DIM]
        out[i] = emb / np.linalg.norm(emb)
    return out


def score(rows, qvecs, ids, vectors, k=10):
    sims = qvecs @ vectors.T                       # cosine: both sides are unit length
    rank_of = []
    for i, row in enumerate(rows):
        target = ids.index(row["target"])
        order = np.argsort(-sims[i])
        rank = int(np.where(order == target)[0][0]) + 1
        rank_of.append(rank)
    ranks = np.array(rank_of)
    return {"recall@10": float(np.mean(ranks <= 10)), "mrr@10": float(np.mean(np.where(ranks <= 10, 1 / ranks, 0)))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    args = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "data" / "eval" / "pairs.jsonl").read_text(encoding="utf-8").splitlines()]
    ds = lance.dataset(ROOT / "data" / "lance" / "verse_vectors.lance")
    t = ds.to_table(columns=["id", "vector"])
    ids = t.column("id").to_pylist()
    vectors = np.asarray(t.column("vector").to_pylist(), dtype=np.float32)

    qvecs = embed_queries([r["query"] for r in rows], Path(args.model_dir))
    results = {}
    for n in (4, 10):
        sel = [i for i, r in enumerate(rows) if r["query_words"] == n]
        results[f"{n} words"] = score([rows[i] for i in sel], qvecs[sel], ids, vectors)
        results[f"{n} words"]["queries"] = len(sel)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
