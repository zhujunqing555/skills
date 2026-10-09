import { promises as fs } from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import { createInterface } from 'node:readline';
import { loadConfig, resolvePlugin, McpClient, valueOf, saveResult } from './mcp-client.mjs';
import { regions, expected } from './demo-design.mjs';

const command = process.argv[2] || 'probe';
const options = {};
for (let i = 3; i < process.argv.length; i++) {
  const key = process.argv[i];
  if (key === '--hold') options.hold = true;
  else if (['--workdir', '--input', '--port'].includes(key) && process.argv[i + 1]) options[key.slice(2)] = process.argv[++i];
  else throw new Error(`Unknown argument: ${key}`);
}
const config = await loadConfig();
const workdir = path.resolve(options.workdir || config.workdir || path.join(process.cwd(), '.zjq-drawio'));
const pluginDir = await resolvePlugin(config);
const port = Number(options.port || config.port || 9333);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid local port');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const clients = [];
let count = 0;
async function client(entry, selectedPort = port) {
  const env = { DRAWIO_LIVE_PROFILE: path.join(workdir, 'profiles', String(selectedPort)) };
  if (config.drawioPath) env.DRAWIO_PATH = config.drawioPath;
  const item = new McpClient(pluginDir, entry, env); clients.push(item); await item.initialize(); return item;
}
async function invoke(item, tool, args = {}, name) {
  const result = await item.call(tool, args);
  if (name) await saveResult(result, workdir, `${stamp}_${name}`);
  return valueOf(result);
}
async function targets(selectedPort) {
  try {
    const response = await fetch(`http://127.0.0.1:${selectedPort}/json/list`, { signal: AbortSignal.timeout(1500) });
    if (!response.ok) return [];
    return (await response.json()).filter(t => t.type === 'page' && /draw\.io|diagrams\.net/i.test(`${t.title} ${t.url}`));
  } catch { return []; }
}
async function portFree(selectedPort) {
  return new Promise(resolve => {
    const server = net.createServer(); server.once('error', () => resolve(false));
    server.listen(selectedPort, '127.0.0.1', () => server.close(() => resolve(true)));
  });
}
async function connect(item, selectedPort, filePath) {
  await invoke(item, 'drawio_live_get_capabilities', { include_registered_shapes: false,
    include_registered_markers: false, include_registered_edge_styles: false });
  const launched = await invoke(item, 'drawio_live_launch', { port: selectedPort,
    ...(filePath ? { file_path: filePath } : {}), maximize: false, step_delay_ms: 30, include_screenshot: false }, 'launch');
  if (!launched.status?.graph_ready) throw new Error('Launched window has no ready graph');
  const status = await invoke(item, 'drawio_live_status', {}, 'status');
  if (!status.graph_ready) throw new Error('Graph is not ready');
  const inspect = await invoke(item, 'drawio_live_inspect', { max_cells: 2000 }, 'inspect');
  return { status, inspect };
}
async function hold(selectedPort) {
  if (!options.hold) return;
  console.log('后台保持连接；关闭受控 draw.io 窗口后助手退出。');
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 10000));
    if (!(await targets(selectedPort)).length) break;
  }
}
function assertDemo(inspect) {
  const vertices = inspect.cells.filter(c => c.type === 'vertex'), edges = inspect.cells.filter(c => c.type === 'edge');
  if (inspect.truncated || vertices.length !== expected.vertices || edges.length !== expected.edges) throw new Error('Demo object count differs');
  if (!vertices.some(c => c.id === expected.editedTextId && c.label === expected.editedText)) throw new Error('Edited text did not persist');
  if (edges.some(c => !c.source || !c.target)) throw new Error('Demo edge is not attached');
  if (vertices.some(c => /shape=image|image=/.test(c.style))) throw new Error('Unexpected picture in demo');
}
async function probe() {
  if (!(await targets(port)).length) throw new Error('未找到受控 draw.io 窗口。先用 open --hold 或 Windows 启动入口。');
  const live = await client('live-server.mjs');
  const { status, inspect } = await connect(live, port);
  console.log(JSON.stringify({ connected: true, graph_ready: true, title: status.title, port,
    objects: inspect.total, modified: false, workdir }));
}
async function open() {
  const existing = await targets(port);
  if (existing.length && options.input) throw new Error('受控端口已有窗口；未切换图纸。先保存并关闭旧受控窗口再重试。');
  if (!existing.length && !(await portFree(port))) throw new Error('本地端口被其他程序占用。');
  let copyPath;
  if (options.input) {
    const source = path.resolve(options.input);
    const handle = await fs.open(source, 'r');
    let head; try { const b = Buffer.alloc(4096); const r = await handle.read(b, 0, b.length, 0); head = b.subarray(0, r.bytesRead).toString('utf8'); } finally { await handle.close(); }
    if (!/<(?:mxfile|mxGraphModel)\b/.test(head)) throw new Error('Input does not look like native draw.io XML');
    const folder = path.join(workdir, 'working-copies'); await fs.mkdir(folder, { recursive: true });
    copyPath = path.join(folder, `${path.basename(source, path.extname(source))}_${stamp}.drawio`);
    await fs.copyFile(source, copyPath, 1);
  }
  const live = await client('live-server.mjs');
  const { status, inspect } = await connect(live, port, copyPath);
  if (copyPath && !status.title.includes(path.basename(copyPath))) throw new Error('Wrong file was opened. Stop editing.');
  const report = { title: status.title, port, objects: inspect.total, input: options.input || null,
    working_copy: copyPath || null, modified: false, workdir };
  await fs.mkdir(workdir, { recursive: true });
  await fs.writeFile(path.join(workdir, 'connection.json'), JSON.stringify(report, null, 2), 'utf8');
  console.log(JSON.stringify(report)); await hold(port);
}
async function session() {
  const live = await client('live-server.mjs'), file = await client('server.mjs');
  console.log(JSON.stringify({ ready: true, live_tools: live.tools.length, file_tools: file.tools.length, workdir }));
  const input = createInterface({ input: process.stdin });
  for await (const line of input) {
    if (!line.trim()) continue;
    try {
      const op = JSON.parse(line); if (op.stop) { input.close(); break; }
      const args = op.argsFile ? JSON.parse(await fs.readFile(op.argsFile, 'utf8')) : op.args || {};
      const result = await (op.server === 'file' ? file : live).call(op.tool, args);
      const saved = await saveResult(result, workdir, op.save || `step-${++count}`);
      let summary = saved.value;
      if (op.summaryKeys) summary = Object.fromEntries(op.summaryKeys.map(k => [k, saved.value[k]]));
      if (summary?.cells) summary = { total: summary.total, truncated: summary.truncated, full_inventory: saved.jsonPath };
      if (summary?.results) summary = { operations_applied: summary.operations_applied, full_results: saved.jsonPath };
      console.log(JSON.stringify({ ok: true, tool: op.tool, ...saved, value: summary }));
    } catch (error) { console.log(JSON.stringify({ ok: false, error: error.message })); }
  }
}
async function demo() {
  let demoPort;
  for (let p = 9441; p <= 9460; p++) if (await portFree(p)) { demoPort = p; break; }
  if (!demoPort) throw new Error('No free demo port');
  const live = await client('live-server.mjs', demoPort), file = await client('server.mjs');
  const { inspect } = await connect(live, demoPort);
  if (inspect.total !== 0) throw new Error('Demo canvas is nonempty. It will not be cleared.');
  for (let i = 0; i < regions.length; i++) {
    await invoke(live, 'drawio_live_draw_sequence', { operations: regions[i].operations, step_delay_ms: 30, screenshot_after: true }, `region-${i + 1}`);
    await invoke(live, 'drawio_live_fit', {}, `region-${i + 1}-render`);
    await invoke(live, 'drawio_live_inspect', { max_cells: 2000 }, `region-${i + 1}-inspect`);
    const audit = await invoke(live, 'drawio_live_audit_figure', { max_findings: 100 }, `region-${i + 1}-audit`);
    if (!audit.passed || audit.hard_failure_count || audit.warning_count || audit.findings_truncated) throw new Error('Region audit failed; inspect evidence before continuing');
    console.log(`${regions[i].name}: structure passed`);
  }
  assertDemo(await invoke(live, 'drawio_live_inspect', { max_cells: 2000 }, 'final-inspect'));
  const folder = path.join(workdir, 'demo-output', stamp); await fs.mkdir(folder, { recursive: true });
  const output = path.join(folder, 'ZJQ_drawio_demo.drawio');
  await invoke(live, 'drawio_live_save_snapshot', { output_path: output, page_name: 'ZJQ synthetic demo', overwrite: false }, 'save');
  const validation = await invoke(file, 'drawio_validate', { input_path: output }, 'validate');
  if (!validation.valid || validation.warnings.length) throw new Error('Saved-file validation failed');
  for (const format of ['png', 'svg']) await invoke(file, 'drawio_export', { input_path: output, format,
    output_path: path.join(folder, `ZJQ_drawio_demo.${format}`), embed: false, border: 24,
    ...(format === 'png' ? { width: 2000 } : {}), overwrite: false }, `export-${format}`);
  await invoke(live, 'drawio_live_close_session', { confirm: true }, 'close-owned-demo');
  await connect(live, demoPort, output);
  assertDemo(await invoke(live, 'drawio_live_inspect', { max_cells: 2000 }, 'reopen-inspect'));
  const audit = await invoke(live, 'drawio_live_audit_figure', { max_findings: 100 }, 'reopen-audit');
  if (!audit.passed || audit.hard_failure_count || audit.warning_count) throw new Error('Reopen audit failed');
  await invoke(live, 'drawio_live_fit', {}, 'reopen-render');
  console.log(JSON.stringify({ passed: true, vertices: 24, edges: 5, images: 0, output, port: demoPort,
    note: '请目视核对实际导出 PNG；结构通过不代表自动审美通过。' }));
  await hold(demoPort);
}
try {
  if (command === 'probe') await probe();
  else if (command === 'open') await open();
  else if (command === 'session') await session();
  else if (command === 'demo') await demo();
  else throw new Error('Commands: probe / open / session / demo');
} catch (error) { console.error(error.message); process.exitCode = 1; }
finally { for (const item of clients) item.stop(); }
