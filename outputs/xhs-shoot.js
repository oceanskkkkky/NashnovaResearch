// 将股市老黄历移动端HTML按栏目渲染为统一的1080x1440小红书卡片图
// 用法: node xhs-shoot.js <report.html> <outDir>
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const [,, htmlPath, outDir] = process.argv;
  if (!htmlPath || !outDir) {
    console.error('usage: node xhs-shoot.js <report.html> <outDir>');
    process.exit(1);
  }

  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const sourcePage = await browser.newPage({ viewport: { width: 480, height: 1000 } });
  await sourcePage.goto('file:///' + path.resolve(htmlPath).replace(/\\/g, '/'));
  await sourcePage.waitForTimeout(500);

  const sourceCss = (await sourcePage.locator('style').allTextContents()).join('\n');
  const shots = [
    ['01-cover', '#cover'],
    ['02-summary', '#executive-summary'],
    ['03-macro', '#macro'],
    ['04-market', '#market'],
    ['05-sectors', '#sectors'],
    ['06-pick', '#picks'],
    ['07-risks', '#risks'],
  ];

  for (const [name, selector] of shots) {
    const source = sourcePage.locator(selector).first();
    if (await source.count() === 0) {
      console.error('FAIL', name, 'selector not found:', selector);
      continue;
    }

    const outerHtml = await source.evaluate(el => el.outerHTML);
    const cardPage = await browser.newPage({
      viewport: { width: 480, height: 640 },
      deviceScaleFactor: 2.25,
    });

    await cardPage.setContent(`
      <style>${sourceCss}</style>
      <style>
        html,body{margin:0!important;width:480px;height:640px;overflow:hidden;background:#f3efe5!important}
        body{display:flex!important;align-items:center!important;justify-content:center!important;min-width:0!important}
        .xhs-stage{width:456px;height:616px;display:flex;align-items:center;justify-content:center;overflow:hidden}
        .xhs-root{display:flex;align-items:center;justify-content:center;transform-origin:center center}
        .xhs-root>.sec,.xhs-root>.cover{box-sizing:border-box!important;width:456px!important;margin:0!important}
      </style>
      <div class="xhs-stage"><div class="xhs-root">${outerHtml}</div></div>
    `, { waitUntil: 'load' });

    await cardPage.evaluate(() => {
      const stage = document.querySelector('.xhs-stage');
      const root = document.querySelector('.xhs-root');
      const item = root.firstElementChild;
      const width = Math.max(item.scrollWidth, item.getBoundingClientRect().width);
      const height = Math.max(item.scrollHeight, item.getBoundingClientRect().height);
      const scale = Math.min(1, (stage.clientWidth - 4) / width, (stage.clientHeight - 4) / height);
      root.style.transform = `scale(${scale})`;
    });

    await cardPage.screenshot({ path: path.join(outDir, name + '.png') });
    console.log('OK', name, '1080x1440');
    await cardPage.close();
  }

  await sourcePage.close();
  await browser.close();
})();
