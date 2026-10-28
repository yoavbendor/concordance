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

## English meaning search and the reranker

    python3 scripts/build_eval_en.py                 # English Rashi, Ramban, Ibn Ezra as queries
    python3 scripts/eval_english.py --model-dir <dir>
    python3 scripts/eval_rerank.py --model-dir <dir> --rerank-dir <dir with jina's model_int8.onnx and tokenizer.json>

On 1,080 English queries (540 per length), the first stage gives recall@10 0.13 (4 words)
and 0.32 (10 words), with recall@50 at 0.25 and 0.47. Reranking the top 50 with
jina-reranker-v1-tiny-en (int8) raises recall@10 to 0.23 and 0.44 and MRR@10 to 0.14 and 0.35
(first 150 queries of each length). The page reranks the top 30, which keeps most of the
gain (recall@10 0.21 and 0.41) at less cost on a phone.

## Hierarchical meaning search (tested, not adopted)

    python3 scripts/build_windows.py
    python3 scripts/eval_windows.py --model-dir <dir>

Windows of 5 verses, 11 verses and whole chapters were embedded from the English and
scored on the English test set. Verse vectors alone (10 words: recall@10 0.32, MRR 0.19)
beat every window level (best window alone 0.07 and 0.05 recall@10) and every mix with
verse scores (best 0.28 recall@10 at weight 0.5). The verse-level search with the
reranker stays the search; the windows are kept only for later experiments.

## Rebuild from scratch

What is in git: the page (`docs/`), the scripts, the tests, and the small generated page data.
What is not: the Lance tables (`data/lance/`), the evaluation pairs (`data/eval/`), the
downloaded models and the llama.cpp build. This is how to make them again, in order. Run
everything from the repository root.

Requirements: Python 3 with `pip install pylance pyarrow numpy onnxruntime tokenizers`;
Node.js with Playwright only for the browser tests; cmake and a C++ compiler for llama.cpp.

1. **Tanakh text, cross-references and word index** (downloads the Sefaria export):

       python3 scripts/build_tanakh.py          # docs/data/tanakh.json, words.json, xrefs.json
       python3 scripts/write_lance.py           # data/lance/verses, words, xrefs (+ indexes)

2. **English translation** (JPS 1917, all 39 books): `python3 scripts/build_english.py`
   writes `docs/data/english.json`.

3. **Embedding model.** The text model is `model_q4.onnx` and `model_q4.onnx_data` from
   `onnx-community/embeddinggemma-2-ONNX`; the page downloads it itself. The Lance
   embeddings use the GGUF file of `embeddinggemma-2` from Ollama's registry (the text
   blob), and a llama.cpp build that knows the `gemma-embedding2` architecture:

       git clone --depth 1 https://github.com/ggml-org/llama.cpp
       cmake -S llama.cpp -B llama.cpp/build -DCMAKE_BUILD_TYPE=Release
       cmake --build llama.cpp/build --target llama-embedding -j4
       export LLAMA_EMBEDDING=$PWD/llama.cpp/build/bin/llama-embedding
       export EMBEDDINGGEMMA_GGUF=<path to the embeddinggemma-2 text GGUF>

4. **English vectors for the page** (about 15 minutes on 4 cores):
   `python3 scripts/embed_english.py` writes `docs/data/english_vectors.f16` and
   `data/lance/english_vectors.lance`.

5. **Commentary** (Rashi, Ramban, Ibn Ezra, Sforno): `python3 scripts/build_commentary.py`
   writes `docs/data/commentary/` (per book, and `index.json`) and `data/lance/commentary.lance`.

6. **Optional.** Hebrew verse vectors (`python3 scripts/embed_verses.py`, then
   `python3 scripts/export_vectors.py`) feed `data/lance/verse_vectors.lance`; the page no
   longer uses the Hebrew vectors. Windows (`python3 scripts/build_windows.py`) feed the
   experiment in the section above.

7. **Evaluation data.** The link files for the Hebrew test set come from the export bucket:

       mkdir -p data/links && for n in $(seq 0 12); do \
         curl -sS -o data/links/links$n.csv https://storage.googleapis.com/sefaria-export/links/links$n.csv; done
       curl -sS -o data/links/books.json https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json
       python3 scripts/build_eval.py --links-dir data/links      # Hebrew pairs
       python3 scripts/build_eval_en.py                          # English pairs

   The evaluation scripts need the model files of step 3 and the reranker
   (`jinaai/jina-reranker-v1-tiny-en`, `onnx/model_int8.onnx` and `tokenizer.json`, from Hugging
   Face), passed with `--model-dir` and `--rerank-dir`.

8. **Run the page**: `python3 -m http.server -d docs 8000`, then open http://localhost:8000.

9. **Browser tests**: see `tests/browser/README.md`.

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

## Later

- **Hierarchical meaning search.** Embed windows of several verses (about 5, 11, and whole
  chapters) as well as single verses, using the English translation. A passage-level
  match would find a meaning that runs across verses, and would tolerate verse numbering
  that differs between the Hebrew and an English translation. The verse-level index stays
  for precise hits. Judge it on the evaluation set first: the Divrei David comments often
  span several verses, so the test should show whether the windows help before we keep them.
- **Reading and commentary.** A long press on a word opens its materials in a sheet;
  verse-level commentary first, from the Lance tables.
