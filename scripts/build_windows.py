"""Hierarchical meaning search: English embeddings of windows of consecutive verses.

Each chapter is cut into windows of 5 verses, of 11 verses, and into the whole chapter; a
window is embedded from its joined English translation, with the document prompt. Windows
do not overlap inside a level, and never cross a chapter. Writes one Lance table per
level: data/lance/windows_<level>.lance (id, book, c, v_start, v_end, vector[256]).
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
LEVELS = {"5": 5, "11": 11, "chapter": None}


def windows(verses, english, size):
    """Consecutive windows inside each chapter: (book, c, v_start, v_end, text)."""
    by_chapter = {}
    for v in verses:
        by_chapter.setdefault((v["book"], v["c"]), []).append(v)
    out = []
    for (book, c), vs in by_chapter.items():
        vs.sort(key=lambda v: v["v"])
        step = size or len(vs)
        for start in range(0, len(vs), step):
            group = vs[start:start + step]
            text = " ".join(" ".join(english[g["id"]].split()) for g in group)
            out.append((book, c, group[0]["v"], group[-1]["v"], text))
    return out


def main():
    verses = json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]
    english = json.loads((DATA / "english.json").read_text(encoding="utf-8"))
    for level, size in LEVELS.items():
        rows = windows(verses, english, size)
        # Chapters can be long; the embedding context is widened for them.
        ctx = 8192 if size is None else 1024
        vectors = []
        for start in range(0, len(rows), 200):
            chunk = [DOCUMENT_PREFIX + r[4] for r in rows[start:start + 200]]
            vectors.append(truncate(embed(chunk, ctx=ctx)))
            print(f"{level}: {min(start + 200, len(rows))}/{len(rows)}", file=sys.stderr, flush=True)
        vectors = np.vstack(vectors)
        table = pa.table({
            "id": pa.array([f"{r[0]} {r[1]}:{r[2]}-{r[3]}" for r in rows], pa.string()),
            "book": pa.array([r[0] for r in rows], pa.string()),
            "c": pa.array([r[1] for r in rows], pa.int32()),
            "v_start": pa.array([r[2] for r in rows], pa.int32()),
            "v_end": pa.array([r[3] for r in rows], pa.int32()),
            "vector": pa.FixedSizeListArray.from_arrays(pa.array(vectors.ravel(), pa.float32()), DIM),
        })
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"windows_{level}.lance"
        ds = lance.write_dataset(table, path, mode="overwrite")
        print(f"windows_{level}: {ds.count_rows()} rows -> {path}")


if __name__ == "__main__":
    main()
