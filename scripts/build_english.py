"""Write docs/data/english.json: the English translation of each Tanakh verse, keyed by the
same verse id as tanakh.json. Translation: The Holy Scriptures, JPS 1917 (public domain),
from the Sefaria export. Standard library only.
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
BOOKS_JSON = "https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json"
VERSION = "The Holy Scriptures A New Translation JPS 1917"
TAG = re.compile(r"<[^>]+>")


def flat(x):
    if isinstance(x, list):
        return " ".join(flat(y) for y in x)
    return " ".join(TAG.sub(" ", x).split())


def main():
    books = json.loads(urllib.request.urlopen(BOOKS_JSON, timeout=300).read())["books"]
    tanakh = [b for b in books if b.get("language") == "English" and b.get("versionTitle") == VERSION
              and b.get("categories", [None])[:1] == ["Tanakh"] and len(b.get("categories", [])) > 1
              and b["categories"][1] in ("Torah", "Prophets", "Writings")]
    english = {}
    for b in tanakh:
        text = json.loads(urllib.request.urlopen(b["json_url"], timeout=300).read())["text"]
        for c, chapter in enumerate(text, 1):
            for v, verse in enumerate(chapter, 1):
                s = flat(verse)
                if s:
                    english[f"{b['title']} {c}:{v}"] = s
    ids = [v["id"] for v in json.loads((DATA / "tanakh.json").read_text(encoding="utf-8"))["verses"]]
    missing = [i for i in ids if i not in english]
    assert not missing, f"no English for {len(missing)} verses, e.g. {missing[:3]}"
    (DATA / "english.json").write_text(json.dumps({i: english[i] for i in ids}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"english.json: {len(ids)} verses")


if __name__ == "__main__":
    main()
