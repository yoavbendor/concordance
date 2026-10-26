# Concordance

Hebrew text of the Tanakh, searchable in the browser, with cross-references.
Offline use is planned. Torah, Prophets and Writings are in; commentary is not.

## Data

Text and cross-references come from the public Sefaria export
(https://github.com/Sefaria/Sefaria-Export, bucket `sefaria-export`). Each text
is licensed separately; the Hebrew Torah here is the `merged` version of each
book. Check the license of any text before publishing a derived copy.

## Build

    python3 scripts/build_tanakh.py

This writes three files into `docs/data/`:

- `tanakh.json`: every verse, with its nikud and the book's Hebrew title.
- `words.json`: search key (consonants, final letters folded) to verse indices.
- `xrefs.json`: Tanakh cross-reference spans, as
  `[from_chapter_verse, book, to_chapter_verse, from2, book2, to2]`.

Standard library only. The build downloads the export; nothing is cached.

## Lance

    pip install pylance pyarrow
    python3 scripts/write_lance.py

Reads the JSON above and writes three Lance datasets under `data/lance/`
(not committed; rebuild locally):

- `verses.lance`: one row per verse, with BTREE indexes on `book`, `c`, `v`.
- `words.lance`: one row per search key, with `verse_ids` into `verses`; BTREE on `key`.
- `xrefs.lance`: one row per cross-reference span pair; BTREE on `from_book`, `to_book`.

## Embeddings

    python3 scripts/embed_verses.py

EmbeddingGemma 2 (`embeddinggemma-2` from Ollama's registry, GGUF) runs through
llama.cpp's `llama-embedding`, which must be built from a version that knows the
`gemma-embedding2` architecture. The 768-dimension vectors are truncated to 256
(Matryoshka) and renormalized, and written to `verse_vectors.lance`.

Queries need `nprobes=128` and `refine_factor=10`. With the defaults, the IVF_PQ
index missed Genesis 1:1 for "בראשית ברא אלהים"; with these settings it matches
exhaustive search on the checked queries.

## Run

Serve `docs/` with any static server, for example:

    python3 -m http.server -d docs 8000

then open http://localhost:8000.

## Status

- Tanakh: Torah, Prophets and Writings (39 books).
- Cross-references kept when both ends fall in the Tanakh. Whole-chapter
  references such as `Genesis 1` are not parsed yet.
- Not yet: commentary, a Lance store, an offline service worker,
  and a semantic index.
