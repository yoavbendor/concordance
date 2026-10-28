const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('verses'), null, { timeout: 120000 });
  await p.fill('#q', 'בראשית'); await p.waitForTimeout(300);
  await p.click('.verse .comments');
  await p.waitForFunction(() => document.querySelectorAll('#sheet-body .com').length > 0 || document.querySelector('#sheet-body .none'), null, { timeout: 60000 });
  console.log('sheet visible:', await p.isVisible('#sheet'), '| title:', await p.textContent('#sheet-title'));
  console.log('commentators:', await p.$$eval('#sheet-body h3', e => e.map(x => x.textContent)));
  await p.click('#sheet-close');
  console.log('closed:', !(await p.isVisible('#sheet')));
  // long press on the Hebrew of the second result
  const second = await p.$('.verse:nth-child(2) > div:nth-child(2)');
  const box = await second.boundingBox();
  await p.mouse.move(box.x + 20, box.y + 10);
  await p.mouse.down();
  await p.waitForTimeout(700);
  await p.mouse.up();
  await p.waitForTimeout(300);
  console.log('after long press, title:', await p.textContent('#sheet-title'));
  console.log('errors:', errs);
  await b.close();
})().catch(e => { console.error('FAILED', e.message); process.exit(1); });
