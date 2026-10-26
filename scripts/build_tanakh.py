"""Build the browser data for the Hebrew Tanakh (Torah, Prophets, Writings) from the Sefaria export.

Writes docs/data/tanakh.json (verses), docs/data/words.json (word -> verse ids)
and docs/data/xrefs.json (cross-reference span pairs between Tanakh passages).
Standard library only. Source: https://github.com/Sefaria/Sefaria-Export
"""
import csv
import html
import io
import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

EXPORT = "https://storage.googleapis.com/sefaria-export"
BOOKS_JSON = "https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json"
LINK_FILES = 13
OUT = Path(__file__).resolve().parent.parent / "docs" / "data"
SECTIONS = {"Torah", "Prophets", "Writings"}

NIKUD_AND_MARKS = re.compile(r"[֑-ׇ]")  # cantillation, points, meteg
TAGS = re.compile(r"<[^>]+>")
FINAL_TO_BASE = str.maketrans("ךםןףץ", "כמנפצ")


def get(url):
    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


def consonants(word):
    """Search key: no points or marks, final letters folded to base form."""
    word = unicodedata.normalize("NFC", word)
    word = NIKUD_AND_MARKS.sub("", word)
    return re.sub(r"[^א-ת]", "", word).translate(FINAL_TO_BASE)


def flatten(verse):
    if isinstance(verse, list):
        return " ".join(flatten(v) for v in verse)
    # Formatting tags (<big>, <b>) wrap parts of a word, so they join; a break (&thinsp;, <br>)
    # separates words. The maqaf joins two words and becomes a space.
    text = TAGS.sub(lambda m: " " if m.group(0).lower().startswith("<br") else "", verse)
    text = html.unescape(text).replace("\u00a0", " ").replace("\u2009", " ").replace("\u05BE", " ")
    return " ".join(text.split())


def load_tanakh_books():
    books = json.loads(get(BOOKS_JSON))["books"]
    tanakh = [
        b for b in books
        if b.get("language") == "Hebrew"
        and b.get("versionTitle") == "merged"
        and b.get("categories", [None, None])[:1] == ["Tanakh"]
        and len(b.get("categories", [])) > 1
        and b["categories"][1] in SECTIONS
    ]
    return sorted(tanakh, key=lambda b: b["title"])


def build_verses(tanakh_books):
    verses, names = [], {}
    for book in tanakh_books:
        data = json.loads(get(book["json_url"]))
        names[book["title"]] = data.get("heTitle", "")
        for c, chapter in enumerate(data["text"], start=1):
            for v, text in enumerate(chapter, start=1):
                he = flatten(text)
                if not he:
                    continue
                verses.append({
                    "id": f"{book['title']} {c}:{v}",
                    "book": book["title"],
                    "c": c,
                    "v": v,
                    "he": he,
                })
    return verses, names


REF = re.compile(r"^(.+?) (\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")


def parse_span(ref, books):
    """'Exodus 1:1-6:1' -> (book, (c1, v1), (c2, v2)). None if not a verse span."""
    m = REF.match(ref.strip())
    if not m or m.group(1) not in books:
        return None
    book, c1, v1, c2, v2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
    if c2 is not None:  # 'Book c:v-c:w' ends in another chapter
        end = (int(c2), int(v2))
    elif v2 is not None:  # 'Book c:v-w' ends in the same chapter
        end = (c1, int(v2))
    else:  # 'Book c:v' is a single verse
        end = (c1, v1)
    return book, (c1, v1), end


def build_xrefs(books):
    """Stream the link CSVs and keep rows where both ends are Tanakh spans."""
    edges = []
    for n in range(LINK_FILES):
        url = f"{EXPORT}/links/links{n}.csv"
        with urllib.request.urlopen(url, timeout=600) as r:
            reader = csv.DictReader(io.TextIOWrapper(r, encoding="utf-8", newline=""))
            for row in reader:
                if row["Category 1"] != "Tanakh" or row["Category 2"] != "Tanakh":
                    continue
                a = parse_span(row["Citation 1"], books)
                b = parse_span(row["Citation 2"], books)
                if a and b:
                    edges.append([list(a[1]), a[0], list(a[2]), list(b[1]), b[0], list(b[2])])
        print(f"links{n}.csv: {len(edges)} Tanakh edges so far")
    return edges


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tanakh_books = load_tanakh_books()
    names = {b["title"] for b in tanakh_books}
    print("books:", ", ".join(sorted(names)))

    verses, he_titles = build_verses(tanakh_books)
    words = defaultdict(set)
    for i, verse in enumerate(verses):
        for token in verse["he"].split():
            key = consonants(token)
            if key:
                words[key].add(i)

    xrefs = build_xrefs(names)

    (OUT / "tanakh.json").write_text(json.dumps(
        {"books": sorted(names), "he_titles": he_titles, "verses": verses},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "words.json").write_text(json.dumps(
        {k: sorted(v) for k, v in sorted(words.items())},
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "xrefs.json").write_text(json.dumps(xrefs, separators=(",", ":")), encoding="utf-8")
    print(f"verses={len(verses)} word_keys={len(words)} xref_edges={len(xrefs)}")


if __name__ == "__main__":
    main()
