# -*- coding: utf-8 -*-
"""小红书发布 v2：两阶段。
用法：
  python xhs_publish2.py fill     # 上传+填表+存草稿
  python xhs_publish2.py publish  # 打开草稿箱->诊断发布按钮DOM->点击发布
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
DRAFTS_URL = "https://creator.xiaohongshu.com/publish/web/drafts"
DOM_LOG = OUT / "xhs-dom.log"


def log(msg: str) -> None:
    print(f"[xhs] {msg}", flush=True)


def dump_publish_dom(page, label: str) -> None:
    info = page.evaluate(
        """() => {
            const out = [];
            const walk = document.querySelectorAll('button,div,span,a,li');
            for (const el of walk) {
                const t = (el.textContent || '').trim();
                if (!t || t.length > 12) continue;
                if (t.includes('发布') || t.includes('暂存')) {
                    out.push({
                        tag: el.tagName, cls: String(el.className).slice(0, 120),
                        text: t, disabled: el.disabled === true || el.getAttribute('disabled') !== null
                            || el.getAttribute('aria-disabled') === 'true',
                        html: el.outerHTML.slice(0, 400),
                    });
                }
                if (out.length >= 14) break;
            }
            return out;
        }"""
    )
    with open(DOM_LOG, "a", encoding="utf-8") as f:
        f.write(f"===== {label} =====\n")
        for i, it in enumerate(info):
            f.write(f"[{i}] <{it['tag']}> text={it['text']!r} disabled={it['disabled']} class={it['cls']}\n")
            f.write(f"    html={it['html']}\n")
    log(f"DOM dumped ({label}): {len(info)} items -> {DOM_LOG.name}")


def launch(pw):
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE),
        headless=False,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def fill(pw) -> int:
    images = sorted(IMG_DIR.glob("*.png"))
    log(f"图片 {len(images)} 张")
    context, page = launch(pw)
    page.goto(PUBLISH_URL)
    page.wait_for_timeout(4000)
    if "login" in page.url or page.locator("text=扫码登录").count() > 0:
        log("NEED_LOGIN: 请在浏览器中扫码登录")
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
        log("tab click skipped")

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
        CONTENT["body"],
    )
    page.wait_for_timeout(1000)
    log(f"标题({len(CONTENT['title'])}字) 正文({len(CONTENT['body'])}字) 已填")

    dump_publish_dom(page, "after-fill")
    page.screenshot(path=str(OUT / "xhs-filled.png"))

    # 等合规检查完成 + hover 发布笔记按钮展开下拉菜单（不再自动点击）
    log("等待6秒让合规检查完成…")
    page.wait_for_timeout(6000)
    try:
        page.evaluate(
            """() => {
                const btn = document.querySelector('.btn-wrapper .btn-inner');
                if (btn) {
                    const r = btn.getBoundingClientRect();
                    const evt = new MouseEvent('mouseover', {bubbles: true, clientX: r.x+10, clientY: r.y+10});
                    btn.dispatchEvent(evt);
                    const evt2 = new MouseEvent('mouseenter', {bubbles: true, clientX: r.x+10, clientY: r.y+10});
                    btn.dispatchEvent(evt2);
                }
            }"""
        )
        # 用真实的 mouse 移动触发悬浮
        try:
            page.locator(".btn-wrapper .btn-inner").first.hover(timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
    except Exception as e:
        log(f"hover 异常: {e!r}")
    dump_publish_dom(page, "after-hover")
    page.screenshot(path=str(OUT / "xhs-dropdown.png"))
    log("下拉菜单截图: outputs/xhs-dropdown.png")
    log("浏览器窗口保持打开，请在弹出菜单中点击「立即发布」/「发布」等项；如需草稿也请在页面操作")
    log("完成或放弃后回复我，我会停止脚本并清理")

    # 保持进程不退出，浏览器窗口不被关闭；每60s打印心跳
    deadline = time.time() + 1800  # 30分钟
    while time.time() < deadline:
        page.wait_for_timeout(60000)
        log("heartbeat - 浏览器仍在等待手动发布")
    log("心跳超时，退出")
    sys.stdout.flush()
    os._exit(0)


def publish(pw) -> int:
    context, page = launch(pw)
    page.goto(DRAFTS_URL)
    page.wait_for_timeout(5000)
    if "login" in page.url:
        log("NEED_LOGIN: 请扫码")
        page.screenshot(path=str(OUT / "xhs-login.png"))
        deadline = time.time() + 300
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if "login" not in page.url:
                break
        page.goto(DRAFTS_URL)
        page.wait_for_timeout(5000)
    log(f"草稿页: {page.url}")
    page.screenshot(path=str(OUT / "xhs-drafts.png"))

    # 打开第一篇草稿
    try:
        first = page.locator(".draft-item, .note-item, li").first
        first.dblclick(timeout=10000)
        page.wait_for_timeout(5000)
    except Exception as e:
        log(f"打开草稿失败: {e!r}")
        dump_publish_dom(page, "drafts-list")
        page.screenshot(path=str(OUT / "xhs-result.png"))
        sys.stdout.flush()
        os._exit(2)
    log(f"草稿编辑页: {page.url}")
    dump_publish_dom(page, "draft-edit")
    page.screenshot(path=str(OUT / "xhs-draft-edit.png"))

    # hover 红色发布按钮，展开下拉
    try:
        trigger = page.locator("text=发布笔记").first
        trigger.hover(timeout=8000)
        page.wait_for_timeout(1200)
        dump_publish_dom(page, "after-hover")
        page.screenshot(path=str(OUT / "xhs-dropdown.png"))
    except Exception as e:
        log(f"hover 失败: {e!r}")

    # 尝试点击下拉项「发布」或按钮本体
    clicked = False
    for sel in ["text=发布 >> nth=0", "button:has-text('发布')", "text=直接发布"]:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(force=True, timeout=6000)
            log(f"已点击 {sel}")
            clicked = True
            break
        except Exception as e:
            log(f"click {sel} 失败: {e!r}")
    if not clicked:
        log("自动点击未成功，保留窗口供手动处理")
        page.screenshot(path=str(OUT / "xhs-result.png"))
        sys.stdout.flush()
        os._exit(2)

    page.wait_for_timeout(8000)
    page.screenshot(path=str(OUT / "xhs-result.png"))
    log(f"PUBLISH RESULT URL={page.url}")
    sys.stdout.flush()
    os._exit(0)


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "fill"
    if DOM_LOG.exists():
        try:
            DOM_LOG.write_text("", encoding="utf-8")
        except OSError:
            pass
    pw = sync_playwright().start()
    if phase == "fill":
        return fill(pw)
    return publish(pw)


if __name__ == "__main__":
    sys.exit(main())
