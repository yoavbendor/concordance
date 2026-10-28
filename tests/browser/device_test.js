const { chromium } = require('playwright');
async function run(gpu) {
  const b = await chromium.launch();
  const p = await b.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('' + (process.env.BASE_URL || 'http://localhost:8794/') + 'index.html');
  await p.evaluate(v => localStorage.setItem('concordance-gpu', v), gpu ? '1' : '0');
  await p.reload();
  await p.waitForFunction(() => document.getElementById('status').textContent.includes('פסוקים'), null, { timeout: 120000 });
  console.log(`gpu=${gpu} checkbox:`, await p.isChecked('#use-gpu'));
  await p.click('#mode-meaning');
  await p.fill('#q', 'בְּרֵאשִׁית בָּרָא אֱלֹהִים');
  await p.press('#q', 'Enter');
  await p.waitForFunction(() => /שגיאה|התאמות/.test(document.getElementById('status').textContent), null, { timeout: 400000 });
  console.log('  status:', await p.textContent('#status'));
  console.log('  top:', await p.$$eval('.verse .ref', els => els.slice(0,2).map(e => e.textContent)));
  const log = await p.evaluate(() => localStorage.getItem('concordance-log') || '');
  console.log(log.split('\n').filter(l => /text model ready|ERROR/.test(l)).slice(-2).map(l => l.slice(0,220)).join('\n'));
  console.log('  page errors:', errs.length);
  await b.close();
}
(async () => { await run(false); await run(true); })().catch(e => { console.error('FAILED', e.message); process.exit(1); });
