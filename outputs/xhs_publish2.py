# -*- coding: utf-8 -*-
"""已停用：小红书网页自动化不再允许。

本文件仅保留为历史入口的安全占位符，不会启动浏览器、访问平台、上传、填充或发布。
请使用日报生成流程产出的本地图片和文案，完全手动登录小红书并发布。
"""

import sys


MESSAGE = """小红书自动化脚本已永久停用。
请完全手动操作：
1. 打开小红书创作服务平台并登录；
2. 手动进入图文发布；
3. 按文件名顺序上传 reports/stock-almanac/<日期>-xhs-images/ 中的图片；
4. 从 reports/stock-almanac/<日期>-xiaohongshu-note.md 复制标题、正文和话题；
5. 人工复核图片顺序、封面、免责声明和合规措辞；
6. 由用户本人手动点击发布。
"""


def main() -> int:
    print(MESSAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
