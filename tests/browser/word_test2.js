const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  for (const w of ['בראשית ברא אלהים', 'בראשית', 'ויאמר אלהים יהי אור', 'אלוהים נוקם', 'השמים והארץ']) {
    await p.fill('#q', w); await p.waitForTimeout(400);
    const top = await p.$$eval('.verse .ref', els => els.slice(0,3).map(e => e.textContent));
    console.log(w, '->', await p.textContent('#status'), '| top:', top);
  }
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
