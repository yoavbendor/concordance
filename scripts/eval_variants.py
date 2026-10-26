"""Compare meaning-search variants on data/eval/pairs.jsonl:
  semantic      the current model
  lexical       word matching on consonant keys (idf-weighted), no model
  hybrid        semantic and lexical scores blended
  graph         hybrid, plus a boost from cross-references among the top hits
Metrics: recall@10 and MRR@10, for 4-word and 10-word queries.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from eval_retrieval import embed_queries  # noqa: E402
from build_tanakh import consonants  # noqa: E402
import lance  # noqa: E402

DATA = ROOT / "docs" / "data"


def metrics(ranks):
    ranks = np.asarray(ranks)
    return {"recall@10": round(float(np.mean(ranks <= 10)), 4),
            "mrr@10": round(float(np.mean(np.where(ranks <= 10, 1 / ranks, 0))), 4)}


def rank_of(scores, target):
    return int((scores > scores[target]).sum()) + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    args = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "data" / "eval" / "pairs.jsonl").read_text(encoding="utf-8").splitlines()]
    tanakh = json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]
    ids = [v["id"] for v in tanakh]
    index = {v: i for i, v in enumerate(ids)}
    t = lance.dataset(ROOT / "data" / "lance" / "verse_vectors.lance").to_table(columns=["id", "vector"])
    vectors = np.asarray(t.column("vector").to_pylist(), dtype=np.float32)
    assert t.column("id").to_pylist() == ids
    words = json.loads((DATA / "words.json").read_text(encoding="utf-8"))
    xrefs = json.loads((DATA / "xrefs.json").read_text(encoding="utf-8"))

    N = len(ids)
    idf = {k: math.log(N / len(v)) for k, v in words.items()}
    # verse-level neighbours: verses in short cross-reference spans (both directions)
    neigh = defaultdict(set)
    for f1, b1, t1, f2, b2, t2 in xrefs:
        a = [index.get(f"{b1} {c}:{v}") for c, v in _span(f1, t1)]
        b = [index.get(f"{b2} {c}:{v}") for c, v in _span(f2, t2)]
        a = [x for x in a if x is not None]
        b = [x for x in b if x is not None]
        if len(a) > 10 or len(b) > 10:
            continue
        for x in a:
            neigh[x].update(b)
        for y in b:
            neigh[y].update(a)

    qvecs = embed_queries([r["query"] for r in rows], Path(args.model_dir))
    # Pairs whose query shares no word with the target verse: the test of meaning, not vocabulary.
    verse_keys = defaultdict(set)
    for key, idx in words.items():
        for i in idx:
            verse_keys[i].add(key)
    results = defaultdict(list)          # (variant, subset, query length) -> ranks
    for qi, row in enumerate(rows):
        target = index[row["target"]]
        n = row["query_words"]
        keys = {consonants(w) for w in row["query"].split()}
        subsets = ["all"] + (["no shared word"] if not (keys & verse_keys[target]) else [])
        sem = vectors @ qvecs[qi]
        lex = np.zeros(N, dtype=np.float32)
        for key in keys:
            if key in words:
                lex[words[key]] += idf[key]
        if lex.max() > 0:
            lex = lex / lex.max()
        sem_z = (sem - sem.mean()) / (sem.std() + 1e-9)
        lex_z = (lex - lex.mean()) / (lex.std() + 1e-9)
        hybrid = sem_z + 0.5 * lex_z
        # graph: the best 30 hybrid hits lend their score to their cross-referenced neighbours
        top = np.argsort(-hybrid)[:30]
        graph = hybrid.copy()
        for v in top:
            for u in neigh.get(int(v), ()):
                graph[u] += 0.2 * hybrid[v]
        for name, scores in (("semantic", sem), ("lexical", lex), ("hybrid", hybrid), ("graph", graph)):
            r = rank_of(scores, target)
            for sub in subsets:
                results[(name, sub, n)].append(r)
    out = {}
    for (name, sub, n), ranks in sorted(results.items()):
        out.setdefault(f"{name} | {sub}", {})[f"{n} words (n={len(ranks)})"] = metrics(ranks)
    print(json.dumps(out, indent=2, ensure_ascii=False))


def _span(start, end):
    (c1, v1), (c2, v2) = start, end
    out = []
    for c in range(c1, c2 + 1):
        lo = v1 if c == c1 else 1
        hi = v2 if c == c2 else 200
        out.extend((c, v) for v in range(lo, hi + 1))
    return out


if __name__ == "__main__":
    main()
