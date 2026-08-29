// 探测小红书创作中心页面真实结构：URL、正文、frames、inputs
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(__dirname, '..', '.workbuddy', 'xhs-profile'), {
    headless: false, viewport: { width: 1280, height: 900 },
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://creator.xiaohongshu.com/publish/publish', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(4000);
  const diagnostics = {
    url: page.url(),
    title: await page.title(),
    body: await page.evaluate(() => document.body.innerText.replace(/\n+/g, ' | ').slice(0, 1600)),
    tabs: await page.$$eval('*', els => els.filter(e => /上传图文/.test((e.textContent || '').trim()) && e.children.length <= 2).slice(0, 20).map(e => ({
      tag: e.tagName,
      text: (e.textContent || '').trim(),
      className: String(e.className || ''),
      role: e.getAttribute('role'),
      outerHTML: e.outerHTML.slice(0, 500),
      rect: (() => { const r = e.getBoundingClientRect(); return { x:r.x, y:r.y, w:r.width, h:r.height }; })(),
    }))),
    frames: [],
  };
  for (const f of page.frames()) {
    const frameInfo = { url: f.url().slice(0, 160), inputs: [] };
    try {
      frameInfo.inputs = await f.$$eval('input, textarea, [contenteditable="true"]', els => els.slice(0, 20).map(e => ({ tag: e.tagName, type: e.type || '', ph: (e.placeholder || '').slice(0, 60), ce: e.getAttribute('contenteditable'), multiple: !!e.multiple, accept: e.accept || '', className: String(e.className || '') })));
    } catch {}
    diagnostics.frames.push(frameInfo);
  }
  fs.writeFileSync(path.join(__dirname, '..', 'reports', 'stock-almanac', 'xhs-probe.json'), JSON.stringify(diagnostics, null, 2), 'utf8');
  console.log(JSON.stringify(diagnostics, null, 2));
  await page.screenshot({ path: path.join(__dirname, '..', 'reports', 'stock-almanac', 'xhs-probe.png'), fullPage: true });
  console.log('截图已存 xhs-probe.png');
  await ctx.close();
})();
