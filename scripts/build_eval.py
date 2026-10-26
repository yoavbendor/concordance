"""Build a retrieval test set from commentary on the Torah.

Source: Divrei David on Rashi (a commentary on Rashi's Torah comments), which the export
links verse by verse; the direct Rashi-to-verse links are not in the export. A query is the
opening words of a comment, the way a reader would type a phrase, and the target is the verse
it explains.
Output: data/eval/pairs.jsonl, one {"query_words", "target", "text"} per line, in
two query lengths. Needs the link CSVs and books.json from the Sefaria export.

    python3 scripts/build_eval.py --links-dir <dir with links0..12.csv and books.json>
"""
import argparse
import csv
import glob
import json
import random
import re
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "eval"
EXPORT = "https://storage.googleapis.com/sefaria-export"
TORAH = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
TAGS = re.compile(r"<[^>]+>")
PARENS = re.compile(r"\([^)]*\)")         # scripture references in brackets, removed so they do not leak
SINGLE = re.compile(r"^(\S+) (\d+):(\d+)$")
SPAN = re.compile(r"^(.+?) (\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")


def clean(text):
    text = TAGS.sub(" ", text)
    text = PARENS.sub(" ", text)
    text = re.sub(r"[֑-ׇ]", "", text)      # points and marks, as in the page
    text = re.sub(r"[^א-ת ]+", " ", text)
    return " ".join(text.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--links-dir", required=True)
    ap.add_argument("--per-book", type=int, default=120)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    links = Path(args.links_dir)
    books = json.load(open(links / "books.json"))["books"]

    # Rashi-to-verse rows, one target verse each.
    rows = []
    for f in sorted(glob.glob(str(links / "links*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8", newline="")):
            if r["Text 2"] not in TORAH or r["Text 1"] != f"Divrei David on Rashi, {r['Text 2']}":
                continue
            if r["Conection Type"] != "commentary":
                continue
            m = SINGLE.match(r["Citation 2"].strip())
            seg = re.match(r"^(.+?) (\d+):(\d+):(\d+)$", r["Citation 1"].strip())
            if m and seg:
                rows.append((r["Text 2"], int(m.group(2)), int(m.group(3)), int(seg.group(2)), int(seg.group(3)), int(seg.group(4))))
    print("commentary-to-verse rows:", len(rows))

    # One Hebrew file holds all of Divrei David on Rashi, keyed by book name.
    dd_url = next(b["json_url"] for b in books if b["title"] == "Divrei David on Rashi"
                  and b.get("language") == "Hebrew" and b.get("versionTitle") == "merged")
    dd_text = json.loads(urllib.request.urlopen(dd_url, timeout=300).read())["text"]

    rng = random.Random(args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for book in TORAH:
        mine = [r for r in rows if r[0] == book]
        rng.shuffle(mine)
        text = dd_text[book]
        taken = 0
        for _, c, v, cc, vv, seg in mine:
            try:
                words = clean(text[cc - 1][vv - 1][seg - 1]).split()
            except (IndexError, TypeError):
                continue
            if len(words) < 12:
                continue
            target = f"{book} {c}:{v}"
            out.append({"query_words": 4, "query": " ".join(words[:4]), "target": target, "text": " ".join(words)})
            out.append({"query_words": 10, "query": " ".join(words[:10]), "target": target, "text": " ".join(words)})
            taken += 1
            if taken >= args.per_book:
                break
        print(book, "pairs:", taken)
    (OUT / "pairs.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8")
    print("wrote", len(out), "query rows to", OUT / "pairs.jsonl")


if __name__ == "__main__":
    main()
