// Scores docs/search.js on data/eval/pairs.jsonl: recall@10 and MRR@10 for each query length.
// Run from the repository root:  node scripts/eval_search.mjs
import { readFileSync } from "node:fs";
import { buildIndex, rankWords } from "../docs/search.js";

const CANON = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
  "I Samuel", "II Samuel", "I Kings", "II Kings", "Isaiah", "Jeremiah", "Ezekiel", "Hosea", "Joel",
  "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
  "Malachi", "Psalms", "Proverbs", "Job", "Song of Songs", "Ruth", "Lamentations", "Ecclesiastes",
  "Esther", "Daniel", "Ezra", "Nehemiah", "I Chronicles", "II Chronicles"];
const tanakh = JSON.parse(readFileSync("docs/data/tanakh.json", "utf8"));
const words = JSON.parse(readFileSync("docs/data/words.json", "utf8"));
const pairs = readFileSync("data/eval/pairs.jsonl", "utf8").trim().split("\n").map(l => JSON.parse(l));
const index = buildIndex(tanakh, words, new Map(CANON.map((b, i) => [b, i])));
const idOf = new Map(tanakh.verses.map((v, i) => [v.id, i]));

const configs = JSON.parse(process.argv[2] || "{}");
const results = {};
for (const n of [4, 10]) {
  const ranks = [];
  for (const row of pairs.filter(r => r.query_words === n)) {
    const target = idOf.get(row.target);
    const ranked = rankWords(row.query, index, configs);
    const pos = ranked.findIndex(([i]) => i === target);
    ranks.push(pos < 0 ? Infinity : pos + 1);
  }
  const recall = ranks.filter(r => r <= 10).length / ranks.length;
  const mrr = ranks.reduce((s, r) => s + (r <= 10 ? 1 / r : 0), 0) / ranks.length;
  results[`${n} words`] = { recall10: +recall.toFixed(4), mrr10: +mrr.toFixed(4), queries: ranks.length };
}
console.log(JSON.stringify({ config: configs, ...results }, null, 2));
