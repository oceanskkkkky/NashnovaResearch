// 探测小红书创作中心页面真实结构：URL、正文、frames、inputs
const path = require('path');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(__dirname, '..', '.workbuddy', 'xhs-profile'), {
    headless: false, viewport: { width: 1280, height: 900 },
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://creator.xiaohongshu.com/publish/publish', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  console.log('== URL:', page.url());
  console.log('== TITLE:', await page.title());
  const txt = await page.evaluate(() => document.body.innerText.replace(/\n+/g, ' | ').slice(0, 800));
  console.log('== BODY:', txt);
  for (const f of page.frames()) {
    console.log('-- frame:', f.url().slice(0, 120));
    try {
      const inputs = await f.$$eval('input, textarea, [contenteditable="true"]', els => els.slice(0, 10).map(e => ({ tag: e.tagName, type: e.type || '', ph: (e.placeholder || '').slice(0, 30), ce: e.getAttribute('contenteditable') })));
      if (inputs.length) console.log('   inputs:', JSON.stringify(inputs));
    } catch {}
  }
  await page.screenshot({ path: path.join(__dirname, '..', 'reports', 'stock-almanac', 'xhs-probe.png'), fullPage: true });
  console.log('截图已存 xhs-probe.png');
  await ctx.close();
})();
