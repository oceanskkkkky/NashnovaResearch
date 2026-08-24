# -*- coding: utf-8 -*-
"""小红书发布 v5：驱动用户真实 Chrome + 真实登录态（channel=chrome + 真实 User Data）。
前提：用户已完全关闭自己的 Chrome。
流程：打开图文发布页 -> 上传9图 -> 填标题/正文 -> 轮询「发布」按钮 -> 点击 -> 校验截图。
"""
import json
import os
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(r"D:\UGit\nashnova")
OUT = ROOT / "outputs"
IMG_DIR = ROOT / "reports/stock-almanac/2026-08-23-xhs-images"
REAL_PROFILE = pathlib.Path(r"C:\Users\tizyt\AppData\Local\Google\Chrome\User Data")
CHROME_PATH = r"C:\Users\tizyt\AppData\Local\Google\Chrome\Application\chrome.exe"
CONTENT = json.loads((OUT / "xhs-content.json").read_text(encoding="utf-8"))
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official&target=image"
DOM_LOG = OUT / "xhs-dom.log"


def log(msg: str) -> None:
    print(f"[xhs5] {msg}", flush=True)


def find_publish(page):
    return page.evaluate(
        """() => {
            const all = [...document.querySelectorAll('div,span,button,a')];
            const vis = all.filter(el => {
                const t = (el.textContent || '').trim();
                if (t !== '发布') return false;
                const r = el.getBoundingClientRect();
                return r.width > 10 && r.height > 10 && r.y > 300;
            });
            if (!vis.length) return null;
            vis.sort((a, b) => b.getBoundingClientRect().y - a.getBoundingClientRect().y);
            const t = vis[0];
            const r = t.getBoundingClientRect();
            return {tag: t.tagName, y: Math.round(r.y), cls: String(t.className).slice(0, 80)};
        }"""
    )


def main() -> int:
    if DOM_LOG.exists():
        try:
            DOM_LOG.write_text("", encoding="utf-8")
        except OSError:
            pass
    images = sorted(IMG_DIR.glob("*.png"))
    log(f"图片 {len(images)} 张 | Chrome: {CHROME_PATH}")
    pw = sync_playwright().start()
    try:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(REAL_PROFILE),
            channel="chrome",
            executable_path=CHROME_PATH,
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        )
    except Exception as e:
        log(f"启动真实Chrome失败（确认Chrome已完全关闭）: {e!r}")
        sys.stdout.flush()
        os._exit(1)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(PUBLISH_URL)
    page.wait_for_timeout(5000)
    if "login" in page.url or page.locator("text=扫码登录").count() > 0:
        log("NEED_LOGIN: 请在浏览器中确认已登录")
        page.screenshot(path=str(OUT / "xhs-login.png"))
        deadline = time.time() + 300
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if "login" not in page.url and page.locator("text=扫码登录").count() == 0:
                break
        page.goto(PUBLISH_URL)
        page.wait_for_timeout(5000)
    log(f"页面: {page.url}")

    try:
        page.locator("text=上传图文").first.click(timeout=4000)
        page.wait_for_timeout(800)
    except Exception:
        log("tab skip")
    page.locator("input[type='file']").first.set_input_files([str(p) for p in images])
    log("图片上传中…")
    page.wait_for_timeout(8000)
    page.evaluate(
        """(t) => {
            const el = document.querySelector('input[placeholder*="标题"]');
            if (el) { el.value = t; el.dispatchEvent(new Event('input', {bubbles: true})); }
        }""",
        CONTENT["title"],
    )
    page.locator(".tiptap.ProseMirror, .ql-editor").first.click()
    page.wait_for_timeout(600)
    page.evaluate(
        """(text) => {
            const paras = text.split('\\n');
            const html = paras.map(p => p.trim() ? '<p>' + p + '</p>' : '<p><br></p>').join('');
            const ed = document.querySelector('.tiptap.ProseMirror') || document.querySelector('.ql-editor');
            if (ed) { ed.focus(); ed.innerHTML = html; ed.dispatchEvent(new Event('input', {bubbles: true})); }
        }""",
        CONTENT["body"],
    )
    log(f"标题({len(CONTENT['title'])}) 正文({len(CONTENT['body'])}) 已填")

    found = None
    for i in range(60):  # 最长 60*5s=300s
        page.wait_for_timeout(5000)
        found = find_publish(page)
        if found:
            log(f"发现「发布」按钮: {found} (第{i+1}轮)")
            break
    if not found:
        log("300s内未出现「发布」按钮，保留窗口")
        page.screenshot(path=str(OUT / "xhs-timeout.png"))
        sys.stdout.flush()
        os._exit(2)
    page.screenshot(path=str(OUT / "xhs-before-publish.png"))

    clicked = page.evaluate(
        """() => {
            const all = [...document.querySelectorAll('div,span,button,a')]
                .filter(el => (el.textContent || '').trim() === '发布');
            const vis = all.filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 10 && r.height > 10 && r.y > 300;
            });
            if (!vis.length) return 'not-found';
            vis.sort((a, b) => b.getBoundingClientRect().y - a.getBoundingClientRect().y);
            vis[0].click();
            return 'clicked';
        }"""
    )
    log(f"点击「发布」: {clicked}")
    page.wait_for_timeout(4000)
    page.evaluate(
        """() => {
            const cands = [...document.querySelectorAll('div,span,button')].filter(
                n => ['确认','确定','确认发布'].includes((n.textContent || '').trim()));
            if (cands[0]) cands[0].click();
        }"""
    )
    page.wait_for_timeout(10000)
    page.screenshot(path=str(OUT / "xhs-result.png"))
    log(f"RESULT URL={page.url}")

    deadline = time.time() + 900
    shot = 0
    while time.time() < deadline:
        page.wait_for_timeout(20000)
        shot += 1
        page.screenshot(path=str(OUT / f"xhs-live-{shot}.png"))
        log(f"live-{shot} URL={page.url}")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
