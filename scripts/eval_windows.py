"""Hierarchical meaning search on data/eval/pairs_en.jsonl: does a window of verses help?

For each query, four rankings of verses are compared (recall@10, recall@50, MRR@10):
  verse      the verse vectors alone (the current search)
  window     each level alone: a verse ranks by the best window containing it
  fused      the verse score plus w times the best containing window's score

    python3 scripts/eval_windows.py --model-dir <dir with model_q4.onnx and tokenizer.json>
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

LEVELS = ["5", "11", "chapter"]


def metrics(ranks):
    r = np.asarray(ranks)
    return {"recall@10": round(float(np.mean(r <= 10)), 4),
            "recall@50": round(float(np.mean(r <= 50)), 4),
            "mrr@10": round(float(np.mean(np.where(r <= 10, 1 / r, 0))), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    args = ap.parse_args()
    rows = [json.loads(l) for l in (ROOT / "data" / "eval" / "pairs_en.jsonl").read_text(encoding="utf-8").splitlines()]
    t = lance.dataset(ROOT / "data" / "lance" / "english_vectors.lance").to_table(columns=["id", "vector"])
    ids = t.column("id").to_pylist()
    index = {v: i for i, v in enumerate(ids)}
    V = np.asarray(t.column("vector").to_pylist(), dtype=np.float32)
    q = embed_queries([r["query"] for r in rows], Path(args.model_dir))
    sim_v = q @ V.T                                   # queries x verses

    # For each level: the window's similarity, and which verses it covers.
    levels = {}
    for lv in LEVELS:
        w = lance.dataset(ROOT / "data" / "lance" / f"windows_{lv}.lance").to_table(
            columns=["book", "c", "v_start", "v_end", "vector"])
        W = np.asarray(w.column("vector").to_pylist(), dtype=np.float32)
        books = w.column("book").to_pylist()
        cs = w.column("c").to_pylist()
        vs = w.column("v_start").to_pylist()
        ve = w.column("v_end").to_pylist()
        member = []                                   # verse index lists per window
        for b, c, s, e in zip(books, cs, vs, ve):
            member.append([index[f"{b} {c}:{v}"] for v in range(s, e + 1)])
        levels[lv] = (q @ W.T, member)

    def window_scores(sim_w, member, n_verses):
        """Per verse: the best window score among the windows that contain it."""
        best = np.full((sim_w.shape[0], n_verses), -np.inf, dtype=np.float32)
        for k, mem in enumerate(member):
            best[:, mem] = np.maximum(best[:, mem], sim_w[:, [k]])
        return best

    results = {}
    for n in (4, 10):
        sel = [i for i, r in enumerate(rows) if r["query_words"] == n]
        targets = np.array([index[rows[i]["target"]] for i in sel])
        sv = sim_v[sel]

        def ranks_of(scores):
            tgt = scores[np.arange(len(sel)), targets]
            return (scores > tgt[:, None]).sum(axis=1) + 1

        out = {"verse": metrics(ranks_of(sv))}
        win = {}
        for lv in LEVELS:
            sim_w, member = levels[lv]
            best = window_scores(sim_w[sel], member, len(ids))
            best = np.where(np.isfinite(best), best, -1.0)
            win[lv] = best
            out[f"window {lv}"] = metrics(ranks_of(best))
        for lv in ("5", "11"):
            for w_ in (0.5, 1.0):
                fused = sv + w_ * win[lv]
                out[f"fused {lv} w={w_}"] = metrics(ranks_of(fused))
        results[f"{n} words (n={len(sel)})"] = out
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
