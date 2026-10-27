"""English retrieval test set: opening words of English commentary on the Torah, with the
verse each comment explains as the target. Sources: English Rashi, Ramban and Ibn Ezra
(merged versions in the export). Written to data/eval/pairs_en.jsonl, in the same format as
pairs.jsonl ({query_words, query, target, text}). Used for evaluation only.
"""
import json
import random
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "eval"
BOOKS_JSON = "https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json"
TORAH = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
COMMENTATORS = ["Rashi", "Ramban", "Ibn Ezra"]
TAG = re.compile(r"<[^>]+>")


def clean(text):
    # Drop markup, bracketed scripture references, and Hebrew words, so the query is English.
    text = TAG.sub(" ", text)
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text)
    return " ".join(w for w in text.split() if not re.search(r"[\u0590-\u05FF]", w))


def main():
    books = json.loads(urllib.request.urlopen(BOOKS_JSON, timeout=300).read())["books"]
    rng = random.Random(7)
    out = []
    for name in COMMENTATORS:
        for book in TORAH:
            b = next((x for x in books if x.get("language") == "English" and x.get("versionTitle") == "merged"
                      and x["title"] == f"{name} on {book}"), None)
            if b is None:
                continue
            text = json.loads(urllib.request.urlopen(b["json_url"], timeout=300).read())["text"]
            candidates = []
            for c, chapter in enumerate(text, 1):
                for v, comments in enumerate(chapter, 1):
                    if isinstance(comments, str):
                        comments = [comments]
                    for comment in comments:
                        t = clean(comment) if isinstance(comment, str) else ""
                        words = t.split()
                        if len(words) >= 12:
                            candidates.append((f"{book} {c}:{v}", words))
            rng.shuffle(candidates)
            for target, words in candidates[:60]:
                text_all = " ".join(words)
                out.append({"query_words": 4, "query": " ".join(words[:4]), "target": target, "text": text_all})
                out.append({"query_words": 10, "query": " ".join(words[:10]), "target": target, "text": text_all})
            print(name, book, min(len(candidates), 60))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pairs_en.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8")
    print("wrote", len(out), "rows")


if __name__ == "__main__":
    main()
