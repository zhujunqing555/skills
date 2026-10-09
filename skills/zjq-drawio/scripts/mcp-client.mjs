import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import os from 'node:os';

export async function loadConfig() {
  const codexDir = process.env.CODEX_HOME || path.join(os.homedir(), '.codex');
  const filename = process.env.ZJQ_DRAWIO_CONFIG || path.join(codexDir, 'zjq-drawio', 'config.json');
  let config = {};
  try { config = JSON.parse(await fs.readFile(filename, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw new Error(`Invalid local config: ${filename}: ${error.message}`); }
  return { ...config, codexDir, drawioPath: process.env.DRAWIO_PATH || config.drawioPath,
    pluginDir: process.env.SCIENTIFIC_ILLUSTRATOR_PLUGIN || config.pluginDir };
}
export async function resolvePlugin(config) {
  const matches = [];
  if (config.pluginDir) matches.push(path.resolve(config.pluginDir));
  else {
    const cache = path.join(config.codexDir, 'plugins', 'cache', 'scientific-illustrator-tools', 'scientific-illustrator');
    try {
      const versions = (await fs.readdir(cache)).filter(v => /^\d+\.\d+\.\d+$/.test(v));
      versions.sort((a, b) => {
        const av = a.split('.').map(Number), bv = b.split('.').map(Number);
        return bv[0] - av[0] || bv[1] - av[1] || bv[2] - av[2];
      });
      matches.push(...versions.map(v => path.join(cache, v)));
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  for (const candidate of matches) {
    for (const dir of [candidate, path.join(candidate, 'plugins', 'scientific-illustrator')]) {
      try { await fs.access(path.join(dir, 'scripts', 'live-server.mjs')); return dir; } catch {}
    }
  }
  throw new Error('Scientific Illustrator backend not found. Install it first or set SCIENTIFIC_ILLUSTRATOR_PLUGIN to its plugin directory.');
}
export class McpClient {
  constructor(pluginDir, entry, env = {}) {
    this.sequence = 0; this.pending = new Map(); this.stderr = '';
    this.child = spawn(process.execPath, [path.join(pluginDir, 'scripts', entry)], {
      cwd: pluginDir, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
      env: { ...process.env, ...env },
    });
    this.lines = createInterface({ input: this.child.stdout });
    this.child.stderr.on('data', data => { this.stderr = (this.stderr + String(data)).slice(-65536); });
    this.lines.on('line', line => {
      let message; try { message = JSON.parse(line); } catch { return; }
      const pending = this.pending.get(message.id); if (!pending) return;
      clearTimeout(pending.timer); this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
      else pending.resolve(message.result);
    });
    const fail = error => {
      for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error); }
      this.pending.clear();
    };
    this.child.once('error', fail);
    this.child.once('exit', code => fail(new Error(`MCP exited: ${code}; ${this.stderr}`)));
  }
  request(method, params = {}, timeout = 60000) {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`MCP timeout: ${method}`)); }, timeout);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    });
  }
  async initialize() {
    const result = await this.request('initialize', { protocolVersion: '2025-06-18', capabilities: {},
      clientInfo: { name: 'zjq-drawio', version: '1.0.0' } });
    this.child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
    this.tools = (await this.request('tools/list')).tools;
    return { server: result.serverInfo, tools: this.tools.length };
  }
  async call(name, args = {}) {
    if (!this.tools?.some(tool => tool.name === name)) throw new Error(`Backend does not advertise ${name}`);
    const result = await this.request('tools/call', { name, arguments: args });
    if (result.isError) throw new Error(JSON.stringify(result.structuredContent || result.content));
    return result;
  }
  stop() { this.lines.close(); this.child.kill(); }
}
export function valueOf(result) {
  return result.structuredContent ?? JSON.parse(result.content.find(c => c.type === 'text').text);
}
export async function saveResult(result, workdir, stem) {
  if (!/^[\p{L}\p{N}_.-]+$/u.test(stem) || stem === '.' || stem === '..') throw new Error('Invalid evidence filename');
  const output = path.join(workdir, 'evidence'); await fs.mkdir(output, { recursive: true });
  const value = valueOf(result), images = [];
  const jsonPath = path.join(output, `${stem}.json`);
  await fs.writeFile(jsonPath, JSON.stringify(value, null, 2), 'utf8');
  for (const block of result.content || []) {
    if (block.type !== 'image') continue;
    const imagePath = path.join(output, `${stem}${images.length ? '-' + images.length : ''}.png`);
    await fs.writeFile(imagePath, Buffer.from(block.data, 'base64')); images.push(imagePath);
  }
  return { value, jsonPath, images };
}
