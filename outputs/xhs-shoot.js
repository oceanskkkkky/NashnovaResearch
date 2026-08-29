// 将行情老黄历移动端HTML按栏目渲染为统一的1080x1440小红书卡片图
// 用法: node xhs-shoot.js <report.html> <outDir>
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

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

    let outerHtml = await source.evaluate(el => el.outerHTML);
    let cardSpecificCss = '';

    const compactCards = new Set([
      '02-summary',
      '03-macro',
      '04-market',
      '06-pick',
      '07-risks',
    ]);
    if (compactCards.has(name)) {
      cardSpecificCss = `
        .xhs-stage{align-items:flex-start!important;padding-top:12px}
        .xhs-root{align-items:stretch!important}
        .xhs-root>.sec{height:592px!important;min-height:592px!important;padding:30px 28px!important;border-top:5px solid #b98532!important;box-shadow:0 10px 28px rgba(24,51,45,.07);overflow:hidden}
        .xhs-root>.sec .kicker{font-size:12px!important;letter-spacing:.14em!important}
        .xhs-root>.sec h2{margin:5px 0 20px!important;font-size:34px!important;line-height:1.18!important}
        .xhs-root>.sec .line,.xhs-root>.sec .kv{font-size:18px!important;line-height:1.55!important}
        .xhs-root>.sec .k{font-size:16px!important;min-width:82px!important}
        #executive-summary,#macro,#market,#picks,#risks{display:flex!important;flex-direction:column!important}
        #executive-summary .line{flex:1;min-height:70px;align-items:center;padding:13px 4px!important}
        #executive-summary>p{margin:18px -4px 0!important;padding:17px 18px;background:#18332d;color:#fff8e8;border-left:5px solid #b98532;font-size:17px;line-height:1.55}
        #macro .kv{flex:1;min-height:150px;margin-top:14px;padding:24px 20px!important;align-items:flex-start!important;background:#faf5e9;border:1px solid #e1d9ca!important;border-left:5px solid #b98532!important}
        #macro .kv .k{font:700 22px/1.3 STSong,"Songti SC",SimSun,serif;color:#18332d}
        #macro .kv span:last-child{max-width:290px;font-size:19px;line-height:1.75}
        #market .line{flex:1;min-height:72px;align-items:center;padding:14px 4px!important}
        #market>p{margin:20px 0 0!important;padding:20px 20px;background:#f4efe2;border-left:5px solid #b98532;font-size:18px;line-height:1.75}
        #picks .stock{flex:1;display:flex;flex-direction:column;margin-top:0!important;padding-top:18px!important}
        #picks .stock h3{margin:0 0 16px!important;padding:18px 20px;background:#18332d;color:#fff8e8;font-size:28px!important;line-height:1.35}
        #picks .stock p{margin:7px 0!important;padding:17px 18px;background:#faf5e9;border-left:5px solid #b98532;font-size:18px;line-height:1.65}
        #risks ul{flex:1;display:flex;flex-direction:column;justify-content:space-between;margin:0!important;padding:0!important;list-style:none}
        #risks li{margin:0 0 10px!important;padding:15px 18px 15px 46px;background:#faf5e9;border-left:5px solid #b98532;font-size:18px;line-height:1.55;position:relative}
        #risks li::before{content:"!";position:absolute;left:18px;top:15px;color:#a83e32;font-weight:800}
        #risks>p{margin:10px 0 0!important;padding:16px 18px;background:#18332d;color:#fff8e8;font-size:17px;line-height:1.5}`;
    }

    if (name === '01-cover') {
      const cover = await source.evaluate(el => {
        const textOf = selector => el.querySelector(selector)?.textContent?.trim() || '';
        const date = textOf('.date, .m-date, .eyebrow');
        const headline = textOf('h1').replace(/^今日\s*/, '').trim();
        const stateTitle = textOf('.state b, .state h2, .m-state h2, .m-state b');
        const stateNode = el.querySelector('.state, .m-state');
        let stateSummary = stateNode?.textContent?.trim() || '';
        if (stateTitle && stateSummary.startsWith(stateTitle)) {
          stateSummary = stateSummary.slice(stateTitle.length).trim();
        }

        let doText = '';
        let avoidText = '';
        const ritual = [...el.querySelectorAll('.m-ritual span')];
        if (ritual.length >= 2) {
          doText = ritual[0].textContent.replace(/^宜\s*/, '').trim();
          avoidText = ritual[1].textContent.replace(/^忌\s*/, '').trim();
        } else {
          const line = [...el.querySelectorAll('p')]
            .map(node => node.textContent.trim())
            .find(text => text.includes('宜') && text.includes('忌')) || '';
          const match = line.match(/宜\s*(.*?)\s*忌\s*(.*)/);
          if (match) {
            doText = match[1].trim();
            avoidText = match[2].trim();
          }
        }

        return { date, headline, stateTitle, stateSummary, doText, avoidText };
      });

      const escapedHeadline = escapeHtml(cover.headline);
      const headlineHtml = cover.headline.length > 6 && escapedHeadline.includes('，')
        ? escapedHeadline.replace('，', '，<br>')
        : escapedHeadline;

      outerHtml = `
        <article class="xhs-almanac-cover">
          <div class="almanac-brand">
            <span class="almanac-seal">历</span>
            <div><strong>行情老黄历</strong><small>A-SHARE DAILY RESEARCH</small></div>
          </div>
          <div class="almanac-hero">
            <div class="almanac-date">${escapeHtml(cover.date)}</div>
            <div class="almanac-title"><em>今日</em><strong>${headlineHtml}</strong></div>
            <div class="almanac-state">${escapeHtml(cover.stateTitle)}</div>
            <div class="almanac-summary">${escapeHtml(cover.stateSummary)}</div>
          </div>
          <div class="almanac-ritual">
            <div><b>今日宜</b><span>${escapeHtml(cover.doText)}</span></div>
            <div><b>今日忌</b><span>${escapeHtml(cover.avoidText)}</span></div>
          </div>
          <div class="almanac-disclaimer">标题仅为栏目包装，正文为数据研究<br>仅供研究参考，不构成投资建议</div>
        </article>`;
      cardSpecificCss = `
        .xhs-almanac-cover{width:456px;height:616px;padding:38px 34px 24px;background:#15372f;color:#f8f1df;border:5px solid #bd8730;display:flex;flex-direction:column;font-family:STSong,"Songti SC",SimSun,serif}
        .almanac-brand{display:flex;align-items:center;gap:14px}
        .almanac-seal{width:42px;height:42px;display:grid;place-items:center;border:2px solid #d5aa60;color:#efcc83;font-size:25px;font-weight:700}
        .almanac-brand strong{display:block;font-size:23px;letter-spacing:.08em;color:#fff8e8}
        .almanac-brand small{display:block;margin-top:2px;font:700 10px/1.2 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;letter-spacing:.18em;color:#e0e4d9}
        .almanac-hero{margin-top:126px}
        .almanac-date{font:700 12px/1.4 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;letter-spacing:.10em;color:#cf9231}
        .almanac-title{margin-top:18px}
        .almanac-title em{display:block;font-style:normal;font-size:44px;line-height:1;color:#fff9e9}
        .almanac-title strong{display:block;margin-top:10px;font-size:54px;line-height:1.12;color:#efca79;letter-spacing:.02em}
        .almanac-state{margin-top:22px;font-size:21px;line-height:1.3;color:#f7eed8}
        .almanac-summary{margin-top:6px;font-size:17px;line-height:1.45;color:#efca79}
        .almanac-ritual{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:auto}
        .almanac-ritual>div{min-height:58px;border:1px solid rgba(213,170,96,.65);padding:10px 12px}
        .almanac-ritual b{display:block;font:700 14px/1.2 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#f7f0df}
        .almanac-ritual span{display:block;margin-top:5px;font-size:14px;line-height:1.35;color:#efca79}
        .almanac-disclaimer{margin-top:10px;text-align:center;font:11px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:#b9c6bd}`;
    }

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
        .xhs-root>.sec,.xhs-root>.cover,.xhs-root>.xhs-almanac-cover{box-sizing:border-box!important;width:456px!important;margin:0!important}
        ${cardSpecificCss}
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
