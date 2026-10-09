# ZJQ_draw.io 技能包

两个可单独选择的中文技能，保留可编辑对象并核对真实 draw.io 显示。新增内容不改变此仓库其他技能的许可证。

| 技能 | 主要用途 | 调用 |
|---|---|---|
| [ZJQ_draw.io](skills/zjq-drawio/SKILL.md) | 科研流程图规划、布局美化、独立文字、绑定箭头、桌面接入 | `$zjq-drawio` |
| [ZJQ_draw.io_Tools](skills/zjq-drawio-tools/SKILL.md) | 兼容性检查、图片压缩、多页保留、局部补丁、真实导出 | `$zjq-drawio-tools` |

## 安装到 Codex

将这两个目录分别复制到 `~/.codex/skills/`，或在 Windows 克隆本仓库后运行：

```powershell
.\install-zjq-drawio.ps1 -DrawioPath 'D:\draw.io\draw.io.exe'
```

程序路径按本机情况替换。安装脚本不覆盖已有同名技能，也不删除旧 drawio/cell/ZJQ 技能；已有技能时先审阅自己的修改再决定更新方式。机器配置仅写入本地 Codex 配置目录，不提交到仓库。

`zjq-drawio` 的桌面模式依赖已安装的 [Scientific Illustrator](https://github.com/icebird1998/scientific-illustrator) 和 Node.js 22+，本包不打包或自动安装上游插件。文件工具 inspect/patch/merge-page 使用 Python 标准库，压缩位图需要：

```text
python -m pip install -r skills/zjq-drawio-tools/requirements.txt
```

## 使用

直接提出：“用 ZJQ_draw.io 美化这张图，保持内容逻辑，文字独立，箭头绑定外框。”

或：“用 ZJQ_draw.io_Tools 检查文件，压缩为 JPG，但保留所有页与可编辑对象。”

Windows 可把已保存图纸拖到 `skills/zjq-drawio/scripts/启动可控drawio.cmd`：建立副本，在默认端口 9333 打开可连接窗口。之后告知 AI 文件和修改范围。已有受控窗口时不会悄悄切换图纸。

## 验证与限制

文件工具有合成多页回归测试，覆盖压缩 diagram、PNG→JPEG、透明度、中文/公式、封装 object id、绑定箭头、合页、拒绝覆盖与坏引用。可运行：

```text
python skills/zjq-drawio-tools/scripts/test_drawio_file.py
node --check skills/zjq-drawio/scripts/live.mjs
node skills/zjq-drawio/scripts/live.mjs demo --workdir <独立测试目录> --hold
```

真实桌面验证基线：Windows、draw.io 32.3.0、Scientific Illustrator 1.5.4；演示用 15 个独立文字框、9 个形状、5 条绑定箭头，无研究图片。输出来自 Desktop 渲染，不能以近似 SVG 替代实际检查。

当前上游 `save_snapshot` 只保存活动页，多页文件必须完整另存或明确合回目标页。PNG 像素宽度不是 dpi 保证。本包不声称任意 PPT 的无损双向同步。

来源整理见 [source-audit.md](skills/zjq-drawio/references/source-audit.md)。仅发布技能、辅助代码、许可证与合成测试，不含用户图纸、缓存、账号配置或科研画像。
