const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'ויאמר'); await p.waitForTimeout(300);
  const info = await p.$$eval('.verse', els => els.slice(0, 40).map(v => ({ ref: v.querySelector('.ref').childNodes[0].textContent, empty: v.querySelector('.comments').classList.contains('empty') })));
  console.log('with comments:', info.filter(x => !x.empty).slice(0,3).map(x => x.ref));
  console.log('empty:', info.filter(x => x.empty).slice(0,3).map(x => x.ref));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
