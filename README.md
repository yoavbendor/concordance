# Concordance

Hebrew text of the Torah, searchable in the browser, with cross-references.
Offline use is planned; this first step is the Torah only.

## Data

Text and cross-references come from the public Sefaria export
(https://github.com/Sefaria/Sefaria-Export, bucket `sefaria-export`). Each text
is licensed separately; the Hebrew Torah here is the `merged` version of each
book. Check the license of any text before publishing a derived copy.

## Build

    python3 scripts/build_torah.py

This writes three files into `docs/data/`:

- `torah.json`: every verse, with its nikud and the book's Hebrew title.
- `words.json`: search key (consonants, final letters folded) to verse indices.
- `xrefs.json`: Torah-to-Torah cross-reference spans, as
  `[from_chapter_verse, book, to_chapter_verse, from2, book2, to2]`.

Standard library only. The build downloads the export; nothing is cached.

## Run

Serve `docs/` with any static server, for example:

    python3 -m http.server -d docs 8000

then open http://localhost:8000.

## Status

- Torah only (5 books, 5,846 verses).
- Cross-references kept when both ends fall in the Torah. Whole-chapter
  references such as `Genesis 1` are not parsed yet.
- Not yet: the Tanakh, commentary, a Lance store, an offline service worker,
  and a semantic index.
