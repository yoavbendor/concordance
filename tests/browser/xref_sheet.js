const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  await p.click('.verse .comments');
  await p.waitForSelector('#sheet-body .xref', { timeout: 60000 });
  console.log('xref buttons:', await p.$$eval('#sheet-body .xref', e => e.slice(0,4).map(x => x.textContent)));
  await p.click('#sheet-body .xref >> nth=0');
  console.log('sheet closed:', !(await p.isVisible('#sheet')), '| status:', await p.textContent('#status'));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
