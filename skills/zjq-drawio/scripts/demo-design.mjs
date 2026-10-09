// Native graph operations only. This file never generates draw.io XML.
export const palette = {
  text: '#304956', arrow: '#687E80',
  panels: [
    { fill: '#F1F6FA', border: '#819DB5', accent: '#D7E5EF' },
    { fill: '#F2F7F3', border: '#869F90', accent: '#DAE8DE' },
    { fill: '#F6F3F8', border: '#A294AE', accent: '#E6DDEE' },
  ],
};
const textStyle = (size = 26, bold = false, font = 'Microsoft YaHei') =>
  `text;html=1;whiteSpace=wrap;align=center;verticalAlign=middle;fillColor=none;strokeColor=none;fontFamily=${font};fontSize=${size};fontColor=${palette.text};fontStyle=${bold ? 1 : 0};spacing=0;`;
const text = (id, label, x, y, width, height, size = 26, bold = false, font) =>
  ({ type: 'shape', id, shape: 'text', label, x, y, width, height, style: textStyle(size, bold, font) });
const box = (id, x, y, width, height, fill, stroke, rounded = false, line = 1.6) =>
  ({ type: 'shape', id, label: '', shape: rounded ? 'rounded' : 'rectangle', x, y, width, height,
    style: `rounded=${rounded ? 1 : 0};arcSize=12;html=1;fillColor=${fill};strokeColor=${stroke};strokeWidth=${line};` });
const connector = (id, source, target, width, horizontal = false) =>
  ({ type: 'edge', id, source, target, label: '', color: palette.arrow, width,
    exit_x: horizontal ? 1 : 0.5, exit_y: horizontal ? 0.5 : 1,
    entry_x: horizontal ? 0 : 0.5, entry_y: horizontal ? 0.5 : 0,
    style: 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;endSize=7;exitPerimeter=1;entryPerimeter=1;' });

export const stageIds = [1, 2, 3].map(i => `demo-panel-${i}`);
export const regions = [
  {
    name: '01_标题和布局',
    operations: [
      text('demo-title', 'draw.io 本地可编辑工作流', 30, 38, 780, 50, 32, true),
      text('demo-subtitle', '连接画布 → 原生编辑 → 核验交付', 45, 100, 750, 38, 26),
      ...palette.panels.map((p, i) => box(stageIds[i], 35 + i * 275, 165, 210, 310, p.fill, p.border, true, 1.8)),
    ],
  },
  ...palette.panels.map((p, i) => {
    const n = i + 1, x = 35 + i * 275;
    return {
      name: `0${n + 1}_第${n}块`,
      operations: [
        text(`demo-number-${n}`, String(n), x + 80, 182, 50, 35, 28, true, 'Times New Roman'),
        text(`demo-heading-${n}`, ['连接画布', '规划与编辑', '核验与交付'][i], x + 9, 225, 192, 42, 26, true),
        box(`demo-action-${n}`, x + 12, 286, 186, 65, p.accent, p.border, true),
        text(`demo-action-label-${n}`, ['读取图纸', '调整布局', '核验与导出'][i], x + 15, 299, 180, 38, 26),
        box(`demo-object-${n}`, x + 12, 399, 186, 56, '#FFFFFF', p.border),
        text(`demo-object-label-${n}`, ['可编辑对象', 'z<sup>chem</sup>', 'draw.io / SVG'][i], x + 16, 404, 178, 46, 26, false, i ? 'Times New Roman' : 'Microsoft YaHei'),
        connector(`demo-inner-edge-${n}`, `demo-action-${n}`, `demo-object-${n}`, 2.4),
      ],
    };
  }),
  {
    name: '05_统一布局和箭头',
    operations: [
      // Demonstrate a real model update, rather than only initial construction.
      { type: 'update', id: 'demo-action-label-1', label: '读取最新图纸' },
      { type: 'align', cell_ids: stageIds, alignment: 'top', relative_to: 'selection' },
      { type: 'distribute', cell_ids: stageIds, direction: 'horizontal', relative_to: 'selection' },
      connector('demo-flow-edge-1', stageIds[0], stageIds[1], 3.6, true),
      connector('demo-flow-edge-2', stageIds[1], stageIds[2], 3.6, true),
      text('demo-footer', '文字、形状与完整箭头均为原生可编辑对象', 30, 511, 780, 36, 24),
      { type: 'fit' },
    ],
  },
];

export const expected = {
  vertices: 24, edges: 5, images: 0,
  editedTextId: 'demo-action-label-1', editedText: '读取最新图纸',
};
