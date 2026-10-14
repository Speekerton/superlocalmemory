const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const src = fs.readFileSync(path.join(root, 'src', 'extension.ts'), 'utf8');

test('license, publisher, name', () => {
  assert.strictEqual(pkg.license, 'MIT');
  assert.strictEqual(pkg.publisher, 'qualixar');
  assert.strictEqual(pkg.name, 'superlocalmemory');
  assert.match(fs.readFileSync(path.join(root, 'LICENSE'), 'utf8'), /^MIT License/);
});

test('engine floor supports the MCP provider API', () => {
  assert.strictEqual(pkg.engines.vscode, '^1.101.0');
});

test('contributed provider id matches the id registered in extension.ts', () => {
  const providers = pkg.contributes.mcpServerDefinitionProviders;
  assert.strictEqual(providers.length, 1);
  const m = src.match(/PROVIDER_ID\s*=\s*'([^']+)'/);
  assert.ok(m, 'PROVIDER_ID constant not found');
  assert.strictEqual(providers[0].id, m[1]);
  assert.ok(src.includes('registerMcpServerDefinitionProvider(PROVIDER_ID'));
});

test('icon exists and entry point is declared', () => {
  assert.ok(fs.existsSync(path.join(root, pkg.icon)));
  assert.strictEqual(pkg.main, './out/extension.js');
});

test('server is launched as "slm mcp" with the vscode agent id', () => {
  assert.ok(src.includes("SLM_AGENT_ID: 'vscode'"));
  assert.ok(src.includes("['mcp']"));
});

test('no network or telemetry code in source', () => {
  assert.ok(!/require\(['"](https?|net|dgram)['"]\)|from ['"](https?|net)['"]|fetch\(/.test(src));
});
