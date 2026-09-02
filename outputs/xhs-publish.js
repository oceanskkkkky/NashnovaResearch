#!/usr/bin/env node
"use strict";

// Legacy entry point intentionally disabled.
// The stock-almanac workflow may prepare local images and copy-ready text only.
// It must never open, inspect, log in to, upload to, or fill any Xiaohongshu page.

const fs = require("fs");
const path = require("path");

const [, , imagesDir, noteMd] = process.argv;

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exitCode = 2;
}

if (!imagesDir || !noteMd) {
  fail("用法: node xhs-publish.js <imagesDir> <note.md>");
} else {
  const resolvedImagesDir = path.resolve(imagesDir);
  const resolvedNoteMd = path.resolve(noteMd);
  const images = fs.existsSync(resolvedImagesDir)
    ? fs.readdirSync(resolvedImagesDir)
        .filter((name) => /\.(png|jpe?g)$/i.test(name))
        .sort()
        .map((name) => path.join(resolvedImagesDir, name))
    : [];

  if (!fs.existsSync(resolvedNoteMd)) {
    fail(`未找到文案文件: ${resolvedNoteMd}`);
  } else if (images.length === 0) {
    fail(`未找到配图: ${resolvedImagesDir}`);
  } else {
    const markdown = fs.readFileSync(resolvedNoteMd, "utf8");
    const title = markdown.split(/\r?\n/).find((line) => /^#\s+/.test(line));

    console.log("小红书网页自动化已永久停用；本脚本不会启动浏览器、访问平台、登录、上传、填充或发布。");
    console.log("");
    console.log("本地材料已就绪:");
    console.log(`- 标题: ${title ? title.replace(/^#\s+/, "").trim() : "请从文案首行复制"}`);
    console.log(`- 文案: ${resolvedNoteMd}`);
    console.log(`- 配图目录: ${resolvedImagesDir}`);
    images.forEach((image, index) => console.log(`  ${index + 1}. ${image}`));
    console.log("");
    console.log("请完全手动操作:");
    console.log("1. 自行打开小红书创作服务平台并登录。");
    console.log("2. 手动选择“发布笔记/上传图文”。");
    console.log("3. 按上述顺序手动上传全部配图。");
    console.log("4. 从文案文件复制标题、正文和话题标签，并手动粘贴。");
    console.log("5. 人工复核图片顺序、封面、标题、正文、话题与免责声明。");
    console.log("6. 确认无误后，由用户本人手动点击发布。");
  }
}
