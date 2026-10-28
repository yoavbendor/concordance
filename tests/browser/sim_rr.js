const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  await p.click('.verse .similar >> nth=0');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('reranked'), null, { timeout: 90000 }).catch(() => {});
  console.log('status:', await p.textContent('#status'));
  console.log('top 5:', await p.$$eval('.verse .ref', e => e.slice(0,5).map(x => x.childNodes[0].textContent)));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
