// 将股市老黄历移动端HTML按栏目截屏为小红书卡片图
// 用法: node xhs-shoot.js <report.html> <outDir>
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const [,, htmlPath, outDir] = process.argv;
  if (!htmlPath || !outDir) { console.error('usage: node xhs-shoot.js <report.html> <outDir>'); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 480, height: 1000 }, deviceScaleFactor: 2.3 });
  await page.goto('file:///' + path.resolve(htmlPath).replace(/\\/g, '/'));
  await page.waitForTimeout(600);

  const shots = [
    ['01-cover', '#cover'],
    ['02-summary', '#executive-summary'],
    ['03-macro', '#macro'],
    ['04-market', '#market'],
    ['05-sectors', '#sectors'],
    ['06-pick-1', '#picks .m-stock@0'],
    ['07-pick-2', '#picks .m-stock@1'],
    ['08-risks', '#risks'],
  ];
  for (const [name, sel] of shots) {
    let loc;
    if (sel.includes('@')) {
      const [base, idx] = sel.split('@');
      loc = page.locator(base).nth(Number(idx));
    } else {
      loc = page.locator(sel.split(', ').join(',')).first();
    }
    try {
      await loc.screenshot({ path: path.join(outDir, name + '.png') });
      console.log('OK', name);
    } catch (e) {
      console.error('FAIL', name, e.message.split('\n')[0]);
    }
  }
  await browser.close();
})();
