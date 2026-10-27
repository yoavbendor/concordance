"""Verse-level commentary for the reading sheet: Rashi, Ramban, Ibn Ezra and Sforno.

Each commentary is linked to the verse it explains (its text is indexed by chapter and
verse, one list of comments per verse). Writes:
  data/lance/commentary.lance      one row per comment: verse_id, commentator, order, text;
                                   BTREE index on verse_id (fast lookup for one verse)
  docs/data/commentary/<Book>.json  per book, {verse id: [{c: commentator, t: text}]}, for the page
Standard library for the JSON; pyarrow and pylance for the Lance table.
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
OUT = ROOT / "data" / "lance"
BOOKS_JSON = "https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json"
COMMENTATORS = ["Rashi", "Ramban", "Ibn Ezra", "Sforno"]
TAG = re.compile(r"<[^>]+>")


def clean(text):
    return " ".join(TAG.sub(" ", text).split())


def fetch(url):
    return json.loads(urllib.request.urlopen(url, timeout=300).read())


def main():
    books = fetch(BOOKS_JSON)["books"]
    ids = {v["id"] for v in json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]}
    rows = []     # (verse_id, book, commentator, order, text)
    for name in COMMENTATORS:
        for b in books:
            if b.get("language") != "Hebrew" or b.get("versionTitle") != "merged":
                continue
            prefix = f"{name} on "
            if not b["title"].startswith(prefix):
                continue
            book = b["title"][len(prefix):]
            text = fetch(b["json_url"])["text"]
            for c, chapter in enumerate(text, 1):
                for v, comments in enumerate(chapter, 1):
                    if isinstance(comments, str):
                        comments = [comments]
                    vid = f"{book} {c}:{v}"
                    if vid not in ids:
                        continue
                    for order, comment in enumerate(comments):
                        t = clean(comment) if isinstance(comment, str) else ""
                        if t:
                            rows.append((vid, book, name, order, t))
    print("comments:", len(rows))

    # Per-book shards for the page.
    shard_dir = DATA / "commentary"
    shard_dir.mkdir(parents=True, exist_ok=True)
    for old in shard_dir.glob("*.json"):
        old.unlink()
    shards = {}
    for vid, book, name, order, t in rows:
        shards.setdefault(book, {}).setdefault(vid, []).append({"c": name, "t": t})
    for book, verses in shards.items():
        (shard_dir / f"{book}.json").write_text(json.dumps(verses, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("shards:", len(shards))

    import lance
    import pyarrow as pa
    table = pa.table({
        "verse_id": pa.array([r[0] for r in rows], pa.string()),
        "commentator": pa.array([r[2] for r in rows], pa.string()),
        "order": pa.array([r[3] for r in rows], pa.int32()),
        "text": pa.array([r[4] for r in rows], pa.string()),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "commentary.lance"
    ds = lance.write_dataset(table, path, mode="overwrite")
    ds.create_scalar_index("verse_id", index_type="BTREE", replace=True)
    print(f"commentary.lance: {ds.count_rows()} rows -> {path}")


if __name__ == "__main__":
    main()
