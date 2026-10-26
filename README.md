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
(Matryoshka) and renormalized, and written to `verse_vectors.lance`. Verses are embedded with the document prompt
`title: none | text: `; queries need the query prompt `task: search result | query: `.

Queries need `nprobes=128` and `refine_factor=10`. With the defaults, the IVF_PQ
index missed Genesis 1:1 for "בראשית ברא אלהים"; with these settings it matches
exhaustive search on the checked queries.

## Evaluation

    python3 scripts/build_eval.py --links-dir <dir with links0..12.csv and books.json>
    python3 scripts/eval_retrieval.py --model-dir <dir with model_q4.onnx and tokenizer.json>
    python3 scripts/eval_variants.py --model-dir <same>

The test set is 480 pairs from Divrei David on Rashi, which the export links to verses in
Genesis, Exodus, Leviticus and Numbers (Deuteronomy has no such links). A query is the first
4 or 10 words of a comment; the target is the verse it explains. Results (recall@10 / MRR@10,
480 queries per length):

| variant | 4 words | 10 words |
|---|---|---|
| semantic (EmbeddingGemma 2, q4, 256-d) | 0.163 / 0.102 | 0.163 / 0.091 |
| lexical (idf-weighted consonant match) | 0.773 / 0.664 | 0.677 / 0.529 |
| hybrid (semantic + 0.5 lexical) | 0.654 / 0.527 | 0.650 / 0.481 |
| graph (hybrid + cross-reference boost) | 0.658 / 0.526 | 0.638 / 0.482 |

On the 88 and 71 pairs whose query shares no word with the target verse, the semantic
score finds none of the targets. Caveat: commentary quotes the verse it explains, so this
set favours word matching; it measures vocabulary more than meaning.

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
