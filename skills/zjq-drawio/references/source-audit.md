# 现有技能整理与能力边界

| 来源 | 用到的能力 | ZJQ 处理方式 |
|---|---|---|
| drawio 2.8.0 | YAML 新建、主题、原生 XML、Desktop 导出 | 离线可选后端；保留原安装，不复制整个渲染器 |
| drawio-academic-skills 2.8.0 | 学术可读性、公式、图例与投稿尺寸 | 按任务采用；不把项目书字体习惯声称为期刊规定 |
| Scientific Illustrator 1.5.4：design / recreate-in-drawio / audit / correct | 规划→原生构建→审查→逐对象修复 | 汇成一套桌面工作流；调用上游 MCP 服务 |
| cell-lct、cell-ppt、cell-ppt-edited、zjq-ppt-edit | 独立可编辑文字、正确文档绑定、原生对象和实际导出核对 | 借鉴编辑经验；没有复制商业 API、凭据、模型或这些技能的代码 |
| 本地 drawio工作流 | 受控启动、后台保持、同级框/箭头、完整保存后重开 | 改为可配置路径并随技能打包 |
| 本地 JPG压缩任务 | 保留非图片结构，仅处理嵌入位图 | 用 zjq-drawio-tools 提供多页/压缩页支持和可核验报告 |

开源来源：

- [bahayonghang/drawio-skills](https://github.com/bahayonghang/drawio-skills)，本地技能元数据标明 MIT。
- [icebird1998/scientific-illustrator](https://github.com/icebird1998/scientific-illustrator)，MIT。基线提交 `3a44435da8715b7d380d5b594259e3f495c5b336`。

ZJQ 包含原创中文整理与辅助脚本；不是上游官方插件，也不代替上游后端。没有打包用户图纸、缓存、账号资料或电脑绝对路径。现有技能不删除、不覆盖。

PPT↔SVG↔draw.io 的转换范围取决于具体转换器；形状、连接器、公式、图片和组合对象都需要分别核对。本包不声称提供任意 PPT 的无损双向同步。
