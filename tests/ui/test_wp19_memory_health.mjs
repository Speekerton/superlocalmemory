/**
 * Health → Memory health: one card in plain words. It shows the automatic
 * improvement progress, offers pause/resume and a single-run undo, a single
 * "Fix N ..." button per repair that needs a decision, and hosts the upgrade
 * store check (#store-check) inside the same card.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import { readFileSync } from 'node:fs';

const SCRIPT = readFileSync(new URL('../../src/superlocalmemory/ui/js/od-memory-health.js', import.meta.url), 'utf8');
const tick = () => new Promise((r) => setTimeout(r, 0));

async function mount(state) {
  const dom = new JSDOM('<div id="health"></div>', { runScripts: 'outside-only' });
  const calls = [];
  dom.window.slmFetch = (path, init) => {
    calls.push({ path, method: (init && init.method) || 'GET', body: init && init.body });
    return Promise.resolve(new Response(JSON.stringify(state()), { status: 200 }));
  };
  dom.window.setInterval = () => 0;
  dom.window.eval(SCRIPT);
  dom.window.odMountMemoryHealth(dom.window.document.getElementById('health'));
  for (let i = 0; i < 6; i += 1) await tick();
  const card = dom.window.document.getElementById('memory-health-card');
  return { dom, calls, card };
}
const buttons = (card) => [...card.querySelectorAll('button')].map((b) => b.textContent);

test('the static source never writes untrusted text as HTML', () => {
  assert.ok(!SCRIPT.includes('.innerHTML'));
  for (const text of ['Improving your memories:', '/api/memory-health/action', 'textContent']) {
    assert.ok(SCRIPT.includes(text), text);
  }
});

test('progress is in plain words, with Pause while running and the store check in the same card', async () => {
  const f = await mount(() => ({ enrichment: { run_id: 'r1', status: 'running', processed: 3, total: 12, changed: 0 }, repairs: [] }));
  assert.match(f.card.textContent, /Memory health/);
  assert.match(f.card.textContent, /Improving your memories: 3 of 12/);
  assert.deepEqual(buttons(f.card), ['Pause']);
  assert.ok(f.card.querySelector('#store-check'), 'the store check renders inside Memory health');
  f.card.querySelector('button').click();
  for (let i = 0; i < 6; i += 1) await tick();
  const post = f.calls.find((c) => c.method === 'POST');
  assert.equal(post.path, '/api/memory-health/action');
  assert.deepEqual(JSON.parse(post.body), { action: 'pause', run_id: 'r1' });
});

test('a paused run offers Resume; a finished run with changes offers one Undo', async () => {
  const paused = await mount(() => ({ enrichment: { run_id: 'r1', status: 'paused', processed: 3, total: 12 }, repairs: [] }));
  assert.deepEqual(buttons(paused.card), ['Resume']);
  const done = await mount(() => ({ enrichment: { run_id: 'r2', status: 'completed', processed: 12, total: 12, changed: 9, updated_at: '2026-10-12T10:00:00+00:00' }, repairs: [] }));
  assert.deepEqual(buttons(done.card), ['Undo last improvement']);
});

test('a repair that needs a decision gets exactly one plain-language Fix button', async () => {
  const f = await mount(() => ({
    enrichment: { status: 'completed', processed: 12, total: 12, changed: 0 },
    repairs: [{ run_id: 'h1', action: 'entity-links', status: 'completed', found: 60, fixed: 25, created_at: '2026-10-12T10:00:00+00:00' }],
  }));
  assert.match(f.card.textContent, /Found 60 entity links; fixed 25 automatically/);
  assert.deepEqual(buttons(f.card), ['Fix 35 entity links', 'Undo last improvement']);
  [...f.card.querySelectorAll('button')].find((b) => b.textContent.startsWith('Fix')).click();
  for (let i = 0; i < 6; i += 1) await tick();
  const post = f.calls.find((c) => c.method === 'POST');
  assert.deepEqual(JSON.parse(post.body), { action: 'repair', repair: 'entity-links' });
});
