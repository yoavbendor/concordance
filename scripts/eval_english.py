"""Score the English meaning search on data/eval/pairs_en.jsonl: recall@10, recall@50, MRR@10.
Queries are embedded with the page's ONNX text model; verses with the English vectors.
The gap between recall@10 and recall@50 is what a reranker could recover.

    python3 scripts/eval_english.py --model-dir <dir with model_q4.onnx and tokenizer.json>
"""
import argparse
import json
import sys
from pathlib import Path

import lance
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from eval_retrieval import embed_queries  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--pairs", default=str(ROOT / "data" / "eval" / "pairs_en.jsonl"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in Path(args.pairs).read_text(encoding="utf-8").splitlines()]
    t = lance.dataset(ROOT / "data" / "lance" / "english_vectors.lance").to_table(columns=["id", "vector"])
    ids = t.column("id").to_pylist()
    index = {v: i for i, v in enumerate(ids)}
    vectors = np.asarray(t.column("vector").to_pylist(), dtype=np.float32)
    q = embed_queries([r["query"] for r in rows], Path(args.model_dir))
    sims = q @ vectors.T
    results = {}
    for n in (4, 10):
        sel = [i for i, r in enumerate(rows) if r["query_words"] == n]
        ranks = []
        for i in sel:
            target = index[rows[i]["target"]]
            ranks.append(int((sims[i] > sims[i][target]).sum()) + 1)
        ranks = np.array(ranks)
        results[f"{n} words"] = {
            "queries": len(sel),
            "recall@10": round(float(np.mean(ranks <= 10)), 4),
            "recall@50": round(float(np.mean(ranks <= 50)), 4),
            "mrr@10": round(float(np.mean(np.where(ranks <= 10, 1 / ranks, 0))), 4),
        }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
