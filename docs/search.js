// Word search for the concordance: several words, ranked by relevance (BM25 with
// match-type weights). Pure functions, so the page and scripts/eval_search.mjs share them.

const FINAL = { "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ" };
const MARKS = /[֑-ׇ]/g;
// One-letter prefixes (and, the, in, to, like, from, that...) that often attach to a word.
export const PREFIXES = ["ו", "ה", "ב", "ל", "כ", "מ", "ש"];

// Same normalization as scripts/build_tanakh.py consonants().
export function consonants(word) {
  return word.normalize("NFC").replace(MARKS, "")
    .replace(/[^א-ת]/g, "").replace(/[ךםןףץ]/g, c => FINAL[c]);
}

export function queryKeys(query) {
  return query.split(/\s+/).map(consonants).filter(k => k.length > 0);
}

// The postings a query word can match, each with a weight for the match type:
// the word as written (1.0), the word without a prefix (0.7), and, only when nothing else
// matches, the word with one internal vav removed (0.5), since the Tanakh spells אלהים for אלוהים.
export function candidateKeys(key, words, opts = {}) {
  const prefixW = opts.prefixW ?? 0.5, vavW = opts.vavW ?? 0.5;
  const out = [];
  if (words[key]) out.push([key, 1.0]);
  if (prefixW > 0 && key.length > 2 && !words[key]) {  // only when the word as written is absent
    for (const p of PREFIXES) {
      if (key.startsWith(p) && words[key.slice(1)]) { out.push([key.slice(1), prefixW]); break; }
    }
  }
  if (vavW > 0 && out.length === 0) {
    for (let j = 1; j < key.length - 1; j++) {
      if (key[j] === "ו" && words[key.slice(0, j) + key.slice(j + 1)]) {
        out.push([key.slice(0, j) + key.slice(j + 1), vavW]);
      }
    }
  }
  return out;
}

// Ranks verses for a query. `index` is { words, verses, lens, avgLen, N, canonical }:
// words: key -> verse indices; verses: { he, book, c, v }[]; lens: words per verse;
// canonical: verse index -> canonical order number. Returns [verseIndex, score][] best first.
export function rankWords(query, index, opts = {}) {
  // Defaults chosen on data/eval: k1 = 0 scores each word by its idf alone; term frequency and
  // verse length made the ranking worse on the test set.
  const k1 = opts.k1 ?? 0, b = opts.b ?? 0.75;
  const { words, verses, lens, avgLen, N, canonical } = index;
  const keysCache = new Map();
  const keysOf = i => {
    let ks = keysCache.get(i);
    if (!ks) {
      ks = verses[i].he.split(" ").map(consonants).filter(Boolean);
      keysCache.set(i, ks);
    }
    return ks;
  };
  const total = new Map();
  for (const key of queryKeys(query)) {
    // Per verse, the best contribution of this query word over its candidate forms.
    const best = new Map();
    for (const [k, w] of candidateKeys(key, words, opts)) {
      const df = words[k].length;
      const idf = Math.log(N / df);
      for (const i of words[k]) {
        let tf = 0;
        for (const x of keysOf(i)) if (x === k) tf++;
        if (tf === 0) tf = 1;  // indexed as present, though the key was not found in this verse's words
        const norm = k1 * (1 - b + (b * lens[i]) / avgLen);
        const score = w * idf * (tf * (k1 + 1)) / (tf + norm);
        if (score > (best.get(i) ?? 0)) best.set(i, score);
      }
    }
    for (const [i, s] of best) total.set(i, (total.get(i) ?? 0) + s);
  }
  return [...total.entries()].sort((x, y) => (y[1] - x[1]) || (canonical[x[0]] - canonical[y[0]]));
}

// Build the index the ranker needs from the page data (tanakh.json and words.json).
export function buildIndex(tanakh, words, canonicalOrder) {
  const verses = tanakh.verses;
  const lens = verses.map(v => v.he.split(" ").filter(Boolean).length);
  const avgLen = lens.reduce((a, b) => a + b, 0) / lens.length;
  const canonical = verses.map(v => {
    const b = canonicalOrder.get(v.book) ?? 99;
    return b * 1e6 + v.c * 1e3 + v.v;
  });
  return { words, verses, lens, avgLen, N: verses.length, canonical };
}
