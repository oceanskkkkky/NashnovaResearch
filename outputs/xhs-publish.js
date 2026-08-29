// 小红书内容填充助手：打开创作中心，上传图片并填好标题/正文，停在发布前交由用户手动确认。
// 安全边界：永远不点击“发布”或任何二次确认控件，不判断发布成功。
// 用法: node xhs-publish.js <imagesDir> <note.md> [profileDir]
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const [,, imagesDir, noteMd, profileDirArg, ...extraArgs] = process.argv;
  if (!imagesDir || !noteMd) { console.error('usage: node xhs-publish.js <imagesDir> <note.md> [profileDir]'); process.exit(1); }
  const profileDir = profileDirArg || path.join(__dirname, '..', '.workbuddy', 'xhs-profile');
  if (extraArgs.includes('--publish')) {
    console.warn('警告：--publish 已永久停用。脚本只填充待发布内容，最终发布必须由用户手动完成。');
  }
  fs.mkdirSync(profileDir, { recursive: true });

  // 解析 note.md
  const md = fs.readFileSync(noteMd, 'utf8');
  const lines = md.split(/\r?\n/);
  let title = '', content = '', tagsLine = '';
  let inBody = false;
  for (const ln of lines) {
    if (/^#\s+/.test(ln) && !inBody) { title = ln.replace(/^#\s+/, '').trim(); continue; }
    if (!inBody && title && ln.trim() !== '') { inBody = true; }
    if (inBody) {
      if (/^#\S+/.test(ln) && !/^#\s/.test(ln)) {
        tagsLine += (tagsLine ? ' ' : '') + ln.trim();
      } else if (ln.trim()) {
        // 小红书编辑器不渲染 Markdown：将粗体分节标题和列表符号转为纯文本样式。
        const plainLine = ln
          .replace(/^\*\*(.+)\*\*$/, '【$1】')
          .replace(/^-\s+/, '• ');
        content += plainLine + '\n';
      }
    }
  }
  content = content.trim();
  // 标签合并到正文末尾（XHS 在内容里识别 #）
  const fullBody = content + (tagsLine ? '\n\n' + tagsLine : '');

  const images = fs.readdirSync(imagesDir).filter(f => /\.(png|jpe?g)$/i.test(f)).sort().map(f => path.join(imagesDir, f));
  console.log('标题:', title);
  console.log('正文长度:', fullBody.length, '图片:', images.length);

  const ctx = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = ctx.pages()[0] || await ctx.newPage();

  console.log('打开创作中心...');
  await page.goto('https://creator.xiaohongshu.com/publish/publish', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);
  await page.bringToFront().catch(() => {});
  if (page.url().includes('login')) {
    console.log('>>> 未登录：请在弹出的 Chromium 窗口（标题「小红书创作服务平台」）中用手机号验证码或扫码登录 <<<');
  }

  // 轮询等待登录完成：URL 脱离 /login 且出现上传入口（用户在弹出的窗口中扫码或短信登录）
  const deadline = Date.now() + 300000;
  let loggedIn = false;
  while (Date.now() < deadline) {
    const url = page.url();
    if (!url.includes('login')) {
      const hasUpload = await page.$('input[type=file]').catch(() => null);
      const bodyTxt = await page.evaluate(() => document.body.innerText.slice(0, 400)).catch(() => '');
      if (hasUpload || /上传|拖拽/.test(bodyTxt)) { loggedIn = true; break; }
    }
    process.stdout.write('.');
    await page.waitForTimeout(3000);
  }
  console.log('');
  if (!loggedIn) { console.error('等待登录超时（5分钟）'); await ctx.close(); process.exit(1); }
  console.log('已登录，进入发布页。');
  await page.bringToFront().catch(() => {});
  // 关键：默认停在「上传视频」tab，必须先切到「上传图文」tab
  await page.waitForTimeout(2000);
  try {
    const tabPoint = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll('.creator-tab, .title, div, span')];
      const candidates = nodes.filter(el => (el.textContent || '').trim() === '上传图文');
      for (const el of candidates) {
        const r = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        if (r.width > 0 && r.height > 0 && r.x >= 0 && r.y >= 0 && style.visibility !== 'hidden' && style.display !== 'none') {
          return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, cls: String(el.className || '') };
        }
      }
      return null;
    });
    if (!tabPoint) throw new Error('没有找到位于可视区域的上传图文标签');
    await page.mouse.click(tabPoint.x, tabPoint.y);
    console.log('已按页面坐标点击「上传图文」：', JSON.stringify(tabPoint));
    await page.waitForTimeout(2500);
    const imageInput = page.locator('input[type=file][accept*="image"], input[type=file][multiple]').first();
    const imageUploadText = page.getByText('上传图片', { exact: true }).first();
    if (!(await imageInput.count()) && !(await imageUploadText.count())) {
      throw new Error('切换后未检测到图片上传入口');
    }
    console.log('已切到「上传图文」tab');
  } catch (e) {
    console.error('点击「上传图文」tab失败：', e.message.split('\n')[0]);
    await page.screenshot({ path: path.join(imagesDir, '..', 'xhs-tab-switch-failed.png'), fullPage: true });
    await ctx.close();
    process.exit(1);
  }

  // 首选方案：点击「上传图片」按钮，拦截系统文件选择框（filechooser）注入全部图片
  // XHS 空白上传页的 file input 往往隐藏且绑定在按钮上，直接找 input 容易选错
  let uploaded = false;
  const uploadBtn = page.getByText('上传图片', { exact: true }).first();
  if (await uploadBtn.count()) {
    try {
      const [fc] = await Promise.all([
        page.waitForEvent('filechooser', { timeout: 10000 }),
        uploadBtn.click(),
      ]);
      await fc.setInputFiles(images);
      uploaded = true;
      console.log('已通过「上传图片」按钮提交', images.length, '张图片');
    } catch (e) {
      console.warn('filechooser 方案失败：', e.message.split('\n')[0], '，回退到 input 扫描');
    }
  }

  if (!uploaded) {
    // 回退方案：找支持多文件的 file input（XHS 可能有多个，优先 multiple；否则逐个尝试）
    let fileInput = null;
    for (const f of page.frames()) {
      const inputs = await f.$$('input[type=file]');
      for (const inp of inputs) {
        const meta = await inp.evaluate(el => ({ multiple: el.multiple, accept: el.accept || '' }));
        const acceptsImages = /image|\.jpe?g|\.png/i.test(meta.accept);
        if (meta.multiple && acceptsImages) { fileInput = inp; console.log('选中图片多文件 input in frame:', f.url()?.slice(0,80)); break; }
      }
      if (fileInput) break;
    }
    if (!fileInput) {
      // 备选：单文件 input 用循环一张张设
      for (const f of page.frames()) {
        const inputs = await f.$$('input[type=file]');
        for (const inp of inputs) {
          const accept = await inp.evaluate(el => el.accept || '');
          if (/image|\.jpe?g|\.png/i.test(accept)) { fileInput = { __single: inp, __allInputs: inputs }; break; }
        }
        if (fileInput) break;
      }
    }
    if (!fileInput) { console.error('找不到文件上传 input'); await page.screenshot({ path: path.join(imagesDir, '..', 'xhs-debug.png'), fullPage: true }); process.exit(1); }

    if (fileInput.__single) {
      console.log('仅找到单文件 input，逐张上传（', images.length, '张）...');
      for (const img of images) {
        await fileInput.__single.setInputFiles(img);
        await page.waitForTimeout(1500);
      }
    } else {
      await fileInput.setInputFiles(images);
    }
    console.log('已提交', images.length, '张图片');
  }
  // 等待进入编辑器（上传后页面会渲染标题输入框），最多等 30 秒
  const editorReady = await page.waitForFunction(() => {
    return !!document.querySelector('input[placeholder*="标题"], [contenteditable="true"], .ql-editor');
  }, { timeout: 30000 }).catch(() => null);
  console.log(editorReady ? '已进入编辑器，图片上传完成。' : '警告：30 秒内未检测到编辑器，可能上传失败。');
  await page.waitForTimeout(5000);
  await page.screenshot({ path: path.join(imagesDir, '..', 'xhs-after-upload.png'), fullPage: true });

  // 填标题（XHS 编辑器 class 动态，多候选 + 跨 iframe）
  const titleSelectors = [
    'input[placeholder*="标题"]', 'textarea[placeholder*="标题"]',
    'input[placeholder*="填写标题"]', 'textarea[placeholder*="填写标题"]',
    '#title', 'input[id*="title" i]', 'textarea[id*="title" i]',
    '[class*="title" i] input', '[class*="title" i] textarea',
  ];
  let titleFilled = false;
  for (let attempt = 0; attempt < 4 && !titleFilled; attempt++) {
    for (const f of page.frames()) {
      for (const sel of titleSelectors) {
        const el = await f.$(sel).catch(() => null);
        if (el) {
          try { await el.click({ timeout: 2000 }); await el.fill(title); console.log('已填标题 via', sel); titleFilled = true; break; } catch {}
        }
      }
      if (titleFilled) break;
    }
    if (!titleFilled) await page.waitForTimeout(2000);
  }
  if (!titleFilled) console.warn('未找到标题输入框（所有候选选择器，重试4次）');

  // 填正文（contenteditable 多候选 + 跨 iframe，用 insertText 更稳）
  const editorSelectors = [
    '[contenteditable="true"]', '.ql-editor',
    '[class*="editor" i] [contenteditable]', '[data-placeholder]',
  ];
  let bodyFilled = false;
  for (let attempt = 0; attempt < 4 && !bodyFilled; attempt++) {
    for (const f of page.frames()) {
      for (const sel of editorSelectors) {
        const el = await f.$(sel).catch(() => null);
        if (el) {
          try {
            await el.click({ timeout: 2000 });
            await page.keyboard.insertText(fullBody);
            console.log('已填正文 via', sel); bodyFilled = true; break;
          } catch {}
        }
      }
      if (bodyFilled) break;
    }
    if (!bodyFilled) await page.waitForTimeout(2000);
  }
  if (!bodyFilled) console.warn('未找到正文编辑器（所有候选选择器，重试4次）');

  // 保存发布前最终态，便于复核标题、正文和图片顺序
  const finalShot = path.join(imagesDir, '..', 'xhs-final.png');
  await page.screenshot({ path: finalShot, fullPage: true });
  console.log('已截图发布前最终态到', finalShot);

  if (!titleFilled || !bodyFilled || images.length === 0) {
    console.error('标题、正文或图片未完整填入，无法交付人工发布。');
    await ctx.close();
    process.exit(1);
  }

  console.log('内容已填充完毕，浏览器停留在发布前页面。');
  console.log('请人工复核图片顺序、标题、正文和声明，然后由用户本人点击「发布」。');
  console.log('脚本不会定位、点击或触发任何发布/确认控件；关闭浏览器窗口后脚本结束。');

  await new Promise(resolve => ctx.once('close', resolve));
})();
