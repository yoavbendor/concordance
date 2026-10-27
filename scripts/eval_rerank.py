"""Test a reranker on the English meaning search: the first stage's top candidates are
rescored by a cross-encoder (query and verse read together). Compares recall@10 and MRR@10
with and without the rerank, on data/eval/pairs_en.jsonl.

    python3 scripts/eval_rerank.py --model-dir <dir with the reranker's model_int8.onnx and tokenizer.json>
"""
import argparse
import json
import sys
import time
from pathlib import Path

import lance
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from eval_retrieval import embed_queries  # noqa: E402

TOP = 50  # candidates rescored per query


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--rerank-dir", required=True)
    ap.add_argument("--queries", type=int, default=0, help="use only the first N queries of each length (0 = all)")
    ap.add_argument("--top", type=int, default=TOP, help="candidates rescored per query")
    args = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "data" / "eval" / "pairs_en.jsonl").read_text(encoding="utf-8").splitlines()]
    if args.queries:
        keep = {n: 0 for n in (4, 10)}
        sub = []
        for r in rows:
            if keep[r["query_words"]] < args.queries:
                keep[r["query_words"]] += 1
                sub.append(r)
        rows = sub
    t = lance.dataset(ROOT / "data" / "lance" / "english_vectors.lance").to_table(columns=["id", "vector"])
    ids = t.column("id").to_pylist()
    index = {v: i for i, v in enumerate(ids)}
    vectors = np.asarray(t.column("vector").to_pylist(), dtype=np.float32)
    english = json.loads((ROOT / "docs" / "data" / "english.json").read_text(encoding="utf-8"))

    qvecs = embed_queries([r["query"] for r in rows], Path(args.model_dir))
    sims = qvecs @ vectors.T

    rdir = Path(args.rerank_dir)
    tok = Tokenizer.from_file(str(rdir / "tokenizer.json"))
    tok.enable_truncation(max_length=512)
    tok.enable_padding(pad_id=0)
    sess = ort.InferenceSession(str(rdir / "model_int8.onnx"), providers=["CPUExecutionProvider"])

    top_n = args.top
    base = {4: [], 10: []}
    rer = {4: [], 10: []}
    t0 = time.time()
    for qi, r in enumerate(rows):
        target = index[r["target"]]
        top = np.argsort(-sims[qi])[:top_n]
        pos = np.where(top == target)[0]
        base[r["query_words"]].append(int(pos[0]) + 1 if len(pos) else 10**6)
        pairs = [(r["query"], english[ids[j]]) for j in top]
        enc = tok.encode_batch(pairs)
        logits = sess.run(None, {
            "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
        })[0].reshape(-1)
        order = top[np.argsort(-logits)]
        pos = np.where(order == target)[0]
        rer[r["query_words"]].append(int(pos[0]) + 1 if len(pos) else 10**6)
    print(f"reranked {len(rows)} queries in {time.time() - t0:.0f}s", file=sys.stderr)

    out = {}
    for n in (4, 10):
        for name, src in (("first stage", base), ("reranked", rer)):
            ranks = np.array(src[n])
            out.setdefault(f"{n} words", {})[name] = {
                "recall@10": round(float(np.mean(ranks <= 10)), 4),
                "mrr@10": round(float(np.mean(np.where(ranks <= 10, 1 / ranks, 0))), 4),
                "queries": len(ranks),
            }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
