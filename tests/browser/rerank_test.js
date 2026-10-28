const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.click('#mode-meaning');
  await p.fill('#q', 'the Lord is my shepherd');
  await p.press('#q', 'Enter');
  await p.waitForFunction(() => /reranked|closest|Error/.test(document.getElementById('status').textContent) && !/Refining|Loading/.test(document.getElementById('status').textContent), null, { timeout: 900000 });
  console.log('status:', await p.textContent('#status'));
  console.log('top 5:', await p.$$eval('.verse .ref', e => e.slice(0,5).map(x => x.childNodes[0].textContent)));
  const log = await p.evaluate(() => localStorage.getItem('concordance-log') || '');
  console.log(log.split('\n').filter(l => /reranker|reranked|ERROR/.test(l)).slice(-4).map(l => l.slice(0,200)).join('\n'));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
