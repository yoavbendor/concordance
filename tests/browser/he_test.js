const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('פסוקים'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  console.log('result labels:', await p.$$eval('.verse .ref', e => e.slice(0,3).map(x => x.childNodes[0].textContent)));
  await p.click('.verse .ref');
  console.log('status:', await p.textContent('#status'), '| title:', await p.textContent('.reader-nav .title'));
  console.log('verse num:', await p.textContent('.vline.focus .vnum'));
  await p.click('text=← פרק הבא');
  console.log('next:', await p.textContent('#status'));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
