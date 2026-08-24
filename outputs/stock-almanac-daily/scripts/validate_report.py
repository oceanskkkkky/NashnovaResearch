#!/usr/bin/env python3
"""静态校验A股选股日报的结构、安全性、布局与阅读预算。支持桌面端与移动端两种格式。"""

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
    "methodology",
}
BANNED_IDS = {
    "evidence": "产物不得包含证据区（id=evidence）；证据台账请存旁车 evidence 文件",
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
EVIDENCE_REF = re.compile(r"\[E\d{2}\]")
EMOJI_PATTERN = re.compile(
    "[\U0001f000-\U0001faff\u2600-\u27bf\u2b00-\u2bff\ufe0f]"
)

DESKTOP_SIGNATURES = (
    ('class="topbar"', "深墨绿页头"),
    ('class="seal"', "历字印章"),
    ("--ink:#18332d", "深墨绿设计令牌"),
    ("--gold:#b98532", "金色设计令牌"),
)
MOBILE_SIGNATURES = (
    ('class="m-shell"', "移动端骨架"),
    ('class="m-seal"', "移动端历字印章"),
    ("--m-ink:#18332d", "移动端深墨绿设计令牌"),
    ("--m-gold:#b98532", "移动端金色设计令牌"),
)


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
    parser = argparse.ArgumentParser(description="校验A股HTML选股日报（桌面端/移动端）")
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--format",
        choices=("desktop", "mobile"),
        default="desktop",
        help="产物格式：desktop 桌面研报（默认）或 mobile 竖屏卡片流",
    )
    parser.add_argument("--max-visible-units", type=int, default=None)
    args = parser.parse_args()

    is_mobile = args.format == "mobile"
    if args.max_visible_units is None:
        args.max_visible_units = 1500 if is_mobile else 3200

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
    signatures = MOBILE_SIGNATURES if is_mobile else DESKTOP_SIGNATURES
    for signature, label in signatures:
        if signature not in lower:
            findings.append("缺少交易老黄历视觉特征：" + label)
    if is_mobile and "min-width:1268px" in lower:
        findings.append("移动端产物不得保留桌面端1268px最小宽度")

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
        findings.append("检测到max-width响应式重排；本Skill要求固定布局（桌面或移动端骨架）")

    missing_ids = sorted(REQUIRED_IDS - report.ids)
    if missing_ids:
        findings.append("缺少必需栏目id：" + ", ".join(missing_ids))
    banned_ids = sorted(BANNED_IDS.keys() & report.ids)
    for banned in banned_ids:
        findings.append(BANNED_IDS[banned])
    if "macro" in report.ids and "market" in report.ids:
        if report.id_order.index("macro") > report.id_order.index("market"):
            findings.append("宏观大势必须位于大盘判断之前")
    if report.open_details:
        findings.append("details必须默认折叠：" + ", ".join(report.open_details))

    all_text = " ".join(report.all_text)
    bad_terms = sorted(term for term in FORBIDDEN_TERMS if term in all_text)
    if bad_terms:
        findings.append("包含禁用内容或措辞：" + ", ".join(bad_terms))
    if EVIDENCE_REF.search(all_text):
        findings.append("产物正文不得出现 [E01] 等证据编号；证据台账请存旁车 evidence 文件")
    almanac_count = all_text.count("老黄历")
    if almanac_count > 3:
        findings.append(f"老黄历包装出现{almanac_count}次，正文主题化过重")
    emoji_count = len(EMOJI_PATTERN.findall(all_text))
    emoji_limit = 15 if is_mobile else 0
    if emoji_count > emoji_limit:
        findings.append(f"emoji出现{emoji_count}次，超出{args.format}格式上限{emoji_limit}")

    visible_units = reading_units(" ".join(report.visible_text))
    minutes = visible_units / 320
    if visible_units > args.max_visible_units:
        findings.append(
            f"首轮可见内容超出阅读预算：{visible_units}单位，约{minutes:.1f}分钟"
        )

    print(f"format={args.format}")
    print(f"visible_units={visible_units}")
    print(f"estimated_minutes={minutes:.1f}")
    print(f"all_text_units={reading_units(all_text)}")
    print(f"almanac_mentions={almanac_count}")
    print(f"emoji_count={emoji_count}")
    if findings:
        for item in findings:
            print(f"FAIL: {item}")
        return 1
    label = "移动端竖屏卡片流" if is_mobile else "桌面布局"
    print(f"PASS: A股范围、{label}、静态安全与阅读预算检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
