# -*- coding: utf-8 -*-
"""小红书发布 v4：全自动。
填充 -> 轮询底部「发布」按钮（最长240s）-> 自动点击 -> 处理确认弹窗 -> 校验结果截图。
全程无需人工点击。
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
CONTENT = json.loads((OUT / "xhs-content.json").read_text(encoding="utf-8"))
PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official&target=image"
DOM_LOG = OUT / "xhs-dom.log"


def log(msg: str) -> None:
    print(f"[xhs4] {msg}", flush=True)


def find_publish(page):
    """返回底部「发布」按钮元素信息，找不到返回 None。"""
    return page.evaluate(
        """() => {
            const all = [...document.querySelectorAll('div,span,button,a')];
            const hits = all.filter(el => (el.textContent || '').trim() === '发布');
            // 排除顶部导航(发布笔记)已天然排除（文本不完全相等）；取最靠下的可见元素
            const vis = hits.filter(el => {
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
    log(f"图片 {len(images)} 张")
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE), headless=False,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(PUBLISH_URL)
    page.wait_for_timeout(4000)
    if "login" in page.url or page.locator("text=扫码登录").count() > 0:
        log("NEED_LOGIN: 请在弹出的浏览器中扫码登录")
        page.screenshot(path=str(OUT / "xhs-login.png"))
        deadline = time.time() + 300
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if "login" not in page.url and page.locator("text=扫码登录").count() == 0:
                break
        page.goto(PUBLISH_URL)
        page.wait_for_timeout(4000)
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

    # 轮询等待底部「发布」按钮渲染（图片处理+合规检查）
    found = None
    for i in range(48):  # 最长 48*5s=240s
        page.wait_for_timeout(5000)
        found = find_publish(page)
        if found:
            log(f"发现「发布」按钮: {found} (第{i+1}轮)")
            break
    if not found:
        log("240s内未出现「发布」按钮，保留窗口供人工处理")
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
            const t = vis[0];
            t.click();
            return 'clicked';
        }"""
    )
    log(f"点击「发布」: {clicked}")
    page.wait_for_timeout(4000)
    # 处理可能的确认弹窗
    page.evaluate(
        """() => {
            const cands = [...document.querySelectorAll('div,span,button')].filter(
                n => (n.textContent || '').trim() === '确认' || (n.textContent || '').trim() === '确认发布'
                     || (n.textContent || '').trim() === '确定');
            if (cands[0]) cands[0].click();
        }"""
    )
    page.wait_for_timeout(8000)
    page.screenshot(path=str(OUT / "xhs-result.png"))
    log(f"RESULT URL={page.url}")
    log("若 URL 已离开 /publish 或出现成功提示，则发布成功")

    # 保持窗口+周期截图
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
