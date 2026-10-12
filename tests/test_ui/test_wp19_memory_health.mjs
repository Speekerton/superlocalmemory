import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('Memory health offers progress, pause, resume and a single-run undo', () => {
  const code = readFileSync('src/superlocalmemory/ui/js/od-memory-health.js', 'utf8');
  for (const text of ['Memory health', 'Improving your memories:', 'Pause', 'Resume',
                       'Undo', '/api/memory-health/action', 'textContent']) {
    assert.ok(code.includes(text), text);
  }
  assert.ok(!code.includes('.innerHTML'), 'untrusted progress and error text must be escaped');
});
