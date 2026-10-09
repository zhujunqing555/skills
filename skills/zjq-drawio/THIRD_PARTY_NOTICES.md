# 来源与依赖

本技能的中文整合及辅助脚本以本目录 MIT LICENSE 发布。既有 drawio、drawio-academic-skills、cell 和上游 Scientific Illustrator 安装均保留，不包含在本包中。

主要设计来源：

- [drawio-skills](https://github.com/bahayonghang/drawio-skills)：本地 2.8.0 技能元数据标明 MIT，借鉴原生对象、格式与实际导出规则；没有复制其渲染器、主题、stencil 或 vendor 代码。
- [Scientific Illustrator](https://github.com/icebird1998/scientific-illustrator)：外部运行依赖，验证版本 v1.5.4；下列为其许可证声明。本包调用已安装服务，未复制其服务端代码。

```text
MIT License

Copyright (c) 2026 一个地质博士 (icebird1998)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Pillow 仅由配套文件工具按需使用，未在本目录捆绑；相关许可见其官方项目。
