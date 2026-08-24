# -*- coding: utf-8 -*-
"""小红书发布 v3：填充 -> 等待底部发布栏渲染 -> DOM定位「发布」并自动点击。
失败则保持窗口+周期性截图供人工处理。
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
    print(f"[xhs3] {msg}", flush=True)


def dump_all(page, label: str) -> None:
    info = page.evaluate(
        """() => {
            const out = [];
            const els = [...document.querySelectorAll('div,span,button,a')];
            for (const el of els) {
                const t = (el.textContent || '').trim();
                if (t === '发布' || t === '暂存离开' || t === '立即发布' || t === '确认发布') {
                    const r = el.getBoundingClientRect();
                    out.push({tag: el.tagName, cls: String(el.className).slice(0, 100),
                              text: t, x: Math.round(r.x), y: Math.round(r.y),
                              w: Math.round(r.width), h: Math.round(r.height),
                              vis: r.width > 0 && r.height > 0,
                              html: el.outerHTML.slice(0, 260)});
                }
            }
            return out;
        }"""
    )
    with open(DOM_LOG, "a", encoding="utf-8") as f:
        f.write(f"===== {label} =====\n")
        for i, it in enumerate(info):
            f.write(f"[{i}] <{it['tag']}> text={it['text']!r} vis={it['vis']} pos=({it['x']},{it['y']}) {it['w']}x{it['h']} cls={it['cls']}\n")
            f.write(f"    {it['html']}\n")
    log(f"dump({label}) 匹配 {len(info)} 项")


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
        log("NEED_LOGIN: 请扫码")
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
    page.screenshot(path=str(OUT / "xhs-filled.png"))

    # 等待底部发布栏渲染（图片处理+合规检查）
    for i in range(5):
        page.wait_for_timeout(4000)
        dump_all(page, f"wait-{i}")
        if page.evaluate(
            """() => [...document.querySelectorAll('div,span,button,a')].some(
                    el => el.textContent.trim() === '发布')"""
        ):
            log(f"检测到「发布」按钮 (第{i+1}轮)")
            break

    page.screenshot(path=str(OUT / "xhs-before-publish.png"))

    # 定位并点击真正的「发布」（排除顶部分发笔记导航）
    clicked = page.evaluate(
        """() => {
            const all = [...document.querySelectorAll('div,span,button,a')]
                .filter(el => el.textContent.trim() === '发布');
            // 取 y 最大的（底部栏），且非顶部导航
            all.sort((a, b) => {
                const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
                return (rb.y + rb.height) - (ra.y + ra.height);
            });
            if (!all.length) return 'not-found';
            const target = all[all.length - 1];
            const r = target.getBoundingClientRect();
            target.click();
            return `clicked y=${Math.round(r.y)} tag=${target.tagName} cls=${target.className}`;
        }"""
    )
    log(f"点击结果: {clicked}")
    page.wait_for_timeout(5000)
    dump_all(page, "after-click")
    page.screenshot(path=str(OUT / "xhs-result.png"))
    log(f"RESULT URL={page.url}")

    # 保持窗口 + 每20s截图供检查
    deadline = time.time() + 1200
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
