const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.click('#mode-meaning');
  for (const q of ['God created the heaven and the earth', 'the Lord is my shepherd']) {
    await p.fill('#q', q);
    await p.press('#q', 'Enter');
    await p.waitForFunction(() => /Error|closest|not available/.test(document.getElementById('status').textContent), null, { timeout: 900000 });
    console.log(q, '->', await p.textContent('#status'), '| top:', await p.$$eval('.verse .ref', e => e.slice(0,3).map(x => x.childNodes[0].textContent)));
    console.log('  english line:', await p.$eval('.verse .en', e => e.textContent).catch(() => 'none'));
  }
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
