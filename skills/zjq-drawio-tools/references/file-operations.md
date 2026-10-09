# 文件工具

所有写操作拒绝原路径和已存在的输出文件。报告默认放到输出旁的 `.report.json`，可以用 `--report` 指定。XML 含 DTD/ENTITY 或压缩页解码超过限制时停止；不会执行标签里的脚本，也不联网加载图源。

## inspect

`inspect INPUT --max-file-mib 256` 支持原生 XML 和 mxfile 的 raw-DEFLATE/base64/URL 编码页。重复 id、缺失 parent/source/target 都会列出；外链图片仅记录引用，不请求远程地址。

## patch

补丁是对象数组，每项有 id，可使用 `label`、`style_updates`、`geometry`。

```json
[
  {"id":"label-1","label":"候选作用轴"},
  {"id":"box-1","style_updates":{"fillColor":"#DAE8DE","strokeWidth":1.8}},
  {"id":"box-2","geometry":{"x":310,"y":160,"width":210,"height":310}}
]
```

`style_updates` 的 null 删除对应键；保留未修改的样式键。geometry 限定 x/y/width/height，宽高须正。补丁找不到 id、同一 id 重复、未知字段或有结构错误时停止，不部分写出。

说明：绑定连接器的 source/target 与 waypoint 不在这个简单补丁入口中改写。连线重路由优先使用桌面原生图接口并实际渲染核对。

## compress

默认质量 90，原尺寸；支持 PNG/JPEG/WebP/GIF 的静态嵌入图。透明图保留 PNG；`--flatten-alpha` 允许把透明区合到指定底色并编码为 JPEG。SVG 和其他格式保持原样并报告。

`--force-jpeg` 用于用户明确要求全部静态位图为 JPG，即使某一图片不变小；与 `--flatten-alpha` 组合可转透明位图。否则不会为了扩展名转换而增大单张图。

输入 URI 可含 `;base64`，也可为 draw.io 常见的 `data:image/png,BASE64`。写出时统一为 draw.io 原生的紧凑前缀，避免样式分号把 base64 载荷拆开。只替换图片载荷与相应前缀。除图片编码外，模型、文字、位置、边引用和页元数据签名相同才允许写出。

## merge-page

快照必须只有一页，原文档目标 id 必须唯一。目标页保留原名与 id，使用快照模型；其他页的模型签名保持不变。快照无法保留原页外部链接语义时，报告需进一步检查，不自动重新命名其科学标签。

## export

支持 `--drawio` 或环境变量 `DRAWIO_PATH`；无显式路径时在 PATH 与常见安装位置查找。PNG/JPG 默认宽 2000，SVG/PDF 不使用宽度参数。没有输出即失败，不按零退出码独自判定导出成功。

多页文件的页导出不意味着其他页已经被审查，正式交付要覆盖用户指定页面。

本工具的 `--page-index` 始终从 0 开始。Desktop CLI 自 27.0.2 起改用从 1 开始的页码；工具通过 `--version` 检测并映射，防止导错页。不能检测版本时停止并要求明确 `--cli-page-base`，不猜测页面。
