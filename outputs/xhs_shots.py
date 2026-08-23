# -*- coding: utf-8 -*-
"""把股市老黄历移动端日报截屏为小红书图片素材。

封面为专用1080x1440设计稿，正文为移动端报告分区截屏（宽1080）。
输出目录：reports/stock-almanac/2026-08-23-xhs-images/
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(r"D:\UGit\nashnova")
REPORT = ROOT / "reports/stock-almanac/2026-08-23-stock-almanac-mobile.html"
COVER = ROOT / "outputs/xhs-cover.html"
OUT = ROOT / "reports/stock-almanac/2026-08-23-xhs-images"

# 分区截屏：文件名前缀 -> 元素选择器
SECTIONS = [
    ("02-summary", "#executive-summary"),
    ("03-macro", "#macro"),
    ("04-market", "#market"),
    ("05-sectors", "#sectors"),
    ("06-pick-zijin", "#picks .m-stock >> nth=0"),
    ("07-pick-zhongjin", "#picks .m-stock >> nth=1"),
    ("08-pick-shandong", "#picks .m-stock >> nth=2"),
    ("09-risks", "#risks"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # 封面：540x720 @2x = 1080x1440（3:4）
        page = browser.new_page(viewport={"width": 540, "height": 720}, device_scale_factor=2)
        page.goto(COVER.as_uri())
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "01-cover.png"))
        print("cover saved", flush=True)

        # 正文分区：540宽 @2x = 1080宽，自然高度
        page = browser.new_page(viewport={"width": 540, "height": 720}, device_scale_factor=2)
        page.goto(REPORT.as_uri())
        page.add_style_tag(content=".m-shell{max-width:540px}")
        page.wait_for_timeout(400)
        for name, selector in SECTIONS:
            locator = page.locator(selector)
            locator.scroll_into_view_if_needed()
            page.wait_for_timeout(150)
            locator.screenshot(path=str(OUT / f"{name}.png"))
            print("saved", name, flush=True)
    print("DONE", OUT, flush=True)
    # 本机 playwright 关闭阶段存在原生崩溃，所有文件已保存后直接退出进程
    sys.stdout.flush()
    os._exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
