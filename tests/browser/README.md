# Browser tests

Playwright scripts that drive `docs/index.html` in headless Chromium. Each one prints what it
found and the page errors; none of them is run by CI yet.

Setup, once: `npm install -g playwright` and `npx playwright install chromium`
(or use an existing Chromium). Serve the page first:

    python3 -m http.server -d docs 8794

Run a script with the server's address:

    BASE_URL=http://localhost:8794/ NODE_PATH=$(npm root -g) node tests/browser/word_test2.js

Scripts (what they check):
- `word_test2.js`: word search, including multi-word queries, ranked with Genesis first.
- `reader_test.js`, `cont_test.js`: the chapter reader opens and scrolls across chapters.
- `he_test.js`: Hebrew labels for references and chapters.
- `sheet_test.js`, `word_sheet.js`, `xref_sheet.js`: the commentary sheet, the word sheet and the
  cross-references in the sheet.
- `empty_test.js`: the grey 💬 button on verses without commentary.
- `en_test.js`, `sim_test.js`, `sim_rr.js`, `sim_rr2.js`: English meaning search and `~=~`
  (the first meaning search downloads the model, so these can take minutes).
- `rerank_test.js`: meaning search with the reranker.
- `device_test.js`, `load_test.js`: the CPU/GPU switch and the cached model load.

The model downloads (about 174 MB for the text model, about 33 MB for the reranker) happen on
first use; the tests wait for them.
