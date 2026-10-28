const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  await p.click('.verse .ref');
  await p.waitForTimeout(500);
  const count = () => p.$$eval('#reader section.chapter', e => e.map(x => x.dataset.ci));
  console.log('start sections:', await count(), '| title:', await p.textContent('#reader-title'));
  // scroll to the bottom repeatedly: chapters after Genesis 1 load
  for (let k = 0; k < 6; k++) { await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(400); }
  console.log('after down-scroll:', await count(), '| title:', await p.textContent('#reader-title'));
  // scroll to the top: earlier chapters load, the window stays bounded
  for (let k = 0; k < 4; k++) { await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(400); }
  console.log('after up-scroll:', (await count()).length, 'sections, title:', await p.textContent('#reader-title'));
  await p.click('text=Back to results');
  console.log('back, status:', await p.textContent('#status'), '| reader present:', await p.$('#reader') !== null);
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
