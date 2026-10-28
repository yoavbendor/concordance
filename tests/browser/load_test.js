const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext();
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('פסוקים'), null, { timeout: 120000 });
  await p.click('#mode-meaning');
  await p.fill('#q', 'בְּרֵאשִׁית בָּרָא אֱלֹהִים');
  await p.press('#q', 'Enter'); await p.press('#q', 'Enter'); // a second search while loading
  await p.waitForFunction(() => document.querySelector('.verse .ref'), null, { timeout: 600000 });
  console.log('first run top:', await p.$$eval('.verse .ref', els => els[0].textContent));
  // Reload: the weights should come from the cache.
  await p.reload();
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('פסוקים'), null, { timeout: 120000 });
  await p.click('#mode-meaning');
  await p.fill('#q', 'בְּרֵאשִׁית בָּרָא אֱלֹהִים');
  await p.press('#q', 'Enter');
  await p.waitForFunction(() => document.querySelector('.verse .ref'), null, { timeout: 600000 });
  const log = await p.evaluate(() => localStorage.getItem('concordance-log') || '');
  console.log(log.split('\n').filter(l => /weights|text model|ERROR/.test(l)).slice(-6).map(l => l.slice(0,160)).join('\n'));
  console.log('page errors:', errs.length);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
