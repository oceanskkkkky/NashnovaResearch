// 小红书发布助手：打开创作中心，扫码登录后上传 8 张卡片图 + 填标题/正文，暂停在发布前由用户确认
// 用法: node xhs-publish.js <imagesDir> <note.md> [profileDir]
const path = require('path');
const fs = require('fs');
const { chromium } = require(path.join(process.env.APPDATA, 'npm/node_modules/@playwright/cli/node_modules/playwright'));

(async () => {
  const [,, imagesDir, noteMd, profileDirArg] = process.argv;
  if (!imagesDir || !noteMd) { console.error('usage: node xhs-publish.js <imagesDir> <note.md> [profileDir]'); process.exit(1); }
  const profileDir = profileDirArg || path.join(__dirname, '..', '.workbuddy', 'xhs-profile');
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
      if (/^#\S+/.test(ln) && !/^#\s/.test(ln)) { tagsLine += (tagsLine ? ' ' : '') + ln.trim(); }
      else if (ln.trim()) { content += ln + '\n'; }
    }
  }
  content = content.trim();
  // 标签合并到正文末尾（XHS 在内容里识别 #）
  const fullBody = content + (tagsLine ? '\n\n' + tagsLine : '');

  const images = fs.readdirSync(imagesDir).filter(f => /\.(png|jpe?g)$/i.test(f)).map(f => path.join(imagesDir, f));
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
    await page.getByText('上传图文', { exact: true }).first().click({ timeout: 5000 });
    console.log('已切到「上传图文」tab');
    await page.waitForTimeout(2000);
  } catch (e) {
    console.warn('点击「上传图文」tab 失败：', e.message.split('\n')[0]);
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
        const isMultiple = await inp.evaluate(el => el.multiple);
        if (isMultiple) { fileInput = inp; console.log('选中多文件 input in frame:', f.url()?.slice(0,80)); break; }
      }
      if (fileInput) break;
    }
    if (!fileInput) {
      // 备选：单文件 input 用循环一张张设
      for (const f of page.frames()) {
        const inputs = await f.$$('input[type=file]');
        if (inputs.length) { fileInput = { __single: inputs[0], __allInputs: inputs }; break; }
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

  // 给用户看最终态，不自动点发布
  await page.screenshot({ path: path.join(imagesDir, '..', 'xhs-final.png'), fullPage: true });
  console.log('已截图最终态到 xhs-final.png。请在浏览器中检查并点击「发布」。');
  // 保持浏览器打开 10 分钟供用户检查与发布
  await page.waitForTimeout(600000);
  await ctx.close();
})();
