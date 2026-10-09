# 桌面接入与实际工作流

## 依赖与配置

主后端是 [Scientific Illustrator](https://github.com/icebird1998/scientific-illustrator)，验证基线 v1.5.4，Node.js 22+，已安装 draw.io Desktop。本技能不含上游服务的副本，也不会自动注册新插件。

宿主有原生工具时直接调用。脚本查找顺序：环境变量 `SCIENTIFIC_ILLUSTRATOR_PLUGIN` → 本地配置 `pluginDir` → Codex 插件缓存中最新可识别版本。配置文件默认在 `$CODEX_HOME/zjq-drawio/config.json`，没有 CODEX_HOME 时为 `~/.codex/zjq-drawio/config.json`。

配置示例（替换成本机路径；不要把真实本机配置发布到 GitHub）：

```json
{"drawioPath":"D:/draw.io/draw.io.exe","port":9333}
```

`DRAWIO_PATH` 环境变量优先于配置。没有显式路径时，使用上游自己的程序定位逻辑。运行目录通过 `--workdir` 指定，图纸副本、证据和 profile 均放在该目录；不会写进技能源码文件夹。

## 正常绘图

1. `drawio_live_get_capabilities` 读取可用形状类型。
2. `drawio_live_launch`，随后 `status`，要求 `graph_ready=true`。
3. `inspect`，核对正确窗口、源文件和对象，不对非空画布擅自 clear。
4. 以 `add_shape(shape=text)` 建独立文字；以 `add_edge(source,target,entry/exit,waypoints)` 建完整绑定箭头。
5. `update_cell` 调整明确对象；`align_cells`、`distribute_cells` 统一布局。
6. 每一区域与整图执行 `audit_figure`，看新截图；按对象修复，再重新审查。
7. 单页 `save_snapshot`；多页完整另存或合回原多页副本。调用文件工具校验并真实导出 PNG，目视核对。复杂变换后重新打开验证。

只使用 draw.io graph API，不用 OS 鼠标/键盘或截图贴图来代替可编辑构建。绑定、绘图、保存是不同能力，必须分别确认。

## 启动限制

普通双击启动的 draw.io 通常没有调试端口。用本技能入口启动的窗口可连接本地端口 9333，调试地址仅为 127.0.0.1。

上游 `launch` 在端口已有窗口时会连接它，**不会打开新传入的 file_path**。脚本因此拒绝在已有受控窗口时悄悄切换输入文件；换图前由用户保存并关闭旧受控窗口。

Windows 后台启动用 `Start-Process -WindowStyle Hidden` 启动保持运行的 Node 助手；draw.io 画布可见。助手保持 MCP 生命周期，用户关闭该受控窗口后退出。普通一次性启动脚本在某些受限执行环境退出时会连带关闭窗口。

## stdio 客户端

`session` 初始化 live 与 file 工具服务后，每行接收一条 JSON：

```json
{"tool":"drawio_live_launch","args":{"port":9333,"include_screenshot":false},"save":"连接"}
{"tool":"drawio_live_inspect","args":{"max_cells":2000},"save":"对象清单"}
{"server":"file","tool":"drawio_validate","args":{"input_path":"/absolute/path/output.drawio"},"save":"文件核验"}
{"stop":true}
```

工具参数也可通过 `argsFile` 指向 UTF-8 JSON 文件传入。结果 JSON 与 PNG 保存到 workdir/evidence；不打印图片 base64。关闭客户端不擅自关闭已连接的用户窗口；`close_session` 只用于本 MCP 自己创建且已保存的独立测试进程。

## 验证基线

2026-10-09，Windows + draw.io 32.3.0 + Scientific Illustrator 1.5.4 已实际验证：原生绘制 15 个独立文字框、9 个形状、5 条绑定箭头，文字更新、精确对齐、保存、2000 像素 PNG/SVG 导出、关闭自有测试进程后重新打开，以及后台持续连接。测试图完全合成，无研究内容。

本技能的发布检查还会验证新打包脚本。结构检查不能替代最终图的目视检查；未测试的平台或上游新版本不宣称完全兼容。
