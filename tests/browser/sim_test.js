const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  const t0 = Date.now();
  await p.click('.verse .similar');
  await p.waitForFunction(() => /similar to/.test(document.getElementById('status').textContent), null, { timeout: 30000 });
  console.log('ms:', Date.now() - t0);
  console.log('mode meaning:', await p.getAttribute('#mode-meaning','aria-pressed'), '| status:', await p.textContent('#status'));
  console.log('box unchanged:', await p.inputValue('#q'));
  console.log('top 5:', await p.$$eval('.verse .ref', e => e.slice(0,5).map(x => x.childNodes[0].textContent)));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
