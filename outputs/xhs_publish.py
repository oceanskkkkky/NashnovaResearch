# -*- coding: utf-8 -*-
"""小红书图文发布脚本（Playwright 持久化登录态）。

策略：避免 page.close()/with 退出的原生崩溃；所有阶段完成后 os._exit 强退。
哨兵文件 outputs/xhs-confirm.txt 内容：publish 或 draft。
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
PROFILE = ROOT / ".workbuddy/xhs-profile"
CONFIRM_FILE = OUT / "xhs-confirm.txt"
CONTENT = json.loads((OUT / "xhs-content.json").read_text(encoding="utf-8"))
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official&target=image"


def log(msg: str) -> None:
    print(f"[xhs] {msg}", flush=True)


def wait_confirm(timeout_s: int = 900) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if CONFIRM_FILE.exists():
            v = CONFIRM_FILE.read_text(encoding="utf-8").strip().lower()
            if v in ("publish", "draft"):
                return v
        time.sleep(2)
    return "timeout"


def main() -> int:
    images = sorted(IMG_DIR.glob("*.png"))
    if not images:
        log("ERROR: 没有找到图片素材")
        return 2
    log(f"图片 {len(images)} 张")
    if CONFIRM_FILE.exists():
        CONFIRM_FILE.unlink()

    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE),
        headless=False,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.new_page() if not context.pages else context.pages[0]
    page.goto(PUBLISH_URL)
    page.wait_for_timeout(4000)

    if "login" in page.url or page.locator("text=扫码登录").count() > 0 or page.locator(".login-container").count() > 0:
        log("NEED_LOGIN: 未登录，请在浏览器中扫码登录")
        page.screenshot(path=str(OUT / "xhs-login.png"))
        deadline = time.time() + 300
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if "login" not in page.url and page.locator("text=扫码登录").count() == 0:
                break
        log("登录完成")
        page.goto(PUBLISH_URL)
        page.wait_for_timeout(4000)
    log(f"当前页面: {page.url}")

    tab = page.locator("text=上传图文")
    if tab.count() > 0:
        try:
            tab.first.click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception as e:
            log(f"tab click skipped: {e!r}; 继续上传")
            page.evaluate("""() => {
                const el = [...document.querySelectorAll('span,div')].find(n => n.textContent.trim() === '上传图文');
                if (el) el.click();
            }""")
            page.wait_for_timeout(1000)

    file_input = page.locator("input[type='file']").first
    file_input.set_input_files([str(p) for p in images])
    log("图片上传中…")
    page.wait_for_timeout(6000)

    title = CONTENT["title"]
    page.evaluate(
        """(t) => {
            const el = document.querySelector('input[placeholder*="标题"]');
            if (el) { el.value = t; el.dispatchEvent(new Event('input', {bubbles: true})); }
        }""",
        title,
    )
    log(f"标题已填({len(title)}字)")

    body = CONTENT["body"]
    editor = page.locator(".tiptap.ProseMirror, .ql-editor").first
    editor.click()
    page.wait_for_timeout(600)
    page.evaluate(
        """(text) => {
            const paras = text.split('\\n');
            const html = paras.map(p => p.trim() ? '<p>' + p + '</p>' : '<p><br></p>').join('');
            const ed = document.querySelector('.tiptap.ProseMirror') || document.querySelector('.ql-editor');
            if (ed) { ed.focus(); ed.innerHTML = html; ed.dispatchEvent(new Event('input', {bubbles: true})); }
        }""",
        body,
    )
    page.wait_for_timeout(1000)
    log(f"正文已填({len(body)}字)")

    page.screenshot(path=str(OUT / "xhs-filled.png"))
    log("SCREENSHOT_READY: outputs/xhs-filled.png")
    log("WAITING_CONFIRM: 用户写入 outputs/xhs-confirm.txt (publish/draft)")

    action = wait_confirm()
    if action == "timeout":
        log("超时未确认，保留页面（不发布）")
        sys.stdout.flush()
        os._exit(3)

    if action == "publish":
        btn = page.locator("button:has-text('发布')").first
        btn.click()
        log("已点击发布，等待结果…")
        page.wait_for_timeout(6000)
        page.screenshot(path=str(OUT / "xhs-result.png"))
        log(f"PUBLISHED? URL={page.url}")
    else:
        btn = page.locator("button:has-text('暂存离开'), text=暂存离开").first
        btn.click()
        log("已点击暂存离开")
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUT / "xhs-result.png"))
        log(f"DRAFT_SAVED? URL={page.url}")

    sys.stdout.flush()
    os._exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
