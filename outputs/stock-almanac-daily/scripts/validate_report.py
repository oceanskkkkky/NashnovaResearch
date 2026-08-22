#!/usr/bin/env python3
"""静态校验A股选股日报的结构、安全性、桌面布局与阅读预算。"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_IDS = {
    "cover",
    "executive-summary",
    "macro",
    "market",
    "sectors",
    "picks",
    "risks",
    "evidence",
    "methodology",
}
FORBIDDEN_TERMS = {
    "必涨",
    "稳赚",
    "抄底机会",
    "最佳买点",
    "最佳卖点",
    "保证收益",
    "明日一定",
    "官方恐慌贪婪指数",
    "ETF",
}
REMOTE_URL = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
STYLE_REMOTE_URL = re.compile(r"url\(\s*[\"']?(?:https?:)?//", re.IGNORECASE)
MOBILE_MEDIA = re.compile(r"@media\s*\([^)]*max-width", re.IGNORECASE)


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.id_order: list[str] = []
        self.details_depth = 0
        self.summary_depth = 0
        self.skip_depth = 0
        self.style_depth = 0
        self.visible_text: list[str] = []
        self.all_text: list[str] = []
        self.open_details: list[str] = []
        self.remote_resources: list[str] = []
        self.has_script = False
        self.style_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        element_id = attr_map.get("id")
        if element_id:
            self.ids.add(element_id)
            self.id_order.append(element_id)
        if tag == "script":
            self.has_script = True
            self.skip_depth += 1
        elif tag == "style":
            self.skip_depth += 1
            self.style_depth += 1
        if tag == "details":
            self.details_depth += 1
            if "open" in attr_map:
                self.open_details.append(element_id or "<无id>")
        if tag == "summary":
            self.summary_depth += 1
        src = attr_map.get("src")
        href = attr_map.get("href") if tag == "link" else None
        for value in (src, href):
            if value and REMOTE_URL.match(value.strip()):
                self.remote_resources.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "style" and self.style_depth:
            self.style_depth -= 1
        if tag == "summary" and self.summary_depth:
            self.summary_depth -= 1
        if tag == "details" and self.details_depth:
            self.details_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            if self.style_depth:
                self.style_chunks.append(data)
            return
        text = " ".join(data.split())
        if not text:
            return
        self.all_text.append(text)
        if self.details_depth == 0 or self.summary_depth:
            self.visible_text.append(text)


def reading_units(text: str) -> int:
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    stripped = re.sub(r"[\u3400-\u9fff]", " ", text)
    words = len(re.findall(r"[A-Za-z0-9]+(?:[._%+-][A-Za-z0-9]+)*", stripped))
    return cjk + words


def main() -> int:
    parser = argparse.ArgumentParser(description="校验A股桌面端HTML选股日报")
    parser.add_argument("report", type=Path)
    parser.add_argument("--max-visible-units", type=int, default=3200)
    args = parser.parse_args()

    try:
        html = args.report.read_text(encoding="utf-8")
    except OSError as error:
        print(f"ERROR: 无法读取报告：{error}")
        return 2

    findings: list[str] = []
    lower = html.lower()
    if "<!doctype html>" not in lower:
        findings.append("缺少 <!doctype html>")
    if '<html lang="zh-cn"' not in lower and "<html lang='zh-cn'" not in lower:
        findings.append("缺少 lang=zh-CN")
    if "<meta charset=" not in lower:
        findings.append("缺少 charset")
    if "name=\"viewport\"" not in lower and "name='viewport'" not in lower:
        findings.append("缺少 viewport")
    for signature, label in (
        ('class="topbar"', "深墨绿页头"),
        ('class="seal"', "历字印章"),
        ("--ink:#18332d", "深墨绿设计令牌"),
        ("--gold:#b98532", "金色设计令牌"),
    ):
        if signature not in lower:
            findings.append("缺少交易老黄历视觉特征：" + label)

    report = ReportParser()
    report.feed(html)
    styles = "\n".join(report.style_chunks)
    if report.has_script:
        findings.append("检测到JavaScript；日报必须为无脚本静态HTML")
    if report.remote_resources:
        findings.append("检测到远程资源引用：" + ", ".join(report.remote_resources))
    if STYLE_REMOTE_URL.search(styles):
        findings.append("内联样式中检测到远程资源URL")
    if MOBILE_MEDIA.search(styles):
        findings.append("检测到移动端max-width响应式重排；本Skill要求桌面研报布局")

    missing_ids = sorted(REQUIRED_IDS - report.ids)
    if missing_ids:
        findings.append("缺少必需栏目id：" + ", ".join(missing_ids))
    if "macro" in report.ids and "market" in report.ids:
        if report.id_order.index("macro") > report.id_order.index("market"):
            findings.append("宏观大势必须位于大盘判断之前")
    if report.open_details:
        findings.append("details必须默认折叠：" + ", ".join(report.open_details))

    all_text = " ".join(report.all_text)
    bad_terms = sorted(term for term in FORBIDDEN_TERMS if term in all_text)
    if bad_terms:
        findings.append("包含禁用内容或措辞：" + ", ".join(bad_terms))
    almanac_count = all_text.count("老黄历")
    if almanac_count > 3:
        findings.append(f"老黄历包装出现{almanac_count}次，正文主题化过重")

    visible_units = reading_units(" ".join(report.visible_text))
    minutes = visible_units / 320
    if visible_units > args.max_visible_units:
        findings.append(
            f"首轮可见内容超出阅读预算：{visible_units}单位，约{minutes:.1f}分钟"
        )

    print(f"visible_units={visible_units}")
    print(f"estimated_minutes={minutes:.1f}")
    print(f"all_text_units={reading_units(all_text)}")
    print(f"almanac_mentions={almanac_count}")
    if findings:
        for item in findings:
            print(f"FAIL: {item}")
        return 1
    print("PASS: A股范围、桌面布局、静态安全与10分钟阅读预算检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
