const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'ויאמר'); await p.waitForTimeout(300);
  // long press on the first word of the first result
  const w = await p.$('.verse:nth-child(1) .he .w >> nth=1');
  const box = await w.boundingBox();
  await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await p.mouse.down(); await p.waitForTimeout(700); await p.mouse.up();
  await p.waitForFunction(() => document.querySelector('#sheet-body h3'), null, { timeout: 30000 });
  console.log('word sheet title:', await p.textContent('#sheet-title'));
  console.log('headings:', await p.$$eval('#sheet-body h3', e => e.map(x => x.textContent)));
  console.log('occurrence buttons:', await p.$$eval('#sheet-body .occ', e => e.length));
  await p.click('#sheet-close');
  // long press on the verse's English line: the verse sheet opens instead
  const en = await p.$('.verse:nth-child(1) .en');
  const eb = await en.boundingBox();
  await p.mouse.move(eb.x + 10, eb.y + 5); await p.mouse.down(); await p.waitForTimeout(700); await p.mouse.up();
  await p.waitForTimeout(500);
  console.log('verse sheet title:', await p.textContent('#sheet-title'));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
