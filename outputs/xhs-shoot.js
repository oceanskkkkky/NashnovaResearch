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
  const zeroRecommendation = await sourcePage.locator('#picks').evaluate(el =>
    /零推荐|不建立个股推荐榜|不建立推荐榜/.test(el.textContent || '')
  );

  const shots = [
    { name: '01-cover', selectors: ['#cover'], variant: 'cover' },
    {
      name: '02-market-overview',
      selectors: ['#executive-summary', '#macro', '#market'],
      variant: 'market-overview',
    },
    { name: '03-sectors', selectors: ['#sectors'], variant: 'sectors' },
  ];

  if (zeroRecommendation) {
    const decisionSelectors = ['#picks', '#risks'];
    if (await sourcePage.locator('#caveats').count()) {
      decisionSelectors.push('#caveats');
    }
    shots.push({
      name: '04-decision-risks',
      selectors: decisionSelectors,
      variant: 'decision-risks',
    });
  } else {
    shots.push(
      { name: '04-picks', selectors: ['#picks'], variant: 'picks' },
      { name: '05-risks', selectors: ['#risks'], variant: 'risks' },
    );
  }

  const staleImagePattern = /^\d{2}-(cover|summary|macro|market|market-overview|sectors|pick|picks|risks|decision-risks)\.png$/;
  for (const file of fs.readdirSync(outDir)) {
    if (staleImagePattern.test(file)) {
      fs.unlinkSync(path.join(outDir, file));
    }
  }

  for (const { name, selectors, variant } of shots) {
    const fragments = [];
    for (const selector of selectors) {
      const source = sourcePage.locator(selector).first();
      if (await source.count() === 0) {
        console.error('FAIL', name, 'selector not found:', selector);
        continue;
      }
      fragments.push(await source.evaluate(el => el.outerHTML));
    }
    if (fragments.length !== selectors.length) {
      continue;
    }

    const isComposite = fragments.length > 1;
    let outerHtml = isComposite
      ? `<article class="xhs-composite xhs-${variant}">${fragments.join('')}</article>`
      : fragments[0];
    let cardSpecificCss = variant === 'cover' ? '' : `
      .xhs-stage{align-items:flex-start!important}
      .xhs-root{align-items:flex-start!important}
      .xhs-root>.sec{margin:0!important;padding:20px 22px!important;border-top:4px solid #b98532!important;box-shadow:0 8px 24px rgba(24,51,45,.06)}
      .xhs-root>.sec h2{margin:4px 0 12px!important;font-size:29px!important;line-height:1.2!important}
      .xhs-root>.sec .line,.xhs-root>.sec .kv{font-size:16px!important;line-height:1.5!important}
      .xhs-composite{width:456px;display:flex;flex-direction:column;gap:10px}
      .xhs-composite>.sec{width:456px!important;margin:0!important;padding:16px 20px!important;border:1px solid #e1d9ca!important;background:#fffdf7!important}
      .xhs-composite>.sec h2{margin:2px 0 9px!important;font-size:25px!important;line-height:1.18!important}
      .xhs-composite>.sec .kicker{font-size:10px!important}
    `;

    if (variant === 'market-overview') {
      cardSpecificCss += `
        .xhs-market-overview{gap:8px}
        .xhs-market-overview #executive-summary{border-top:4px solid #b98532!important}
        .xhs-market-overview #executive-summary .line{padding:5px 0!important}
        .xhs-market-overview #executive-summary>p{margin:10px 0 0!important;padding:9px 12px;background:#18332d;color:#fff8e8;font-size:13px;line-height:1.45}
        .xhs-market-overview #macro{display:grid;grid-template-columns:1fr 1fr;column-gap:12px}
        .xhs-market-overview #macro .kicker,.xhs-market-overview #macro h2{grid-column:1/-1}
        .xhs-market-overview #macro .kv{display:block;margin:0;padding:9px 10px!important;background:#faf5e9;border:1px solid #e1d9ca!important}
        .xhs-market-overview #macro .kv .k{display:block;margin-bottom:4px;color:#18332d;font-weight:700}
        .xhs-market-overview #market .line{padding:5px 0!important}
        .xhs-market-overview #market>p{margin:9px 0 0!important;padding:10px 12px;background:#f4efe2;border-left:4px solid #b98532;font-size:14px;line-height:1.55}`;
    }

    if (variant === 'decision-risks') {
      cardSpecificCss += `
        .xhs-decision-risks{gap:10px}
        .xhs-decision-risks #picks{border-top:4px solid #b98532!important}
        .xhs-decision-risks #picks .stock{margin-top:0!important;padding-top:8px!important}
        .xhs-decision-risks #picks .stock h3{margin:0 0 8px!important;padding:10px 12px;background:#18332d;color:#fff8e8;font-size:22px!important;line-height:1.3}
        .xhs-decision-risks #picks .stock p{margin:6px 0!important;font-size:15px;line-height:1.55}
        .xhs-decision-risks #risks{border-left:4px solid #a83e32!important}
        .xhs-decision-risks #risks ul{margin:0!important;padding-left:20px!important}
        .xhs-decision-risks #risks li{margin:0 0 5px!important;font-size:14px;line-height:1.48}
        .xhs-decision-risks #risks>p{margin:9px 0 0!important;padding:9px 11px;background:#f4efe2;font-size:12px;line-height:1.45}
        .xhs-decision-risks #caveats .kicker,.xhs-decision-risks #caveats h2{color:var(--m-ink)}
        .xhs-decision-risks #caveats .kv{margin:0!important;padding:8px 10px!important;background:#faf5e9;border:1px solid #e1d9ca;display:block}
        .xhs-decision-risks #caveats .kv .k{display:block;margin-bottom:3px;color:#18332d;font-weight:700;font-size:13px}
        .xhs-decision-risks #caveats .kv{font-size:13px;line-height:1.5;margin-bottom:6px!important}
        .xhs-decision-risks #caveats>p{margin:6px 0 0!important;font-size:11px;line-height:1.45}
        .xhs-decision-risks #caveats>h2{font-size:24px!important;margin:2px 0 8px!important}`;
    }

    if (name === '01-cover') {
      const coverSource = sourcePage.locator(selectors[0]).first();
      const cover = await coverSource.evaluate(el => {
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
        .xhs-root{display:flex;align-items:center;justify-content:center;transform-origin:top center}
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
