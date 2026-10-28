const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  p.on('pageerror', e => console.log('PAGEERROR', String(e).slice(0,200)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  await p.click('.verse .similar >> nth=0');
  for (let k = 0; k < 12; k++) {
    await p.waitForTimeout(10000);
    const s = await p.textContent('#status');
    if (/reranked/.test(s)) break;
  }
  console.log('status:', await p.textContent('#status'));
  const log = await p.evaluate(() => localStorage.getItem('concordance-log') || '');
  console.log(log.split('\n').filter(l => /reranker|reranked|ERROR|similar/.test(l)).slice(-6).map(l => l.slice(0,220)).join('\n'));
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
