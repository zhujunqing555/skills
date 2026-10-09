---
name: zjq-drawio-tools
description: "ZJQ_draw.io_Tools：检查和修复 draw.io 文件兼容性、保留多页内容、局部修改原生对象、把嵌入位图压缩为 JPG/PNG，并通过 Desktop 导出真实预览。适合文件过大、别人打不开、合回当前页快照等任务；整体美化用 zjq-drawio。"
license: MIT
metadata:
  version: "1.0.0"
---

# ZJQ_draw.io_Tools

面向文件本身的检查、压缩、局部修改和多页保留。默认另写新文件，保留原文件。通过内容识别 XML，而不是仅看扩展名；支持未压缩模型、压缩 diagram 和多页 mxfile。

## 先检查再处理

```text
python scripts/drawio_file.py inspect INPUT
```

报告页数、顶点/边、独立文字、嵌入图片类型与大小、重复 id 和失效引用。不要把所有“别人打不开”都归因于文件大小；还要看 XML、图片编码、外链图源、软件版本和结构错误。检查本身不修改文件，也不下载外链图片。

## 图片压缩

```text
python scripts/drawio_file.py compress INPUT OUTPUT --quality 90
python scripts/drawio_file.py compress INPUT OUTPUT --quality 90 --flatten-alpha --background '#FFFFFF'
```

脚本仅处理嵌入位图，非图片对象与版式必须保持一致。默认保留有透明度的 PNG，避免白底破坏；用户明确要求所有位图转 JPG 时使用 `--flatten-alpha` 并说明透明度会被所选底色替代。按用户任务调整底色。

默认保留像素尺寸；`--max-side` 才会降采样。不因压缩任务把矢量 SVG、可编辑文字或整张流程图栅格化。动画图默认保留并报告。若 JPG 更大，保留原编码，除非用户明确要求强制 JPG。

写出后重新解析、核对非图片结构签名和页数，报告原/新字节大小、处理与保留图片。不能把“文件变小”当成“别人一定能打开”的证明，必要时用实际 draw.io 重新打开和导出。

## 多页与局部修改

单页桌面快照合回完整文件：

```text
python scripts/drawio_file.py merge-page ORIGINAL SNAPSHOT OUTPUT --page-id ORIGINAL_PAGE_ID
```

必须先 inspect 确认目标页 id；保留该页名称、其他页和文档元数据。不能用快照的 `live-page` 猜测应替换原文件哪一页。

仅改明确对象的文字、样式或几何：

```text
python scripts/drawio_file.py patch INPUT PATCHES.json OUTPUT --page-id PAGE_ID
```

补丁示例与数据限制见 [文件工具参考](references/file-operations.md)。不自动“修复”无法确定科学含义的连接方向；不删掉未知对象来消除报错。

## 真实导出与交付

```text
python scripts/drawio_file.py export INPUT OUTPUT.png --drawio /path/to/draw.io --width 2000
```

支持 PNG/SVG/PDF/JPG，使用实际 draw.io Desktop。`--page-index` 为零开始的导出页。导出后检查文件存在、非空，并目视核对可读性与连线；没有 Desktop 时报告限制，不以自制近似预览冒充实际结果。

对压缩、补丁或合页任务，核验应通过后再交付新 `.drawio` 与真实预览；说明未解决的结构问题。包内测试只用合成图，不发布用户研究图。

## 依赖

Python 3.10+。inspect、patch、merge-page 使用标准库；compress 需要 Pillow（见 `requirements.txt`）。运行时用正确解释器，不因缺一个包而顺便重建用户 Python 环境。源码、报告和输出分开放，不把临时报告写入技能安装目录。
