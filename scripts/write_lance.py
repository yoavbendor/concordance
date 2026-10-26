"""Convert the Tanakh JSON built by build_tanakh.py into Lance datasets.

Reads docs/data/tanakh.json, words.json and xrefs.json and writes Lance datasets
under data/lance/ (not committed; rebuild locally). Needs pylance and pyarrow:

    pip install pylance pyarrow
    python3 scripts/write_lance.py
"""
import json
import sys
from pathlib import Path

import lance
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
OUT = ROOT / "data" / "lance"
SECTION = {"Torah": 0, "Prophets": 1, "Writings": 2}


def write_verses(tanakh):
    book_order = {b: i for i, b in enumerate(tanakh["books"])}
    rows = {"id": [], "book": [], "book_order": [], "c": [], "v": [], "he": [], "search": []}
    from build_tanakh import consonants  # same key as the page uses
    for verse in tanakh["verses"]:
        rows["id"].append(verse["id"])
        rows["book"].append(verse["book"])
        rows["book_order"].append(book_order[verse["book"]])
        rows["c"].append(verse["c"])
        rows["v"].append(verse["v"])
        rows["he"].append(verse["he"])
        rows["search"].append(" ".join(filter(None, (consonants(t) for t in verse["he"].split()))))
    table = pa.table({
        "id": pa.array(rows["id"], pa.string()),
        "book": pa.array(rows["book"], pa.string()),
        "book_order": pa.array(rows["book_order"], pa.int32()),
        "c": pa.array(rows["c"], pa.int32()),
        "v": pa.array(rows["v"], pa.int32()),
        "he": pa.array(rows["he"], pa.string()),
        "search": pa.array(rows["search"], pa.string()),
    })
    return table


def write_words(words):
    keys = list(words.keys())
    return pa.table({
        "key": pa.array(keys, pa.string()),
        "verse_ids": pa.array([words[k] for k in keys], pa.list_(pa.int32())),
    })


def write_xrefs(xrefs):
    cols = {n: [] for n in (
        "from_book", "from_c", "from_v", "from_end_c", "from_end_v",
        "to_book", "to_c", "to_v", "to_end_c", "to_end_v")}
    for (f1, b1, t1, f2, b2, t2) in xrefs:
        for name, val in zip(cols, (b1, f1[0], f1[1], t1[0], t1[1], b2, f2[0], f2[1], t2[0], t2[1])):
            cols[name].append(val)
    types = {n: pa.string() if n.endswith("book") else pa.int32() for n in cols}
    return pa.table({n: pa.array(cols[n], types[n]) for n in cols})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tanakh = json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))
    words = json.loads((DATA / "words.json").read_text(encoding="utf-8"))
    xrefs = json.loads((DATA / "xrefs.json").read_text(encoding="utf-8"))

    tables = {
        "verses": write_verses(tanakh),
        "words": write_words(words),
        "xrefs": write_xrefs(xrefs),
    }
    for name, table in tables.items():
        path = OUT / f"{name}.lance"
        ds = lance.write_dataset(table, path, mode="overwrite")
        print(f"{name}: {ds.count_rows()} rows -> {path}")

    verses = lance.dataset(OUT / "verses.lance")
    for col in ("book", "c", "v"):
        verses.create_scalar_index(col, index_type="BTREE", replace=True)
    words_ds = lance.dataset(OUT / "words.lance")
    words_ds.create_scalar_index("key", index_type="BTREE", replace=True)
    xrefs_ds = lance.dataset(OUT / "xrefs.lance")
    for col in ("from_book", "to_book"):
        xrefs_ds.create_scalar_index(col, index_type="BTREE", replace=True)
    print("indexes built")


if __name__ == "__main__":
    main()
